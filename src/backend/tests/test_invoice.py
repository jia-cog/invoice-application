#!/usr/bin/env python3
"""
Invoice Endpoint Tests

Tests for invoice CRUD operations and validation at /api/invoices/*.
"""

import os
import sys
import unittest
import tempfile
import shutil
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User
from flask_jwt_extended import create_access_token


class TestInvoiceEndpoints(unittest.TestCase):
    """Test cases for invoice CRUD operations and validation."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        from flask import Flask
        from config import Config
        from flask_jwt_extended import JWTManager
        from routes.invoices import invoices_bp
        
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        
        db.init_app(self.app)
        JWTManager(self.app)
        self.app.register_blueprint(invoices_bp, url_prefix='/api/invoices')
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        self.client = self.app.test_client()
        
        self.user = User(username="user1", email="user1@example.com")
        self.user.set_password("password123")
        db.session.add(self.user)
        db.session.commit()
        
        self.token = create_access_token(identity=str(self.user.id))
        self.auth_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _make_items(self):
        """Create sample invoice items."""
        return [
            {"description": "Design work", "quantity": 2, "unit_price": 150.0},
            {"description": "Hosting", "quantity": 1, "unit_price": 20.0},
        ]
    
    def _make_invoice_payload(self, tax_rate=10.0, items=None, overrides=None):
        """Create a sample invoice payload."""
        payload = {
            "customer_name": "Acme Corp",
            "customer_email": "billing@acme.test",
            "customer_address": "123 Road St",
            "due_date": (date.today() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "tax_rate": tax_rate,
            "notes": "Thanks!",
            "status": "draft",
            "items": items if items is not None else self._make_items(),
        }
        if overrides:
            payload.update(overrides)
        return payload
    
    def _create_second_user_headers(self):
        """Create auth headers for a second user for cross-tenant tests."""
        u2 = User(username="user2", email="user2@example.com")
        u2.set_password("password123")
        db.session.add(u2)
        db.session.commit()
        token2 = create_access_token(identity=str(u2.id))
        return {
            "Authorization": f"Bearer {token2}",
            "Content-Type": "application/json",
        }
    
    def test_get_invoices_initially_empty(self):
        """Test that a new user has no invoices."""
        resp = self.client.get("/api/invoices/", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("invoices", data)
        self.assertEqual(len(data["invoices"]), 0)
    
    def test_create_invoice_success_and_totals(self):
        """Test successful invoice creation with correct total calculations."""
        payload = self._make_invoice_payload(tax_rate=10.0)
        resp = self.client.post("/api/invoices/", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn("invoice", data)
        inv = data["invoice"]
        self.assertTrue(inv["invoice_number"].startswith("INV-"))
        self.assertEqual(len(inv["items"]), 2)
        
        expected_subtotal = 2 * 150.0 + 1 * 20.0
        expected_tax = expected_subtotal * 0.10
        expected_total = expected_subtotal + expected_tax
        self.assertAlmostEqual(inv["subtotal"], expected_subtotal, places=2)
        self.assertAlmostEqual(inv["tax_amount"], expected_tax, places=2)
        self.assertAlmostEqual(inv["total_amount"], expected_total, places=2)
    
    def test_create_invoice_missing_required_fields(self):
        """Test invoice creation fails when required fields are missing."""
        base = self._make_invoice_payload()
        for field in ["customer_name", "due_date", "items"]:
            with self.subTest(missing=field):
                payload = dict(base)
                payload.pop(field, None)
                resp = self.client.post("/api/invoices/", json=payload, headers=self.auth_headers)
                self.assertEqual(resp.status_code, 400)
                msg = resp.get_json().get("error", "").lower()
                self.assertIn(field, msg)
        
        payload = self._make_invoice_payload(items=[])
        resp = self.client.post("/api/invoices/", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("items is required", resp.get_json().get("error", ""))
    
    def test_create_invoice_item_validation(self):
        """Test invoice creation fails when item fields are invalid."""
        items = [{"description": "Design work", "quantity": 2}]
        payload = self._make_invoice_payload(items=items)
        resp = self.client.post("/api/invoices/", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Each item must have", resp.get_json().get("error", ""))
    
    def test_get_invoice_by_id_and_not_found(self):
        """Test getting a specific invoice by ID and not found scenarios."""
        payload = self._make_invoice_payload()
        created = self.client.post("/api/invoices/", json=payload, headers=self.auth_headers).get_json()["invoice"]
        inv_id = created["id"]
        
        resp = self.client.get(f"/api/invoices/{inv_id}", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["invoice"]["id"], inv_id)
        
        resp_nf = self.client.get("/api/invoices/999999", headers=self.auth_headers)
        self.assertEqual(resp_nf.status_code, 404)
        
        other_headers = self._create_second_user_headers()
        resp_oth = self.client.get(f"/api/invoices/{inv_id}", headers=other_headers)
        self.assertEqual(resp_oth.status_code, 404)
    
    def test_update_invoice_success_and_recalculate(self):
        """Test successful invoice update with recalculated totals."""
        created = self.client.post("/api/invoices/", json=self._make_invoice_payload(), headers=self.auth_headers).get_json()["invoice"]
        inv_id = created["id"]
        
        new_items = [{"description": "Consulting", "quantity": 3, "unit_price": 100.0}]
        update_payload = {
            "customer_name": "Updated Co",
            "tax_rate": 5.0,
            "items": new_items,
        }
        resp = self.client.put(f"/api/invoices/{inv_id}", json=update_payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        inv = resp.get_json()["invoice"]
        self.assertEqual(inv["customer_name"], "Updated Co")
        self.assertEqual(len(inv["items"]), 1)
        
        expected_subtotal = 3 * 100.0
        expected_tax = expected_subtotal * 0.05
        expected_total = expected_subtotal + expected_tax
        self.assertAlmostEqual(inv["subtotal"], expected_subtotal, places=2)
        self.assertAlmostEqual(inv["tax_amount"], expected_tax, places=2)
        self.assertAlmostEqual(inv["total_amount"], expected_total, places=2)
    
    def test_update_invoice_not_found(self):
        """Test updating a non-existent invoice returns 404."""
        resp = self.client.put("/api/invoices/999999", json={"customer_name": "Nope"}, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)
    
    def test_delete_invoice_success_and_then_404(self):
        """Test successful invoice deletion and verification it's gone."""
        created = self.client.post("/api/invoices/", json=self._make_invoice_payload(), headers=self.auth_headers).get_json()["invoice"]
        inv_id = created["id"]
        
        resp_del = self.client.delete(f"/api/invoices/{inv_id}", headers=self.auth_headers)
        self.assertEqual(resp_del.status_code, 200)
        
        resp_nf = self.client.get(f"/api/invoices/{inv_id}", headers=self.auth_headers)
        self.assertEqual(resp_nf.status_code, 404)
    
    def test_unauthorized_requests_require_jwt(self):
        """Test that requests without authentication are rejected."""
        resp = self.client.get("/api/invoices/")
        self.assertEqual(resp.status_code, 401)


def run_invoice_tests():
    """Run all invoice tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoiceEndpoints)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_invoice_tests()
    if success:
        print("\n✅ All invoice tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some invoice tests failed!")
        sys.exit(1)

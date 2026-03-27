#!/usr/bin/env python3
"""
Invoice CRUD Operations Tests

Tests for invoice creation, retrieval, update, and deletion endpoints.
"""

import sys
import os
import unittest
import json

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from models import db, User, Invoice, InvoiceItem
from routes.invoices import invoices_bp


class TestInvoiceCRUD(unittest.TestCase):
    """Test cases for invoice CRUD operations."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True

        db.init_app(self.app)
        JWTManager(self.app)
        self.app.register_blueprint(invoices_bp, url_prefix='/api/invoices')

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

        # Create a test user
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()

        # Generate a JWT token for the test user
        self.token = create_access_token(identity=str(self.user.id))
        self.auth_headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ---- Helper ----

    def _valid_invoice_data(self, **overrides):
        """Return a valid invoice payload, with optional overrides."""
        data = {
            'customer_name': 'Acme Corp',
            'customer_email': 'billing@acme.com',
            'customer_address': '123 Main St',
            'due_date': '2026-12-31',
            'tax_rate': 10.0,
            'notes': 'Net 30',
            'items': [
                {'description': 'Widget A', 'quantity': 2, 'unit_price': 50.0},
                {'description': 'Widget B', 'quantity': 1, 'unit_price': 100.0},
            ]
        }
        data.update(overrides)
        return data

    def _create_invoice(self, **overrides):
        """Create an invoice via the API and return the response."""
        data = self._valid_invoice_data(**overrides)
        return self.client.post(
            '/api/invoices/',
            data=json.dumps(data),
            headers=self.auth_headers
        )

    # ---- GET /api/invoices/ (list) ----

    def test_list_invoices_empty(self):
        """GET /api/invoices/ returns an empty list when no invoices exist."""
        resp = self.client.get('/api/invoices/', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body['invoices'], [])

    def test_list_invoices_returns_user_invoices(self):
        """GET /api/invoices/ returns invoices belonging to the authenticated user."""
        self._create_invoice(customer_name='Customer 1')
        self._create_invoice(customer_name='Customer 2')

        resp = self.client.get('/api/invoices/', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(len(body['invoices']), 2)

    def test_list_invoices_scoped_to_user(self):
        """Invoices from another user are not returned."""
        # Create a second user with their own invoice
        other_user = User(username='other', email='other@example.com')
        other_user.set_password('pass')
        db.session.add(other_user)
        db.session.commit()

        other_token = create_access_token(identity=str(other_user.id))
        other_headers = {
            'Authorization': f'Bearer {other_token}',
            'Content-Type': 'application/json'
        }

        # Create invoice for each user
        self._create_invoice(customer_name='My Customer')
        self.client.post(
            '/api/invoices/',
            data=json.dumps(self._valid_invoice_data(customer_name='Other Customer')),
            headers=other_headers
        )

        # Authenticated user should only see their own invoice
        resp = self.client.get('/api/invoices/', headers=self.auth_headers)
        body = resp.get_json()
        self.assertEqual(len(body['invoices']), 1)
        self.assertEqual(body['invoices'][0]['customer_name'], 'My Customer')

    # ---- POST /api/invoices/ (create) ----

    def test_create_invoice_success(self):
        """POST /api/invoices/ creates an invoice and returns 201."""
        resp = self._create_invoice()
        self.assertEqual(resp.status_code, 201)

        body = resp.get_json()
        invoice = body['invoice']
        self.assertIn('invoice_number', invoice)
        self.assertTrue(invoice['invoice_number'].startswith('INV-'))
        self.assertEqual(invoice['customer_name'], 'Acme Corp')
        self.assertEqual(len(invoice['items']), 2)

    def test_create_invoice_number_format(self):
        """Invoice number follows INV-YYYYMMDD-XXXXXXXX format."""
        resp = self._create_invoice()
        invoice = resp.get_json()['invoice']
        parts = invoice['invoice_number'].split('-')
        self.assertEqual(parts[0], 'INV')
        self.assertEqual(len(parts[1]), 8)  # YYYYMMDD
        self.assertEqual(len(parts[2]), 8)  # UUID fragment

    def test_create_invoice_items_created(self):
        """Created invoice has the correct items."""
        resp = self._create_invoice()
        items = resp.get_json()['invoice']['items']
        descriptions = {item['description'] for item in items}
        self.assertEqual(descriptions, {'Widget A', 'Widget B'})

    def test_create_invoice_totals_calculated(self):
        """Totals are correctly calculated on creation."""
        resp = self._create_invoice()
        invoice = resp.get_json()['invoice']
        # Widget A: 2 * 50 = 100, Widget B: 1 * 100 = 100 => subtotal = 200
        self.assertAlmostEqual(invoice['subtotal'], 200.0)
        # tax_rate = 10% => tax_amount = 20
        self.assertAlmostEqual(invoice['tax_amount'], 20.0)
        self.assertAlmostEqual(invoice['total_amount'], 220.0)

    # ---- POST /api/invoices/ — validation errors ----

    def test_create_invoice_missing_customer_name(self):
        """Missing customer_name returns 400."""
        data = self._valid_invoice_data()
        del data['customer_name']
        resp = self.client.post('/api/invoices/', data=json.dumps(data), headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_due_date(self):
        """Missing due_date returns 400."""
        data = self._valid_invoice_data()
        del data['due_date']
        resp = self.client.post('/api/invoices/', data=json.dumps(data), headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_items(self):
        """Missing items returns 400."""
        data = self._valid_invoice_data()
        del data['items']
        resp = self.client.post('/api/invoices/', data=json.dumps(data), headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_description(self):
        """Item missing description returns 400."""
        data = self._valid_invoice_data(items=[{'quantity': 1, 'unit_price': 10}])
        resp = self.client.post('/api/invoices/', data=json.dumps(data), headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_quantity(self):
        """Item missing quantity returns 400."""
        data = self._valid_invoice_data(items=[{'description': 'X', 'unit_price': 10}])
        resp = self.client.post('/api/invoices/', data=json.dumps(data), headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_unit_price(self):
        """Item missing unit_price returns 400."""
        data = self._valid_invoice_data(items=[{'description': 'X', 'quantity': 1}])
        resp = self.client.post('/api/invoices/', data=json.dumps(data), headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)

    # ---- GET /api/invoices/<id> ----

    def test_get_invoice_by_id(self):
        """GET /api/invoices/<id> returns the invoice with all fields."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.get(f'/api/invoices/{invoice_id}', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        invoice = resp.get_json()['invoice']
        self.assertEqual(invoice['id'], invoice_id)
        self.assertEqual(invoice['customer_name'], 'Acme Corp')
        self.assertIn('items', invoice)
        self.assertIn('invoice_number', invoice)
        self.assertIn('subtotal', invoice)
        self.assertIn('total_amount', invoice)

    def test_get_invoice_not_found(self):
        """GET /api/invoices/<id> returns 404 for non-existent invoice."""
        resp = self.client.get('/api/invoices/99999', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)

    # ---- PUT /api/invoices/<id> ----

    def test_update_invoice_fields(self):
        """PUT /api/invoices/<id> updates scalar fields."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        update_data = {
            'customer_name': 'Updated Corp',
            'status': 'sent',
            'notes': 'Updated notes'
        }
        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps(update_data),
            headers=self.auth_headers
        )
        self.assertEqual(resp.status_code, 200)
        invoice = resp.get_json()['invoice']
        self.assertEqual(invoice['customer_name'], 'Updated Corp')
        self.assertEqual(invoice['status'], 'sent')
        self.assertEqual(invoice['notes'], 'Updated notes')

    def test_update_invoice_replaces_items(self):
        """PUT with new items replaces old items and recalculates totals."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        new_items = [
            {'description': 'New Item', 'quantity': 5, 'unit_price': 20.0}
        ]
        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps({'items': new_items}),
            headers=self.auth_headers
        )
        self.assertEqual(resp.status_code, 200)
        invoice = resp.get_json()['invoice']
        self.assertEqual(len(invoice['items']), 1)
        self.assertEqual(invoice['items'][0]['description'], 'New Item')
        # 5 * 20 = 100, tax 10% = 10 => total 110
        self.assertAlmostEqual(invoice['subtotal'], 100.0)
        self.assertAlmostEqual(invoice['tax_amount'], 10.0)
        self.assertAlmostEqual(invoice['total_amount'], 110.0)

    def test_update_invoice_not_found(self):
        """PUT /api/invoices/<id> returns 404 for non-existent invoice."""
        resp = self.client.put(
            '/api/invoices/99999',
            data=json.dumps({'customer_name': 'Ghost'}),
            headers=self.auth_headers
        )
        self.assertEqual(resp.status_code, 404)

    # ---- DELETE /api/invoices/<id> ----

    def test_delete_invoice(self):
        """DELETE /api/invoices/<id> removes the invoice."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.delete(f'/api/invoices/{invoice_id}', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)

        # Verify it no longer exists
        resp = self.client.get(f'/api/invoices/{invoice_id}', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_cascade_items(self):
        """DELETE cascades and removes associated invoice items."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        # Confirm items exist
        items_before = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertTrue(len(items_before) > 0)

        self.client.delete(f'/api/invoices/{invoice_id}', headers=self.auth_headers)

        items_after = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items_after), 0)

    def test_delete_invoice_not_found(self):
        """DELETE /api/invoices/<id> returns 404 for non-existent invoice."""
        resp = self.client.delete('/api/invoices/99999', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)

    # ---- Authentication tests ----

    def test_list_invoices_no_token(self):
        """GET /api/invoices/ returns 401 without JWT."""
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, 401)

    def test_create_invoice_no_token(self):
        """POST /api/invoices/ returns 401 without JWT."""
        resp = self.client.post(
            '/api/invoices/',
            data=json.dumps(self._valid_invoice_data()),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 401)

    def test_get_invoice_no_token(self):
        """GET /api/invoices/<id> returns 401 without JWT."""
        resp = self.client.get('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)

    def test_update_invoice_no_token(self):
        """PUT /api/invoices/<id> returns 401 without JWT."""
        resp = self.client.put(
            '/api/invoices/1',
            data=json.dumps({'customer_name': 'Nope'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 401)

    def test_delete_invoice_no_token(self):
        """DELETE /api/invoices/<id> returns 401 without JWT."""
        resp = self.client.delete('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)


def run_invoice_tests():
    """Run all invoice tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoiceCRUD)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_invoice_tests()
    if success:
        print("\nAll invoice tests passed!")
        sys.exit(0)
    else:
        print("\nSome invoice tests failed!")
        sys.exit(1)

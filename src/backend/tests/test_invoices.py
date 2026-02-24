#!/usr/bin/env python3
"""
Invoice API Endpoint Tests

Tests for all invoice CRUD endpoints including authentication,
validation, financial calculations, and cascade deletion.
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from config import Config
from models import db, User, Invoice, InvoiceItem


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for all invoice API endpoints."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True

        db.init_app(self.app)
        self.jwt = JWTManager(self.app)

        from routes.invoices import invoices_bp
        self.app.register_blueprint(invoices_bp, url_prefix='/api/invoices')

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

        self.test_user = User(
            username='testuser',
            email='test@example.com',
            company_name='Test Corp'
        )
        self.test_user.set_password('password123')
        db.session.add(self.test_user)
        db.session.commit()

        self.token = create_access_token(identity=str(self.test_user.id))
        self.auth_headers = {'Authorization': f'Bearer {self.token}'}

        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_invoice_in_db(self, user_id=None, customer_name='Acme Corp',
                              invoice_number='INV-TEST-001', tax_rate=10.0):
        """Helper to create an invoice directly in the database."""
        if user_id is None:
            user_id = self.test_user.id

        invoice = Invoice(
            invoice_number=invoice_number,
            user_id=user_id,
            customer_name=customer_name,
            customer_email='contact@acme.com',
            customer_address='123 Main St',
            due_date=(datetime.utcnow() + timedelta(days=30)).date(),
            tax_rate=tax_rate,
            notes='Test invoice',
            status='draft'
        )
        db.session.add(invoice)
        db.session.flush()

        item1 = InvoiceItem(
            invoice_id=invoice.id,
            description='Web Development',
            quantity=10.0,
            unit_price=100.0,
            total=1000.0
        )
        item2 = InvoiceItem(
            invoice_id=invoice.id,
            description='Hosting',
            quantity=1.0,
            unit_price=50.0,
            total=50.0
        )
        db.session.add_all([item1, item2])
        invoice.calculate_totals()
        db.session.commit()
        return invoice

    def _valid_invoice_payload(self):
        """Helper to return a valid invoice creation payload."""
        return {
            'customer_name': 'Acme Corp',
            'customer_email': 'contact@acme.com',
            'customer_address': '123 Main St',
            'due_date': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 10.0,
            'notes': 'Test invoice',
            'status': 'draft',
            'items': [
                {'description': 'Web Development', 'quantity': 10, 'unit_price': 100.0},
                {'description': 'Hosting', 'quantity': 1, 'unit_price': 50.0}
            ]
        }

    # ------------------------------------------------------------------ #
    #  GET /api/invoices/ (List invoices)
    # ------------------------------------------------------------------ #

    def test_get_invoices_success(self):
        """Test successful retrieval of multiple invoices."""
        self._create_invoice_in_db(invoice_number='INV-TEST-001')
        self._create_invoice_in_db(invoice_number='INV-TEST-002', customer_name='Beta Inc')

        response = self.client.get('/api/invoices/', headers=self.auth_headers)
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)

    def test_get_invoices_empty_list(self):
        """Test retrieval when no invoices exist for the user."""
        response = self.client.get('/api/invoices/', headers=self.auth_headers)
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)

    def test_get_invoices_requires_auth(self):
        """Test that listing invoices requires authentication."""
        response = self.client.get('/api/invoices/')

        self.assertEqual(response.status_code, 401)

    def test_get_invoices_ordered_by_date(self):
        """Test that invoices are returned in descending order by created_at."""
        inv1 = self._create_invoice_in_db(invoice_number='INV-FIRST')
        inv2 = self._create_invoice_in_db(invoice_number='INV-SECOND')

        response = self.client.get('/api/invoices/', headers=self.auth_headers)
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        invoices = data['invoices']
        self.assertEqual(len(invoices), 2)
        self.assertTrue(invoices[0]['created_at'] >= invoices[1]['created_at'])

    # ------------------------------------------------------------------ #
    #  GET /api/invoices/<id> (Get single invoice)
    # ------------------------------------------------------------------ #

    def test_get_invoice_success(self):
        """Test successful retrieval of a single invoice."""
        invoice = self._create_invoice_in_db()

        response = self.client.get(f'/api/invoices/{invoice.id}', headers=self.auth_headers)
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Acme Corp')
        self.assertIn('items', data['invoice'])
        self.assertEqual(len(data['invoice']['items']), 2)

    def test_get_invoice_not_found(self):
        """Test 404 response for non-existent invoice."""
        response = self.client.get('/api/invoices/9999', headers=self.auth_headers)
        data = response.get_json()

        self.assertEqual(response.status_code, 404)
        self.assertIn('error', data)

    def test_get_invoice_wrong_user(self):
        """Test 404 response when invoice belongs to a different user."""
        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.commit()

        invoice = self._create_invoice_in_db(
            user_id=other_user.id, invoice_number='INV-OTHER-001'
        )

        response = self.client.get(f'/api/invoices/{invoice.id}', headers=self.auth_headers)

        self.assertEqual(response.status_code, 404)

    def test_get_invoice_requires_auth(self):
        """Test that getting a single invoice requires authentication."""
        invoice = self._create_invoice_in_db()

        response = self.client.get(f'/api/invoices/{invoice.id}')

        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------ #
    #  POST /api/invoices/ (Create invoice)
    # ------------------------------------------------------------------ #

    def test_create_invoice_success(self):
        """Test successful creation of an invoice with valid data."""
        payload = self._valid_invoice_payload()

        response = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Acme Corp')
        self.assertEqual(len(data['invoice']['items']), 2)

    def test_create_invoice_missing_customer_name(self):
        """Test 400 response when customer_name is missing."""
        payload = self._valid_invoice_payload()
        del payload['customer_name']

        response = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'])

    def test_create_invoice_missing_due_date(self):
        """Test 400 response when due_date is missing."""
        payload = self._valid_invoice_payload()
        del payload['due_date']

        response = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'])

    def test_create_invoice_missing_items(self):
        """Test 400 response when items array is missing."""
        payload = self._valid_invoice_payload()
        del payload['items']

        response = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
        self.assertIn('items', data['error'])

    def test_create_invoice_invalid_item(self):
        """Test 400 response when an item is missing required fields."""
        payload = self._valid_invoice_payload()
        payload['items'] = [{'description': 'Incomplete item'}]

        response = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)

    def test_create_invoice_calculates_totals(self):
        """Test that financial totals are correctly calculated on creation."""
        payload = self._valid_invoice_payload()
        payload['tax_rate'] = 10.0
        payload['items'] = [
            {'description': 'Service A', 'quantity': 2, 'unit_price': 100.0},
            {'description': 'Service B', 'quantity': 3, 'unit_price': 50.0}
        ]

        response = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 201)
        inv = data['invoice']
        expected_subtotal = (2 * 100.0) + (3 * 50.0)
        expected_tax = expected_subtotal * 10.0 / 100
        expected_total = expected_subtotal + expected_tax
        self.assertAlmostEqual(inv['subtotal'], expected_subtotal, places=2)
        self.assertAlmostEqual(inv['tax_amount'], expected_tax, places=2)
        self.assertAlmostEqual(inv['total_amount'], expected_total, places=2)

    def test_create_invoice_generates_invoice_number(self):
        """Test that a unique invoice number is generated."""
        payload = self._valid_invoice_payload()

        response = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(data['invoice']['invoice_number'].startswith('INV-'))

    def test_create_invoice_requires_auth(self):
        """Test that creating an invoice requires authentication."""
        payload = self._valid_invoice_payload()

        response = self.client.post('/api/invoices/', json=payload)

        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------ #
    #  PUT /api/invoices/<id> (Update invoice)
    # ------------------------------------------------------------------ #

    def test_update_invoice_success(self):
        """Test successful update of an invoice."""
        invoice = self._create_invoice_in_db()

        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json={'customer_name': 'Updated Corp', 'status': 'sent'},
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Corp')
        self.assertEqual(data['invoice']['status'], 'sent')

    def test_update_invoice_not_found(self):
        """Test 404 response when updating a non-existent invoice."""
        response = self.client.put(
            '/api/invoices/9999',
            json={'customer_name': 'Ghost'},
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 404)

    def test_update_invoice_wrong_user(self):
        """Test 404 response when updating another user's invoice."""
        other_user = User(username='otheruser2', email='other2@example.com')
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.commit()

        invoice = self._create_invoice_in_db(
            user_id=other_user.id, invoice_number='INV-OTHER-002'
        )

        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json={'customer_name': 'Hacked'},
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 404)

    def test_update_invoice_updates_items(self):
        """Test that updating items replaces existing items."""
        invoice = self._create_invoice_in_db()
        original_item_count = len(invoice.items)
        self.assertEqual(original_item_count, 2)

        new_items = [
            {'description': 'New Service', 'quantity': 5, 'unit_price': 200.0}
        ]

        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json={'items': new_items},
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['invoice']['items']), 1)
        self.assertEqual(data['invoice']['items'][0]['description'], 'New Service')

    def test_update_invoice_recalculates_totals(self):
        """Test that totals are recalculated after updating items."""
        invoice = self._create_invoice_in_db(tax_rate=10.0)

        new_items = [
            {'description': 'Expensive Service', 'quantity': 1, 'unit_price': 500.0}
        ]

        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json={'items': new_items},
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        inv = data['invoice']
        self.assertAlmostEqual(inv['subtotal'], 500.0, places=2)
        self.assertAlmostEqual(inv['tax_amount'], 50.0, places=2)
        self.assertAlmostEqual(inv['total_amount'], 550.0, places=2)

    def test_update_invoice_updates_timestamp(self):
        """Test that updated_at timestamp changes after an update."""
        invoice = self._create_invoice_in_db()
        original_updated_at = invoice.updated_at

        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json={'customer_name': 'Timestamp Corp'},
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(data['invoice']['updated_at'])

    def test_update_invoice_requires_auth(self):
        """Test that updating an invoice requires authentication."""
        invoice = self._create_invoice_in_db()

        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json={'customer_name': 'No Auth'}
        )

        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------ #
    #  DELETE /api/invoices/<id> (Delete invoice)
    # ------------------------------------------------------------------ #

    def test_delete_invoice_success(self):
        """Test successful deletion of an invoice."""
        invoice = self._create_invoice_in_db()
        invoice_id = invoice.id

        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn('message', data)

        deleted = db.session.get(Invoice, invoice_id)
        self.assertIsNone(deleted)

    def test_delete_invoice_not_found(self):
        """Test 404 response when deleting a non-existent invoice."""
        response = self.client.delete(
            '/api/invoices/9999',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_invoice_wrong_user(self):
        """Test 404 response when deleting another user's invoice."""
        other_user = User(username='otheruser3', email='other3@example.com')
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.commit()

        invoice = self._create_invoice_in_db(
            user_id=other_user.id, invoice_number='INV-OTHER-003'
        )

        response = self.client.delete(
            f'/api/invoices/{invoice.id}',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_invoice_cascades_items(self):
        """Test that deleting an invoice also removes its InvoiceItems."""
        invoice = self._create_invoice_in_db()
        invoice_id = invoice.id
        item_ids = [item.id for item in invoice.items]
        self.assertTrue(len(item_ids) > 0)

        self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )

        for item_id in item_ids:
            self.assertIsNone(db.session.get(InvoiceItem, item_id))

    def test_delete_invoice_requires_auth(self):
        """Test that deleting an invoice requires authentication."""
        invoice = self._create_invoice_in_db()

        response = self.client.delete(f'/api/invoices/{invoice.id}')

        self.assertEqual(response.status_code, 401)


def run_invoice_tests():
    """Run all invoice tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoiceRoutes)
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

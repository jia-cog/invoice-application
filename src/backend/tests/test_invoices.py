#!/usr/bin/env python3
"""
Invoice CRUD Tests

Comprehensive tests for invoice creation, retrieval, update, deletion,
validation, and authentication/authorization checks.
"""

import sys
import os
import unittest
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Invoice, InvoiceItem
from flask_jwt_extended import create_access_token


class TestInvoiceCRUD(unittest.TestCase):
    """Test cases for invoice CRUD operations."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()

        self.token = create_access_token(identity=str(self.user.id))
        self.auth_headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        self.valid_invoice_data = {
            'customer_name': 'Acme Corp',
            'customer_email': 'billing@acme.com',
            'customer_address': '123 Main St',
            'due_date': '2026-12-31',
            'tax_rate': 10.0,
            'notes': 'Net 30',
            'status': 'draft',
            'items': [
                {
                    'description': 'Web Development',
                    'quantity': 10,
                    'unit_price': 150.0
                },
                {
                    'description': 'Design Services',
                    'quantity': 5,
                    'unit_price': 100.0
                }
            ]
        }

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_invoice(self, data=None):
        """Helper to create an invoice and return the response."""
        payload = data if data is not None else self.valid_invoice_data
        return self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(payload)
        )

    # ---- CREATE tests ----

    def test_create_invoice_success(self):
        """Test successful invoice creation with valid data."""
        response = self._create_invoice()
        data = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Acme Corp')
        self.assertEqual(data['invoice']['customer_email'], 'billing@acme.com')
        self.assertEqual(data['invoice']['status'], 'draft')
        self.assertEqual(len(data['invoice']['items']), 2)

    def test_create_invoice_calculates_totals(self):
        """Test that creating an invoice correctly calculates subtotal, tax, and total."""
        response = self._create_invoice()
        invoice = response.get_json()['invoice']

        expected_subtotal = (10 * 150.0) + (5 * 100.0)
        expected_tax = expected_subtotal * 0.10
        expected_total = expected_subtotal + expected_tax

        self.assertAlmostEqual(invoice['subtotal'], expected_subtotal)
        self.assertAlmostEqual(invoice['tax_amount'], expected_tax)
        self.assertAlmostEqual(invoice['total_amount'], expected_total)

    def test_create_invoice_generates_invoice_number(self):
        """Test that a unique invoice number is generated."""
        response = self._create_invoice()
        invoice = response.get_json()['invoice']

        self.assertTrue(invoice['invoice_number'].startswith('INV-'))

    def test_create_invoice_missing_customer_name(self):
        """Test that missing customer_name returns 400."""
        data = {**self.valid_invoice_data, 'customer_name': ''}
        response = self._create_invoice(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

    def test_create_invoice_missing_due_date(self):
        """Test that missing due_date returns 400."""
        data = {**self.valid_invoice_data, 'due_date': ''}
        response = self._create_invoice(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

    def test_create_invoice_missing_items(self):
        """Test that missing items returns 400."""
        data = {**self.valid_invoice_data, 'items': []}
        response = self._create_invoice(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

    def test_create_invoice_item_missing_description(self):
        """Test that an item without description returns 400."""
        data = {**self.valid_invoice_data, 'items': [
            {'description': '', 'quantity': 1, 'unit_price': 100}
        ]}
        response = self._create_invoice(data)

        self.assertEqual(response.status_code, 400)

    def test_create_invoice_item_missing_quantity(self):
        """Test that an item without quantity returns 400."""
        data = {**self.valid_invoice_data, 'items': [
            {'description': 'Item', 'quantity': 0, 'unit_price': 100}
        ]}
        response = self._create_invoice(data)

        self.assertEqual(response.status_code, 400)

    def test_create_invoice_item_missing_unit_price(self):
        """Test that an item without unit_price returns 400."""
        data = {**self.valid_invoice_data, 'items': [
            {'description': 'Item', 'quantity': 1, 'unit_price': 0}
        ]}
        response = self._create_invoice(data)

        self.assertEqual(response.status_code, 400)

    def test_create_invoice_default_status(self):
        """Test that the default status is 'draft' when not specified."""
        data = {**self.valid_invoice_data}
        del data['status']
        response = self._create_invoice(data)
        invoice = response.get_json()['invoice']

        self.assertEqual(invoice['status'], 'draft')

    def test_create_invoice_zero_tax_rate(self):
        """Test invoice creation with zero tax rate."""
        data = {**self.valid_invoice_data, 'tax_rate': 0}
        response = self._create_invoice(data)
        invoice = response.get_json()['invoice']

        self.assertEqual(response.status_code, 201)
        self.assertAlmostEqual(invoice['tax_amount'], 0.0)
        self.assertAlmostEqual(invoice['total_amount'], invoice['subtotal'])

    def test_create_invoice_optional_fields_default(self):
        """Test that optional fields default to empty strings."""
        data = {
            'customer_name': 'Minimal Corp',
            'due_date': '2026-06-01',
            'items': [{'description': 'Service', 'quantity': 1, 'unit_price': 50}]
        }
        response = self._create_invoice(data)
        invoice = response.get_json()['invoice']

        self.assertEqual(response.status_code, 201)
        self.assertEqual(invoice['customer_email'], '')
        self.assertEqual(invoice['customer_address'], '')
        self.assertEqual(invoice['notes'], '')

    # ---- READ tests ----

    def test_get_all_invoices(self):
        """Test retrieving all invoices for the authenticated user."""
        self._create_invoice()
        response = self.client.get('/api/invoices/', headers=self.auth_headers)
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 1)

    def test_get_all_invoices_empty(self):
        """Test retrieving invoices when none exist."""
        response = self.client.get('/api/invoices/', headers=self.auth_headers)
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['invoices']), 0)

    def test_get_single_invoice(self):
        """Test retrieving a single invoice by ID."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice_id)

    def test_get_invoice_not_found(self):
        """Test retrieving a non-existent invoice returns 404."""
        response = self.client.get(
            '/api/invoices/9999',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.get_json())

    def test_get_invoice_belongs_to_another_user(self):
        """Test that a user cannot access another user's invoice."""
        self._create_invoice()

        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password456')
        db.session.add(other_user)
        db.session.commit()

        other_token = create_access_token(identity=str(other_user.id))
        other_headers = {
            'Authorization': f'Bearer {other_token}',
            'Content-Type': 'application/json'
        }

        invoice = Invoice.query.first()
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers=other_headers
        )

        self.assertEqual(response.status_code, 404)

    def test_get_invoices_returns_only_own(self):
        """Test that listing invoices returns only the authenticated user's invoices."""
        self._create_invoice()

        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password456')
        db.session.add(other_user)
        db.session.commit()

        other_token = create_access_token(identity=str(other_user.id))
        other_headers = {
            'Authorization': f'Bearer {other_token}',
            'Content-Type': 'application/json'
        }

        response = self.client.get('/api/invoices/', headers=other_headers)
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['invoices']), 0)

    # ---- UPDATE tests ----

    def test_update_invoice_customer_name(self):
        """Test updating the customer name of an existing invoice."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps({'customer_name': 'Updated Corp'})
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Corp')

    def test_update_invoice_status(self):
        """Test updating the status of an invoice."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps({'status': 'sent'})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['invoice']['status'], 'sent')

    def test_update_invoice_due_date(self):
        """Test updating the due date of an invoice."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps({'due_date': '2027-01-15'})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['invoice']['due_date'], '2027-01-15')

    def test_update_invoice_items_recalculates_totals(self):
        """Test that updating items recalculates totals correctly."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        new_items = [{'description': 'Consulting', 'quantity': 20, 'unit_price': 200.0}]
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps({'items': new_items, 'tax_rate': 10.0})
        )
        invoice = response.get_json()['invoice']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(invoice['items']), 1)
        self.assertAlmostEqual(invoice['subtotal'], 4000.0)
        self.assertAlmostEqual(invoice['tax_amount'], 400.0)
        self.assertAlmostEqual(invoice['total_amount'], 4400.0)

    def test_update_invoice_not_found(self):
        """Test updating a non-existent invoice returns 404."""
        response = self.client.put(
            '/api/invoices/9999',
            headers=self.auth_headers,
            data=json.dumps({'customer_name': 'Ghost'})
        )

        self.assertEqual(response.status_code, 404)

    def test_update_invoice_of_another_user(self):
        """Test that a user cannot update another user's invoice."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password456')
        db.session.add(other_user)
        db.session.commit()

        other_token = create_access_token(identity=str(other_user.id))
        other_headers = {
            'Authorization': f'Bearer {other_token}',
            'Content-Type': 'application/json'
        }

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=other_headers,
            data=json.dumps({'customer_name': 'Hacked'})
        )

        self.assertEqual(response.status_code, 404)

    def test_update_invoice_multiple_fields(self):
        """Test updating multiple fields at once."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        update_data = {
            'customer_name': 'New Name',
            'customer_email': 'new@email.com',
            'notes': 'Updated notes',
            'tax_rate': 15.0
        }
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps(update_data)
        )
        invoice = response.get_json()['invoice']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(invoice['customer_name'], 'New Name')
        self.assertEqual(invoice['customer_email'], 'new@email.com')
        self.assertEqual(invoice['notes'], 'Updated notes')
        self.assertAlmostEqual(invoice['tax_rate'], 15.0)

    # ---- DELETE tests ----

    def test_delete_invoice_success(self):
        """Test successful deletion of an invoice."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.get_json())

        get_resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        self.assertEqual(get_resp.status_code, 404)

    def test_delete_invoice_not_found(self):
        """Test deleting a non-existent invoice returns 404."""
        response = self.client.delete(
            '/api/invoices/9999',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_invoice_of_another_user(self):
        """Test that a user cannot delete another user's invoice."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password456')
        db.session.add(other_user)
        db.session.commit()

        other_token = create_access_token(identity=str(other_user.id))
        other_headers = {
            'Authorization': f'Bearer {other_token}',
            'Content-Type': 'application/json'
        }

        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=other_headers
        )

        self.assertEqual(response.status_code, 404)

        get_resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        self.assertEqual(get_resp.status_code, 200)

    def test_delete_invoice_removes_items(self):
        """Test that deleting an invoice also removes its items."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        items_before = InvoiceItem.query.filter_by(invoice_id=invoice_id).count()
        self.assertGreater(items_before, 0)

        self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )

        items_after = InvoiceItem.query.filter_by(invoice_id=invoice_id).count()
        self.assertEqual(items_after, 0)


class TestInvoiceAuthentication(unittest.TestCase):
    """Test cases for invoice endpoint authentication requirements."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_invoices_without_token(self):
        """Test that GET /api/invoices/ requires authentication."""
        response = self.client.get('/api/invoices/')

        self.assertEqual(response.status_code, 401)

    def test_get_single_invoice_without_token(self):
        """Test that GET /api/invoices/<id> requires authentication."""
        response = self.client.get('/api/invoices/1')

        self.assertEqual(response.status_code, 401)

    def test_create_invoice_without_token(self):
        """Test that POST /api/invoices/ requires authentication."""
        response = self.client.post(
            '/api/invoices/',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'customer_name': 'Test'})
        )

        self.assertEqual(response.status_code, 401)

    def test_update_invoice_without_token(self):
        """Test that PUT /api/invoices/<id> requires authentication."""
        response = self.client.put(
            '/api/invoices/1',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'customer_name': 'Test'})
        )

        self.assertEqual(response.status_code, 401)

    def test_delete_invoice_without_token(self):
        """Test that DELETE /api/invoices/<id> requires authentication."""
        response = self.client.delete('/api/invoices/1')

        self.assertEqual(response.status_code, 401)

    def test_invalid_token_rejected(self):
        """Test that requests with invalid tokens are rejected."""
        headers = {
            'Authorization': 'Bearer invalid.token.value',
            'Content-Type': 'application/json'
        }
        response = self.client.get('/api/invoices/', headers=headers)

        self.assertEqual(response.status_code, 401)


def run_invoice_tests():
    """Run all invoice tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceCRUD))
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceAuthentication))
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

#!/usr/bin/env python3
"""
Invoice Endpoint Tests

Tests for /api/invoices/* endpoints: list, get, create, update, delete.
"""

import sys
import os
import unittest

# Add the parent directory to the path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Invoice, InvoiceItem


class TestInvoiceEndpoints(unittest.TestCase):
    """Test cases for invoice API endpoints."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['TESTING'] = True

        with self.app.app_context():
            db.drop_all()
            db.create_all()

        self.client = self.app.test_client()

        # Register a user and store the token
        reg_resp = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        })
        self.token = reg_resp.get_json()['access_token']
        self.auth_header = {'Authorization': f'Bearer {self.token}'}

    def tearDown(self):
        """Clean up after each test method."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_invoice(self, customer_name='Acme Corp', due_date='2026-12-31',
                        tax_rate=10.0, status='draft', items=None):
        """Helper to create an invoice and return the response."""
        if items is None:
            items = [
                {'description': 'Widget A', 'quantity': 2, 'unit_price': 50.00},
                {'description': 'Widget B', 'quantity': 1, 'unit_price': 100.00}
            ]
        return self.client.post('/api/invoices/', json={
            'customer_name': customer_name,
            'customer_email': 'acme@example.com',
            'customer_address': '123 Main St',
            'due_date': due_date,
            'tax_rate': tax_rate,
            'notes': 'Test invoice',
            'status': status,
            'items': items
        }, headers=self.auth_header)

    def _register_second_user(self):
        """Register a second user and return their auth header."""
        reg_resp = self.client.post('/api/auth/register', json={
            'username': 'otheruser',
            'email': 'other@example.com',
            'password': 'password456'
        })
        token = reg_resp.get_json()['access_token']
        return {'Authorization': f'Bearer {token}'}

    # --- List Invoices Tests ---

    def test_list_invoices_empty(self):
        """Test listing invoices when none exist."""
        resp = self.client.get('/api/invoices/', headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['invoices'], [])

    def test_list_invoices_with_data(self):
        """Test listing invoices after creating some."""
        self._create_invoice(customer_name='Acme Corp')
        self._create_invoice(customer_name='Globex Corp')

        resp = self.client.get('/api/invoices/', headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(data['invoices']), 2)

    def test_list_invoices_no_token(self):
        """Test listing invoices fails without auth token."""
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, 401)

    def test_list_invoices_scoped_to_user(self):
        """Test that users only see their own invoices."""
        self._create_invoice(customer_name='Acme Corp')
        other_header = self._register_second_user()

        resp = self.client.get('/api/invoices/', headers=other_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(data['invoices']), 0)

    # --- Get Single Invoice Tests ---

    def test_get_invoice_success(self):
        """Test getting a single invoice by ID."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_header
        )
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['invoice']['customer_name'], 'Acme Corp')
        self.assertEqual(len(data['invoice']['items']), 2)

    def test_get_invoice_not_found(self):
        """Test getting a nonexistent invoice returns 404."""
        resp = self.client.get('/api/invoices/9999', headers=self.auth_header)
        self.assertEqual(resp.status_code, 404)

    def test_get_invoice_other_user(self):
        """Test that a user cannot access another user's invoice."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']
        other_header = self._register_second_user()

        resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=other_header
        )
        self.assertEqual(resp.status_code, 404)

    # --- Create Invoice Tests ---

    def test_create_invoice_success(self):
        """Test successful invoice creation."""
        resp = self._create_invoice()
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(data['message'], 'Invoice created successfully')
        invoice = data['invoice']
        self.assertEqual(invoice['customer_name'], 'Acme Corp')
        self.assertEqual(invoice['status'], 'draft')
        self.assertIn('INV-', invoice['invoice_number'])
        # subtotal: 2*50 + 1*100 = 200, tax: 200*0.10 = 20, total: 220
        self.assertAlmostEqual(invoice['subtotal'], 200.0)
        self.assertAlmostEqual(invoice['tax_amount'], 20.0)
        self.assertAlmostEqual(invoice['total_amount'], 220.0)
        self.assertEqual(len(invoice['items']), 2)

    def test_create_invoice_missing_customer_name(self):
        """Test creation fails without customer_name."""
        resp = self.client.post('/api/invoices/', json={
            'due_date': '2026-12-31',
            'items': [{'description': 'X', 'quantity': 1, 'unit_price': 10}]
        }, headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('customer_name is required', data['error'])

    def test_create_invoice_missing_due_date(self):
        """Test creation fails without due_date."""
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Acme',
            'items': [{'description': 'X', 'quantity': 1, 'unit_price': 10}]
        }, headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('due_date is required', data['error'])

    def test_create_invoice_missing_items(self):
        """Test creation fails without items."""
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Acme',
            'due_date': '2026-12-31'
        }, headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('items is required', data['error'])

    def test_create_invoice_item_missing_description(self):
        """Test creation fails when an item lacks description."""
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Acme',
            'due_date': '2026-12-31',
            'items': [{'quantity': 1, 'unit_price': 10}]
        }, headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('description, quantity, and unit_price', data['error'])

    def test_create_invoice_no_token(self):
        """Test creation fails without auth token."""
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Acme',
            'due_date': '2026-12-31',
            'items': [{'description': 'X', 'quantity': 1, 'unit_price': 10}]
        })
        self.assertEqual(resp.status_code, 401)

    def test_create_invoice_zero_tax(self):
        """Test invoice creation with zero tax rate."""
        resp = self._create_invoice(tax_rate=0.0)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        self.assertAlmostEqual(data['invoice']['tax_amount'], 0.0)
        self.assertAlmostEqual(data['invoice']['subtotal'],
                               data['invoice']['total_amount'])

    # --- Update Invoice Tests ---

    def test_update_invoice_fields(self):
        """Test updating invoice fields."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.put(f'/api/invoices/{invoice_id}', json={
            'customer_name': 'Updated Corp',
            'status': 'sent',
            'notes': 'Updated notes'
        }, headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['message'], 'Invoice updated successfully')
        self.assertEqual(data['invoice']['customer_name'], 'Updated Corp')
        self.assertEqual(data['invoice']['status'], 'sent')
        self.assertEqual(data['invoice']['notes'], 'Updated notes')

    def test_update_invoice_items(self):
        """Test updating invoice with new items recalculates totals."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        new_items = [
            {'description': 'New Item', 'quantity': 5, 'unit_price': 20.00}
        ]
        resp = self.client.put(f'/api/invoices/{invoice_id}', json={
            'items': new_items
        }, headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        # subtotal: 5*20 = 100, tax: 100*0.10 = 10, total: 110
        self.assertAlmostEqual(data['invoice']['subtotal'], 100.0)
        self.assertAlmostEqual(data['invoice']['tax_amount'], 10.0)
        self.assertAlmostEqual(data['invoice']['total_amount'], 110.0)
        self.assertEqual(len(data['invoice']['items']), 1)

    def test_update_invoice_not_found(self):
        """Test updating a nonexistent invoice returns 404."""
        resp = self.client.put('/api/invoices/9999', json={
            'customer_name': 'Ghost'
        }, headers=self.auth_header)
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_other_user(self):
        """Test that a user cannot update another user's invoice."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']
        other_header = self._register_second_user()

        resp = self.client.put(f'/api/invoices/{invoice_id}', json={
            'customer_name': 'Hacker'
        }, headers=other_header)
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_due_date(self):
        """Test updating the due_date field."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.put(f'/api/invoices/{invoice_id}', json={
            'due_date': '2027-06-15'
        }, headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['invoice']['due_date'], '2027-06-15')

    # --- Delete Invoice Tests ---

    def test_delete_invoice_success(self):
        """Test successful invoice deletion."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_header
        )
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['message'], 'Invoice deleted successfully')

        # Confirm it's gone
        get_resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_header
        )
        self.assertEqual(get_resp.status_code, 404)

    def test_delete_invoice_not_found(self):
        """Test deleting a nonexistent invoice returns 404."""
        resp = self.client.delete('/api/invoices/9999', headers=self.auth_header)
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_other_user(self):
        """Test that a user cannot delete another user's invoice."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']
        other_header = self._register_second_user()

        resp = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=other_header
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == '__main__':
    unittest.main()

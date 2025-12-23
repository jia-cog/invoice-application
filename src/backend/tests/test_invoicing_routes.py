#!/usr/bin/env python3
"""
Invoicing Routes Tests

Tests for invoice CRUD operations and related API endpoints.
"""

import sys
import os
import unittest
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Invoice, InvoiceItem
from flask_jwt_extended import create_access_token


class TestInvoicingRoutes(unittest.TestCase):
    """Test cases for invoicing route functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        db.drop_all()
        db.create_all()

        self.test_user = User(
            username='testuser',
            email='test@example.com',
            company_name='Test Company'
        )
        self.test_user.set_password('testpassword123')
        db.session.add(self.test_user)
        db.session.commit()

        self.access_token = create_access_token(identity=str(self.test_user.id))
        self.auth_headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        self.other_user = User(
            username='otheruser',
            email='other@example.com',
            company_name='Other Company'
        )
        self.other_user.set_password('otherpassword123')
        db.session.add(self.other_user)
        db.session.commit()

        self.valid_invoice_data = {
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'customer_address': '123 Main St, City, Country',
            'due_date': '2025-12-31',
            'tax_rate': 10.0,
            'notes': 'Test invoice notes',
            'status': 'draft',
            'items': [
                {
                    'description': 'Service A',
                    'quantity': 2,
                    'unit_price': 100.00
                },
                {
                    'description': 'Service B',
                    'quantity': 1,
                    'unit_price': 50.00
                }
            ]
        }

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_invoices_empty_list(self):
        """Test getting invoices when user has no invoices."""
        response = self.client.get(
            '/api/invoices/',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)

    def test_get_invoices_unauthorized(self):
        """Test getting invoices without authentication."""
        response = self.client.get('/api/invoices/')

        self.assertEqual(response.status_code, 401)

    def test_create_invoice_success(self):
        """Test successful invoice creation."""
        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Invoice created successfully')

        invoice = data['invoice']
        self.assertEqual(invoice['customer_name'], 'John Doe')
        self.assertEqual(invoice['customer_email'], 'john@example.com')
        self.assertEqual(invoice['status'], 'draft')
        self.assertEqual(len(invoice['items']), 2)
        self.assertTrue(invoice['invoice_number'].startswith('INV-'))

    def test_create_invoice_calculates_totals_correctly(self):
        """Test that invoice totals are calculated correctly."""
        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice = data['invoice']

        expected_subtotal = (2 * 100.00) + (1 * 50.00)
        expected_tax = expected_subtotal * 0.10
        expected_total = expected_subtotal + expected_tax

        self.assertEqual(invoice['subtotal'], expected_subtotal)
        self.assertEqual(invoice['tax_amount'], expected_tax)
        self.assertEqual(invoice['total_amount'], expected_total)

    def test_create_invoice_missing_customer_name(self):
        """Test invoice creation fails without customer_name."""
        invalid_data = self.valid_invoice_data.copy()
        del invalid_data['customer_name']

        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invalid_data)
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'])

    def test_create_invoice_missing_due_date(self):
        """Test invoice creation fails without due_date."""
        invalid_data = self.valid_invoice_data.copy()
        del invalid_data['due_date']

        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invalid_data)
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'])

    def test_create_invoice_missing_items(self):
        """Test invoice creation fails without items."""
        invalid_data = self.valid_invoice_data.copy()
        del invalid_data['items']

        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invalid_data)
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('items', data['error'])

    def test_create_invoice_item_missing_description(self):
        """Test invoice creation fails when item is missing description."""
        invalid_data = self.valid_invoice_data.copy()
        invalid_data['items'] = [
            {
                'quantity': 1,
                'unit_price': 100.00
            }
        ]

        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invalid_data)
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_create_invoice_item_missing_quantity(self):
        """Test invoice creation fails when item is missing quantity."""
        invalid_data = self.valid_invoice_data.copy()
        invalid_data['items'] = [
            {
                'description': 'Service',
                'unit_price': 100.00
            }
        ]

        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invalid_data)
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_create_invoice_item_missing_unit_price(self):
        """Test invoice creation fails when item is missing unit_price."""
        invalid_data = self.valid_invoice_data.copy()
        invalid_data['items'] = [
            {
                'description': 'Service',
                'quantity': 1
            }
        ]

        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invalid_data)
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_create_invoice_unauthorized(self):
        """Test invoice creation without authentication."""
        response = self.client.post(
            '/api/invoices/',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(self.valid_invoice_data)
        )

        self.assertEqual(response.status_code, 401)

    def test_get_single_invoice_success(self):
        """Test getting a single invoice by ID."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice_id)
        self.assertEqual(data['invoice']['customer_name'], 'John Doe')

    def test_get_single_invoice_not_found(self):
        """Test getting a non-existent invoice."""
        response = self.client.get(
            '/api/invoices/99999',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')

    def test_get_single_invoice_unauthorized(self):
        """Test getting invoice without authentication."""
        response = self.client.get('/api/invoices/1')

        self.assertEqual(response.status_code, 401)

    def test_get_invoice_belongs_to_another_user(self):
        """Test that users cannot access other users' invoices."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        other_token = create_access_token(identity=str(self.other_user.id))
        other_headers = {
            'Authorization': f'Bearer {other_token}',
            'Content-Type': 'application/json'
        }

        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=other_headers
        )

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')

    def test_update_invoice_success(self):
        """Test successful invoice update."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        update_data = {
            'customer_name': 'Jane Doe',
            'status': 'sent'
        }

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps(update_data)
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Jane Doe')
        self.assertEqual(data['invoice']['status'], 'sent')
        self.assertEqual(data['message'], 'Invoice updated successfully')

    def test_update_invoice_with_new_items(self):
        """Test updating invoice with new items."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        update_data = {
            'items': [
                {
                    'description': 'New Service',
                    'quantity': 3,
                    'unit_price': 200.00
                }
            ]
        }

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps(update_data)
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        invoice = data['invoice']

        self.assertEqual(len(invoice['items']), 1)
        self.assertEqual(invoice['items'][0]['description'], 'New Service')

        expected_subtotal = 3 * 200.00
        expected_tax = expected_subtotal * 0.10
        expected_total = expected_subtotal + expected_tax

        self.assertEqual(invoice['subtotal'], expected_subtotal)
        self.assertEqual(invoice['tax_amount'], expected_tax)
        self.assertEqual(invoice['total_amount'], expected_total)

    def test_update_invoice_not_found(self):
        """Test updating a non-existent invoice."""
        update_data = {'customer_name': 'Jane Doe'}

        response = self.client.put(
            '/api/invoices/99999',
            headers=self.auth_headers,
            data=json.dumps(update_data)
        )

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')

    def test_update_invoice_unauthorized(self):
        """Test updating invoice without authentication."""
        response = self.client.put(
            '/api/invoices/1',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'customer_name': 'Jane Doe'})
        )

        self.assertEqual(response.status_code, 401)

    def test_update_invoice_belongs_to_another_user(self):
        """Test that users cannot update other users' invoices."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        other_token = create_access_token(identity=str(self.other_user.id))
        other_headers = {
            'Authorization': f'Bearer {other_token}',
            'Content-Type': 'application/json'
        }

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=other_headers,
            data=json.dumps({'customer_name': 'Hacker'})
        )

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')

    def test_delete_invoice_success(self):
        """Test successful invoice deletion."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invoice deleted successfully')

        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        self.assertEqual(get_response.status_code, 404)

    def test_delete_invoice_not_found(self):
        """Test deleting a non-existent invoice."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')

    def test_delete_invoice_unauthorized(self):
        """Test deleting invoice without authentication."""
        response = self.client.delete('/api/invoices/1')

        self.assertEqual(response.status_code, 401)

    def test_delete_invoice_belongs_to_another_user(self):
        """Test that users cannot delete other users' invoices."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        other_token = create_access_token(identity=str(self.other_user.id))
        other_headers = {
            'Authorization': f'Bearer {other_token}',
            'Content-Type': 'application/json'
        }

        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=other_headers
        )

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')

        verify_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        self.assertEqual(verify_response.status_code, 200)

    def test_get_invoices_returns_only_user_invoices(self):
        """Test that get invoices only returns invoices for the authenticated user."""
        self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )

        other_token = create_access_token(identity=str(self.other_user.id))
        other_headers = {
            'Authorization': f'Bearer {other_token}',
            'Content-Type': 'application/json'
        }

        other_invoice_data = self.valid_invoice_data.copy()
        other_invoice_data['customer_name'] = 'Other Customer'
        self.client.post(
            '/api/invoices/',
            headers=other_headers,
            data=json.dumps(other_invoice_data)
        )

        response = self.client.get(
            '/api/invoices/',
            headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'John Doe')

    def test_create_invoice_with_zero_tax_rate(self):
        """Test creating invoice with zero tax rate."""
        invoice_data = self.valid_invoice_data.copy()
        invoice_data['tax_rate'] = 0.0

        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invoice_data)
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice = data['invoice']

        self.assertEqual(invoice['tax_rate'], 0.0)
        self.assertEqual(invoice['tax_amount'], 0.0)
        self.assertEqual(invoice['subtotal'], invoice['total_amount'])

    def test_create_invoice_with_default_status(self):
        """Test that invoice defaults to 'draft' status if not provided."""
        invoice_data = self.valid_invoice_data.copy()
        del invoice_data['status']

        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invoice_data)
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['status'], 'draft')

    def test_update_invoice_partial_fields(self):
        """Test updating invoice with only some fields."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        update_data = {
            'notes': 'Updated notes only'
        }

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps(update_data)
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        invoice = data['invoice']

        self.assertEqual(invoice['notes'], 'Updated notes only')
        self.assertEqual(invoice['customer_name'], 'John Doe')
        self.assertEqual(invoice['status'], 'draft')

    def test_update_invoice_due_date(self):
        """Test updating invoice due date."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        update_data = {
            'due_date': '2026-01-15'
        }

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps(update_data)
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['due_date'], '2026-01-15')

    def test_create_multiple_invoices(self):
        """Test creating multiple invoices for the same user."""
        response1 = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        self.assertEqual(response1.status_code, 201)

        second_invoice_data = self.valid_invoice_data.copy()
        second_invoice_data['customer_name'] = 'Jane Smith'

        response2 = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(second_invoice_data)
        )
        self.assertEqual(response2.status_code, 201)

        list_response = self.client.get(
            '/api/invoices/',
            headers=self.auth_headers
        )

        self.assertEqual(list_response.status_code, 200)
        data = json.loads(list_response.data)
        self.assertEqual(len(data['invoices']), 2)

    def test_invoice_item_total_calculation(self):
        """Test that individual item totals are calculated correctly."""
        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        items = data['invoice']['items']

        self.assertEqual(items[0]['total'], 200.00)
        self.assertEqual(items[1]['total'], 50.00)

    def test_update_invoice_tax_rate(self):
        """Test updating invoice tax rate recalculates totals."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        update_data = {
            'tax_rate': 20.0
        }

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps(update_data)
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        invoice = data['invoice']

        expected_subtotal = 250.00
        expected_tax = expected_subtotal * 0.20
        expected_total = expected_subtotal + expected_tax

        self.assertEqual(invoice['tax_rate'], 20.0)
        self.assertEqual(invoice['tax_amount'], expected_tax)
        self.assertEqual(invoice['total_amount'], expected_total)

    def test_create_invoice_with_single_item(self):
        """Test creating invoice with a single item."""
        invoice_data = self.valid_invoice_data.copy()
        invoice_data['items'] = [
            {
                'description': 'Single Service',
                'quantity': 1,
                'unit_price': 500.00
            }
        ]

        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invoice_data)
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoice']['items']), 1)
        self.assertEqual(data['invoice']['subtotal'], 500.00)

    def test_update_all_invoice_fields(self):
        """Test updating all invoice fields at once."""
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.valid_invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']

        update_data = {
            'customer_name': 'Updated Customer',
            'customer_email': 'updated@example.com',
            'customer_address': '456 New St',
            'due_date': '2026-06-30',
            'tax_rate': 15.0,
            'notes': 'Updated notes',
            'status': 'paid',
            'items': [
                {
                    'description': 'Updated Service',
                    'quantity': 5,
                    'unit_price': 75.00
                }
            ]
        }

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps(update_data)
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        invoice = data['invoice']

        self.assertEqual(invoice['customer_name'], 'Updated Customer')
        self.assertEqual(invoice['customer_email'], 'updated@example.com')
        self.assertEqual(invoice['customer_address'], '456 New St')
        self.assertEqual(invoice['due_date'], '2026-06-30')
        self.assertEqual(invoice['tax_rate'], 15.0)
        self.assertEqual(invoice['notes'], 'Updated notes')
        self.assertEqual(invoice['status'], 'paid')
        self.assertEqual(len(invoice['items']), 1)


def run_invoicing_tests():
    """Run all invoicing tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoicingRoutes)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_invoicing_tests()
    if success:
        print("\nAll invoicing route tests passed!")
        sys.exit(0)
    else:
        print("\nSome invoicing route tests failed!")
        sys.exit(1)

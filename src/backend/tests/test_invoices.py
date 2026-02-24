#!/usr/bin/env python3
"""
Invoice Endpoint Tests

Comprehensive tests for the invoice endpoint functionality including:
- Invoice creation with customer details and line items
- Authentication and user data isolation
- Auto-generated invoice numbers
- Status tracking
- Automatic calculation of subtotals, tax, and totals
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from models import db, User, Invoice, InvoiceItem
from routes.invoices import invoices_bp
from routes.auth import auth_bp
from config import Config


class TestConfig(Config):
    """Test configuration with in-memory SQLite database."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True


class TestInvoiceEndpoint(unittest.TestCase):
    """Test cases for invoice endpoint functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)

        db.init_app(self.app)
        self.jwt = JWTManager(self.app)

        self.app.register_blueprint(invoices_bp, url_prefix='/api/invoices')
        self.app.register_blueprint(auth_bp, url_prefix='/api/auth')

        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

        # Create test users
        self.user1 = User(username='testuser1', email='test1@example.com')
        self.user1.set_password('password123')
        db.session.add(self.user1)

        self.user2 = User(username='testuser2', email='test2@example.com')
        self.user2.set_password('password456')
        db.session.add(self.user2)

        db.session.commit()

        # Create JWT tokens for both users
        self.token1 = create_access_token(identity=str(self.user1.id))
        self.token2 = create_access_token(identity=str(self.user2.id))

        self.auth_headers1 = {'Authorization': f'Bearer {self.token1}'}
        self.auth_headers2 = {'Authorization': f'Bearer {self.token2}'}

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def get_valid_invoice_data(self):
        """Return valid invoice data for testing."""
        return {
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'customer_address': '123 Main St, City, Country',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 10.0,
            'notes': 'Test invoice notes',
            'items': [
                {
                    'description': 'Web Development Services',
                    'quantity': 10,
                    'unit_price': 100.00
                },
                {
                    'description': 'Consulting Hours',
                    'quantity': 5,
                    'unit_price': 150.00
                }
            ]
        }

    # ==================== Authentication Tests ====================

    def test_get_invoices_requires_authentication(self):
        """Test that GET /api/invoices/ requires authentication."""
        response = self.client.get('/api/invoices/')
        self.assertEqual(response.status_code, 401)

    def test_get_single_invoice_requires_authentication(self):
        """Test that GET /api/invoices/<id> requires authentication."""
        response = self.client.get('/api/invoices/1')
        self.assertEqual(response.status_code, 401)

    def test_create_invoice_requires_authentication(self):
        """Test that POST /api/invoices/ requires authentication."""
        response = self.client.post('/api/invoices/', json=self.get_valid_invoice_data())
        self.assertEqual(response.status_code, 401)

    def test_update_invoice_requires_authentication(self):
        """Test that PUT /api/invoices/<id> requires authentication."""
        response = self.client.put('/api/invoices/1', json={'customer_name': 'Updated'})
        self.assertEqual(response.status_code, 401)

    def test_delete_invoice_requires_authentication(self):
        """Test that DELETE /api/invoices/<id> requires authentication."""
        response = self.client.delete('/api/invoices/1')
        self.assertEqual(response.status_code, 401)

    def test_invalid_token_rejected(self):
        """Test that invalid JWT tokens are rejected."""
        invalid_headers = {'Authorization': 'Bearer invalid.token.here'}
        response = self.client.get('/api/invoices/', headers=invalid_headers)
        # Flask-JWT-Extended returns 422 for malformed tokens, 401 for invalid/expired
        self.assertIn(response.status_code, [401, 422])

    # ==================== Invoice Creation Tests ====================

    def test_create_invoice_success(self):
        """Test successful invoice creation with valid data."""
        data = self.get_valid_invoice_data()
        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        json_data = response.get_json()
        self.assertIn('invoice', json_data)
        self.assertIn('message', json_data)
        self.assertEqual(json_data['message'], 'Invoice created successfully')

    def test_create_invoice_generates_unique_invoice_number(self):
        """Test that invoice creation generates a unique invoice number with correct format."""
        data = self.get_valid_invoice_data()
        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']

        # Verify invoice number format: INV-YYYYMMDD-XXXXXXXX
        invoice_number = invoice['invoice_number']
        pattern = r'^INV-\d{8}-[A-Z0-9]{8}$'
        self.assertRegex(invoice_number, pattern)

        # Verify the date portion is today's date
        today = datetime.now().strftime('%Y%m%d')
        self.assertIn(today, invoice_number)

    def test_create_multiple_invoices_unique_numbers(self):
        """Test that multiple invoices get unique invoice numbers."""
        data = self.get_valid_invoice_data()

        response1 = self.client.post('/api/invoices/', json=data, headers=self.auth_headers1)
        response2 = self.client.post('/api/invoices/', json=data, headers=self.auth_headers1)

        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)

        invoice_number1 = response1.get_json()['invoice']['invoice_number']
        invoice_number2 = response2.get_json()['invoice']['invoice_number']

        self.assertNotEqual(invoice_number1, invoice_number2)

    def test_create_invoice_default_status_is_draft(self):
        """Test that new invoices default to 'draft' status."""
        data = self.get_valid_invoice_data()
        if 'status' in data:
            del data['status']

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']
        self.assertEqual(invoice['status'], 'draft')

    def test_create_invoice_with_custom_status(self):
        """Test creating invoice with custom status."""
        data = self.get_valid_invoice_data()
        data['status'] = 'sent'

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']
        self.assertEqual(invoice['status'], 'sent')

    def test_create_invoice_calculates_subtotal(self):
        """Test that invoice creation correctly calculates subtotal from items."""
        data = self.get_valid_invoice_data()
        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']

        # Expected: (10 * 100) + (5 * 150) = 1000 + 750 = 1750
        expected_subtotal = 1750.0
        self.assertEqual(invoice['subtotal'], expected_subtotal)

    def test_create_invoice_calculates_tax_amount(self):
        """Test that invoice creation correctly calculates tax amount."""
        data = self.get_valid_invoice_data()
        data['tax_rate'] = 10.0

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']

        # Expected tax: 1750 * 0.10 = 175
        expected_tax = 175.0
        self.assertEqual(invoice['tax_amount'], expected_tax)

    def test_create_invoice_calculates_total_amount(self):
        """Test that invoice creation correctly calculates total amount."""
        data = self.get_valid_invoice_data()
        data['tax_rate'] = 10.0

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']

        # Expected total: 1750 + 175 = 1925
        expected_total = 1925.0
        self.assertEqual(invoice['total_amount'], expected_total)

    def test_create_invoice_with_zero_tax_rate(self):
        """Test invoice creation with zero tax rate."""
        data = self.get_valid_invoice_data()
        data['tax_rate'] = 0.0

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']

        self.assertEqual(invoice['tax_rate'], 0.0)
        self.assertEqual(invoice['tax_amount'], 0.0)
        self.assertEqual(invoice['subtotal'], invoice['total_amount'])

    def test_create_invoice_includes_items(self):
        """Test that created invoice includes all line items."""
        data = self.get_valid_invoice_data()
        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']

        self.assertEqual(len(invoice['items']), 2)

        # Verify first item
        item1 = invoice['items'][0]
        self.assertEqual(item1['description'], 'Web Development Services')
        self.assertEqual(item1['quantity'], 10)
        self.assertEqual(item1['unit_price'], 100.0)
        self.assertEqual(item1['total'], 1000.0)

        # Verify second item
        item2 = invoice['items'][1]
        self.assertEqual(item2['description'], 'Consulting Hours')
        self.assertEqual(item2['quantity'], 5)
        self.assertEqual(item2['unit_price'], 150.0)
        self.assertEqual(item2['total'], 750.0)

    def test_create_invoice_stores_customer_details(self):
        """Test that invoice stores all customer details correctly."""
        data = self.get_valid_invoice_data()
        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']

        self.assertEqual(invoice['customer_name'], 'John Doe')
        self.assertEqual(invoice['customer_email'], 'john@example.com')
        self.assertEqual(invoice['customer_address'], '123 Main St, City, Country')

    # ==================== Validation Tests ====================

    def test_create_invoice_requires_customer_name(self):
        """Test that customer_name is required for invoice creation."""
        data = self.get_valid_invoice_data()
        del data['customer_name']

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('customer_name is required', response.get_json()['error'])

    def test_create_invoice_requires_due_date(self):
        """Test that due_date is required for invoice creation."""
        data = self.get_valid_invoice_data()
        del data['due_date']

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('due_date is required', response.get_json()['error'])

    def test_create_invoice_requires_items(self):
        """Test that items are required for invoice creation."""
        data = self.get_valid_invoice_data()
        del data['items']

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('items is required', response.get_json()['error'])

    def test_create_invoice_requires_item_description(self):
        """Test that each item must have a description."""
        data = self.get_valid_invoice_data()
        data['items'] = [{'quantity': 1, 'unit_price': 100}]

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('description', response.get_json()['error'].lower())

    def test_create_invoice_requires_item_quantity(self):
        """Test that each item must have a quantity."""
        data = self.get_valid_invoice_data()
        data['items'] = [{'description': 'Test', 'unit_price': 100}]

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('quantity', response.get_json()['error'].lower())

    def test_create_invoice_requires_item_unit_price(self):
        """Test that each item must have a unit_price."""
        data = self.get_valid_invoice_data()
        data['items'] = [{'description': 'Test', 'quantity': 1}]

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('unit_price', response.get_json()['error'].lower())

    # ==================== Get Invoices Tests ====================

    def test_get_invoices_empty_list(self):
        """Test getting invoices when user has none."""
        response = self.client.get('/api/invoices/', headers=self.auth_headers1)

        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn('invoices', json_data)
        self.assertEqual(len(json_data['invoices']), 0)

    def test_get_invoices_returns_user_invoices(self):
        """Test that GET /api/invoices/ returns all invoices for the user."""
        # Create two invoices for user1
        data = self.get_valid_invoice_data()
        self.client.post('/api/invoices/', json=data, headers=self.auth_headers1)
        self.client.post('/api/invoices/', json=data, headers=self.auth_headers1)

        response = self.client.get('/api/invoices/', headers=self.auth_headers1)

        self.assertEqual(response.status_code, 200)
        invoices = response.get_json()['invoices']
        self.assertEqual(len(invoices), 2)

    def test_get_invoices_ordered_by_created_at_desc(self):
        """Test that invoices are returned in descending order by created_at."""
        data = self.get_valid_invoice_data()

        # Create first invoice
        response1 = self.client.post('/api/invoices/', json=data, headers=self.auth_headers1)
        invoice1_id = response1.get_json()['invoice']['id']

        # Create second invoice
        response2 = self.client.post('/api/invoices/', json=data, headers=self.auth_headers1)
        invoice2_id = response2.get_json()['invoice']['id']

        # Get all invoices
        response = self.client.get('/api/invoices/', headers=self.auth_headers1)
        invoices = response.get_json()['invoices']

        # Most recent should be first
        self.assertEqual(invoices[0]['id'], invoice2_id)
        self.assertEqual(invoices[1]['id'], invoice1_id)

    # ==================== Get Single Invoice Tests ====================

    def test_get_single_invoice_success(self):
        """Test getting a single invoice by ID."""
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 200)
        invoice = response.get_json()['invoice']
        self.assertEqual(invoice['id'], invoice_id)
        self.assertEqual(invoice['customer_name'], 'John Doe')

    def test_get_single_invoice_not_found(self):
        """Test getting a non-existent invoice returns 404."""
        response = self.client.get('/api/invoices/99999', headers=self.auth_headers1)

        self.assertEqual(response.status_code, 404)
        self.assertIn('Invoice not found', response.get_json()['error'])

    # ==================== User Data Isolation Tests ====================

    def test_user_cannot_access_other_users_invoices_list(self):
        """Test that users can only see their own invoices in the list."""
        # Create invoice for user1
        data = self.get_valid_invoice_data()
        self.client.post('/api/invoices/', json=data, headers=self.auth_headers1)

        # User2 should see empty list
        response = self.client.get('/api/invoices/', headers=self.auth_headers2)

        self.assertEqual(response.status_code, 200)
        invoices = response.get_json()['invoices']
        self.assertEqual(len(invoices), 0)

    def test_user_cannot_access_other_users_single_invoice(self):
        """Test that users cannot access another user's invoice by ID."""
        # Create invoice for user1
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        # User2 tries to access user1's invoice
        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers2
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn('Invoice not found', response.get_json()['error'])

    def test_user_cannot_update_other_users_invoice(self):
        """Test that users cannot update another user's invoice."""
        # Create invoice for user1
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        # User2 tries to update user1's invoice
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json={'customer_name': 'Hacked Name'},
            headers=self.auth_headers2
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn('Invoice not found', response.get_json()['error'])

    def test_user_cannot_delete_other_users_invoice(self):
        """Test that users cannot delete another user's invoice."""
        # Create invoice for user1
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        # User2 tries to delete user1's invoice
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers2
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn('Invoice not found', response.get_json()['error'])

        # Verify invoice still exists for user1
        verify_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers1
        )
        self.assertEqual(verify_response.status_code, 200)

    def test_multiple_users_independent_invoices(self):
        """Test that multiple users can have independent invoices."""
        data = self.get_valid_invoice_data()

        # Create invoices for both users
        self.client.post('/api/invoices/', json=data, headers=self.auth_headers1)
        self.client.post('/api/invoices/', json=data, headers=self.auth_headers1)

        data['customer_name'] = 'User2 Customer'
        self.client.post('/api/invoices/', json=data, headers=self.auth_headers2)

        # Verify user1 sees only their 2 invoices
        response1 = self.client.get('/api/invoices/', headers=self.auth_headers1)
        invoices1 = response1.get_json()['invoices']
        self.assertEqual(len(invoices1), 2)
        for inv in invoices1:
            self.assertEqual(inv['customer_name'], 'John Doe')

        # Verify user2 sees only their 1 invoice
        response2 = self.client.get('/api/invoices/', headers=self.auth_headers2)
        invoices2 = response2.get_json()['invoices']
        self.assertEqual(len(invoices2), 1)
        self.assertEqual(invoices2[0]['customer_name'], 'User2 Customer')

    # ==================== Update Invoice Tests ====================

    def test_update_invoice_customer_name(self):
        """Test updating invoice customer name."""
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json={'customer_name': 'Jane Smith'},
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 200)
        invoice = response.get_json()['invoice']
        self.assertEqual(invoice['customer_name'], 'Jane Smith')

    def test_update_invoice_status(self):
        """Test updating invoice status through all valid states."""
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        # Test all status transitions
        statuses = ['sent', 'paid', 'overdue', 'draft']
        for status in statuses:
            response = self.client.put(
                f'/api/invoices/{invoice_id}',
                json={'status': status},
                headers=self.auth_headers1
            )

            self.assertEqual(response.status_code, 200)
            invoice = response.get_json()['invoice']
            self.assertEqual(invoice['status'], status)

    def test_update_invoice_items_recalculates_totals(self):
        """Test that updating items recalculates totals."""
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        # Update with new items
        new_items = [
            {'description': 'New Service', 'quantity': 2, 'unit_price': 500.00}
        ]

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json={'items': new_items},
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 200)
        invoice = response.get_json()['invoice']

        # New subtotal: 2 * 500 = 1000
        # Tax (10%): 100
        # Total: 1100
        self.assertEqual(invoice['subtotal'], 1000.0)
        self.assertEqual(invoice['tax_amount'], 100.0)
        self.assertEqual(invoice['total_amount'], 1100.0)
        self.assertEqual(len(invoice['items']), 1)

    def test_update_invoice_tax_rate_recalculates_totals(self):
        """Test that updating tax rate recalculates totals."""
        data = self.get_valid_invoice_data()
        data['tax_rate'] = 10.0
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        # Update tax rate to 20%
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json={'tax_rate': 20.0},
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 200)
        invoice = response.get_json()['invoice']

        # Subtotal: 1750
        # Tax (20%): 350
        # Total: 2100
        self.assertEqual(invoice['tax_rate'], 20.0)
        self.assertEqual(invoice['tax_amount'], 350.0)
        self.assertEqual(invoice['total_amount'], 2100.0)

    def test_update_invoice_not_found(self):
        """Test updating a non-existent invoice returns 404."""
        response = self.client.put(
            '/api/invoices/99999',
            json={'customer_name': 'Test'},
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn('Invoice not found', response.get_json()['error'])

    def test_update_invoice_multiple_fields(self):
        """Test updating multiple invoice fields at once."""
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        update_data = {
            'customer_name': 'Updated Customer',
            'customer_email': 'updated@example.com',
            'customer_address': 'New Address',
            'status': 'sent',
            'notes': 'Updated notes'
        }

        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json=update_data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 200)
        invoice = response.get_json()['invoice']

        self.assertEqual(invoice['customer_name'], 'Updated Customer')
        self.assertEqual(invoice['customer_email'], 'updated@example.com')
        self.assertEqual(invoice['customer_address'], 'New Address')
        self.assertEqual(invoice['status'], 'sent')
        self.assertEqual(invoice['notes'], 'Updated notes')

    def test_update_invoice_due_date(self):
        """Test updating invoice due date."""
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        new_due_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json={'due_date': new_due_date},
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 200)
        invoice = response.get_json()['invoice']
        self.assertEqual(invoice['due_date'], new_due_date)

    # ==================== Delete Invoice Tests ====================

    def test_delete_invoice_success(self):
        """Test successful invoice deletion."""
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Invoice deleted successfully', response.get_json()['message'])

        # Verify invoice is deleted
        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers1
        )
        self.assertEqual(get_response.status_code, 404)

    def test_delete_invoice_not_found(self):
        """Test deleting a non-existent invoice returns 404."""
        response = self.client.delete('/api/invoices/99999', headers=self.auth_headers1)

        self.assertEqual(response.status_code, 404)
        self.assertIn('Invoice not found', response.get_json()['error'])

    def test_delete_invoice_removes_items(self):
        """Test that deleting an invoice also removes its items."""
        data = self.get_valid_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )
        invoice_id = create_response.get_json()['invoice']['id']

        # Verify items exist
        invoice = Invoice.query.get(invoice_id)
        self.assertEqual(len(invoice.items), 2)

        # Delete invoice
        self.client.delete(f'/api/invoices/{invoice_id}', headers=self.auth_headers1)

        # Verify items are deleted (cascade)
        items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items), 0)

    # ==================== Edge Case Tests ====================

    def test_create_invoice_with_single_item(self):
        """Test creating invoice with a single line item."""
        data = self.get_valid_invoice_data()
        data['items'] = [{'description': 'Single Item', 'quantity': 1, 'unit_price': 99.99}]

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']
        self.assertEqual(len(invoice['items']), 1)
        self.assertEqual(invoice['subtotal'], 99.99)

    def test_create_invoice_with_decimal_quantities(self):
        """Test creating invoice with decimal quantities."""
        data = self.get_valid_invoice_data()
        data['items'] = [{'description': 'Hourly Work', 'quantity': 2.5, 'unit_price': 100.00}]

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']
        self.assertEqual(invoice['items'][0]['quantity'], 2.5)
        self.assertEqual(invoice['items'][0]['total'], 250.0)

    def test_create_invoice_without_optional_fields(self):
        """Test creating invoice without optional fields."""
        data = {
            'customer_name': 'Minimal Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Service', 'quantity': 1, 'unit_price': 100}]
        }

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']

        # Optional fields should have default values
        self.assertEqual(invoice['customer_email'], '')
        self.assertEqual(invoice['customer_address'], '')
        self.assertEqual(invoice['tax_rate'], 0.0)
        self.assertEqual(invoice['notes'], '')
        self.assertEqual(invoice['status'], 'draft')

    def test_create_invoice_with_many_items(self):
        """Test creating invoice with many line items."""
        data = self.get_valid_invoice_data()
        data['items'] = [
            {'description': f'Item {i}', 'quantity': i, 'unit_price': 10.0}
            for i in range(1, 11)
        ]

        response = self.client.post(
            '/api/invoices/',
            json=data,
            headers=self.auth_headers1
        )

        self.assertEqual(response.status_code, 201)
        invoice = response.get_json()['invoice']
        self.assertEqual(len(invoice['items']), 10)

        # Verify subtotal: sum of (i * 10) for i in 1..10 = 10 * (1+2+...+10) = 10 * 55 = 550
        self.assertEqual(invoice['subtotal'], 550.0)


def run_invoice_tests():
    """Run all invoice tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoiceEndpoint)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_invoice_tests()
    if success:
        print("\nAll invoice endpoint tests passed!")
        sys.exit(0)
    else:
        print("\nSome invoice endpoint tests failed!")
        sys.exit(1)

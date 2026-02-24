#!/usr/bin/env python3
"""
Invoice API Routes Tests

Tests for all invoice CRUD operations including authentication,
authorization, and business logic validation.
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from app import create_app
from models import db, User, Invoice, InvoiceItem
from config import Config


class TestConfig(Config):
    """Test configuration with in-memory SQLite database."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for invoice API routes."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        
        # Initialize extensions
        db.init_app(self.app)
        self.jwt = JWTManager(self.app)
        
        # Register blueprints
        from routes.invoices import invoices_bp
        self.app.register_blueprint(invoices_bp, url_prefix='/api/invoices')
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create all tables
        db.create_all()
        
        # Create test users
        self.user1 = User(
            username='testuser1',
            email='test1@example.com',
            company_name='Test Company 1'
        )
        self.user1.set_password('password123')
        
        self.user2 = User(
            username='testuser2',
            email='test2@example.com',
            company_name='Test Company 2'
        )
        self.user2.set_password('password456')
        
        db.session.add(self.user1)
        db.session.add(self.user2)
        db.session.commit()
        
        # Create test client
        self.client = self.app.test_client()
        
        # Generate JWT tokens for test users
        self.token1 = create_access_token(identity=str(self.user1.id))
        self.token2 = create_access_token(identity=str(self.user2.id))
        
        # Auth headers
        self.auth_headers1 = {'Authorization': f'Bearer {self.token1}'}
        self.auth_headers2 = {'Authorization': f'Bearer {self.token2}'}
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _create_test_invoice(self, user_id, customer_name='Test Customer', status='draft'):
        """Helper method to create a test invoice with items."""
        invoice = Invoice(
            invoice_number=f'INV-TEST-{datetime.now().timestamp()}',
            user_id=user_id,
            customer_name=customer_name,
            customer_email='customer@example.com',
            customer_address='123 Test St',
            due_date=(datetime.now() + timedelta(days=30)).date(),
            tax_rate=10.0,
            status=status
        )
        db.session.add(invoice)
        db.session.flush()
        
        # Add test items
        item1 = InvoiceItem(
            invoice_id=invoice.id,
            description='Test Item 1',
            quantity=2,
            unit_price=100.0
        )
        item1.calculate_total()
        
        item2 = InvoiceItem(
            invoice_id=invoice.id,
            description='Test Item 2',
            quantity=1,
            unit_price=50.0
        )
        item2.calculate_total()
        
        db.session.add(item1)
        db.session.add(item2)
        
        invoice.calculate_totals()
        db.session.commit()
        
        return invoice

    # ==================== GET /api/invoices/ Tests ====================
    
    def test_get_invoices_authenticated(self):
        """Test GET / returns invoices for authenticated user."""
        # Create test invoices for user1
        self._create_test_invoice(self.user1.id, 'Customer A')
        self._create_test_invoice(self.user1.id, 'Customer B')
        
        response = self.client.get('/api/invoices/', headers=self.auth_headers1)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_invoices_empty_list(self):
        """Test GET / returns empty list when no invoices exist."""
        response = self.client.get('/api/invoices/', headers=self.auth_headers1)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_user_isolation(self):
        """Test GET / only returns invoices belonging to authenticated user."""
        # Create invoices for both users
        self._create_test_invoice(self.user1.id, 'User1 Customer')
        self._create_test_invoice(self.user2.id, 'User2 Customer')
        
        # User1 should only see their invoice
        response = self.client.get('/api/invoices/', headers=self.auth_headers1)
        data = response.get_json()
        
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'User1 Customer')
    
    def test_get_invoices_unauthenticated(self):
        """Test GET / returns 401 without JWT token."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_invoices_invalid_token(self):
        """Test GET / rejects invalid JWT token."""
        headers = {'Authorization': 'Bearer invalid-token'}
        response = self.client.get('/api/invoices/', headers=headers)
        
        # Flask-JWT-Extended returns 422 for malformed tokens (unprocessable entity)
        # and 401 for missing/expired tokens
        self.assertIn(response.status_code, [401, 422])

    # ==================== GET /api/invoices/<id> Tests ====================
    
    def test_get_invoice_by_id_success(self):
        """Test GET /<id> returns invoice for valid ID."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.get(f'/api/invoices/{invoice.id}', headers=self.auth_headers1)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice.id)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_get_invoice_by_id_not_found(self):
        """Test GET /<id> returns 404 for non-existent invoice."""
        response = self.client.get('/api/invoices/99999', headers=self.auth_headers1)
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_by_id_other_user(self):
        """Test GET /<id> returns 404 for invoice belonging to another user."""
        # Create invoice for user2
        invoice = self._create_test_invoice(self.user2.id)
        
        # Try to access with user1's token
        response = self.client.get(f'/api/invoices/{invoice.id}', headers=self.auth_headers1)
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_by_id_unauthenticated(self):
        """Test GET /<id> returns 401 without JWT token."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.get(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_invoice_includes_items(self):
        """Test GET /<id> returns invoice with items."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.get(f'/api/invoices/{invoice.id}', headers=self.auth_headers1)
        
        data = response.get_json()
        self.assertIn('items', data['invoice'])
        self.assertEqual(len(data['invoice']['items']), 2)

    # ==================== POST /api/invoices/ Tests ====================
    
    def test_create_invoice_valid_data(self):
        """Test POST / creates invoice with valid data."""
        invoice_data = {
            'customer_name': 'New Customer',
            'customer_email': 'new@example.com',
            'customer_address': '456 New St',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 8.5,
            'items': [
                {'description': 'Service A', 'quantity': 3, 'unit_price': 150.0},
                {'description': 'Service B', 'quantity': 1, 'unit_price': 200.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'New Customer')
        self.assertIn('message', data)
    
    def test_create_invoice_generates_invoice_number(self):
        """Test POST / generates unique invoice number."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        data = response.get_json()
        self.assertTrue(data['invoice']['invoice_number'].startswith('INV-'))
    
    def test_create_invoice_calculates_totals(self):
        """Test POST / correctly calculates invoice totals."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 10.0,
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 100.0},  # 200
                {'description': 'Item 2', 'quantity': 3, 'unit_price': 50.0}    # 150
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        data = response.get_json()
        invoice = data['invoice']
        
        # Subtotal: 200 + 150 = 350
        self.assertEqual(invoice['subtotal'], 350.0)
        # Tax: 350 * 0.10 = 35
        self.assertEqual(invoice['tax_amount'], 35.0)
        # Total: 350 + 35 = 385
        self.assertEqual(invoice['total_amount'], 385.0)
    
    def test_create_invoice_missing_customer_name(self):
        """Test POST / returns 400 when customer_name is missing."""
        invoice_data = {
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'])
    
    def test_create_invoice_missing_due_date(self):
        """Test POST / returns 400 when due_date is missing."""
        invoice_data = {
            'customer_name': 'Customer',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'])
    
    def test_create_invoice_missing_items(self):
        """Test POST / returns 400 when items is missing."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('items', data['error'])
    
    def test_create_invoice_invalid_item_missing_description(self):
        """Test POST / returns 400 when item is missing description."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_quantity(self):
        """Test POST / returns 400 when item is missing quantity."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_unit_price(self):
        """Test POST / returns 400 when item is missing unit_price."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_unauthenticated(self):
        """Test POST / returns 401 without JWT token."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post('/api/invoices/', json=invoice_data)
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_invoice_default_status(self):
        """Test POST / creates invoice with default 'draft' status."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        data = response.get_json()
        self.assertEqual(data['invoice']['status'], 'draft')
    
    def test_create_invoice_custom_status(self):
        """Test POST / creates invoice with custom status."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'status': 'sent',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.auth_headers1
        )
        
        data = response.get_json()
        self.assertEqual(data['invoice']['status'], 'sent')

    # ==================== PUT /api/invoices/<id> Tests ====================
    
    def test_update_invoice_success(self):
        """Test PUT /<id> updates invoice fields."""
        invoice = self._create_test_invoice(self.user1.id)
        
        update_data = {
            'customer_name': 'Updated Customer',
            'status': 'sent'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'sent')
    
    def test_update_invoice_not_found(self):
        """Test PUT /<id> returns 404 for non-existent invoice."""
        update_data = {'customer_name': 'Updated'}
        
        response = self.client.put(
            '/api/invoices/99999',
            json=update_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_other_user(self):
        """Test PUT /<id> returns 404 for invoice belonging to another user."""
        invoice = self._create_test_invoice(self.user2.id)
        
        update_data = {'customer_name': 'Hacked'}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_invoice_items(self):
        """Test PUT /<id> updates invoice items and recalculates totals."""
        invoice = self._create_test_invoice(self.user1.id)
        
        update_data = {
            'items': [
                {'description': 'New Item', 'quantity': 5, 'unit_price': 200.0}
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        # Should have only 1 item now
        self.assertEqual(len(data['invoice']['items']), 1)
        # Subtotal: 5 * 200 = 1000
        self.assertEqual(data['invoice']['subtotal'], 1000.0)
    
    def test_update_invoice_unauthenticated(self):
        """Test PUT /<id> returns 401 without JWT token."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json={'customer_name': 'Updated'}
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_update_invoice_partial_update(self):
        """Test PUT /<id> allows partial updates."""
        invoice = self._create_test_invoice(self.user1.id)
        original_customer = invoice.customer_name
        
        update_data = {'notes': 'Updated notes only'}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        # Customer name should remain unchanged
        self.assertEqual(data['invoice']['customer_name'], original_customer)
        self.assertEqual(data['invoice']['notes'], 'Updated notes only')
    
    def test_update_invoice_due_date(self):
        """Test PUT /<id> updates due_date correctly."""
        invoice = self._create_test_invoice(self.user1.id)
        new_due_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
        
        update_data = {'due_date': new_due_date}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['invoice']['due_date'], new_due_date)

    # ==================== DELETE /api/invoices/<id> Tests ====================
    
    def test_delete_invoice_success(self):
        """Test DELETE /<id> deletes invoice successfully."""
        invoice = self._create_test_invoice(self.user1.id)
        invoice_id = invoice.id
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        
        # Verify invoice is deleted
        deleted_invoice = Invoice.query.get(invoice_id)
        self.assertIsNone(deleted_invoice)
    
    def test_delete_invoice_not_found(self):
        """Test DELETE /<id> returns 404 for non-existent invoice."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_delete_invoice_other_user(self):
        """Test DELETE /<id> returns 404 for invoice belonging to another user."""
        invoice = self._create_test_invoice(self.user2.id)
        
        response = self.client.delete(
            f'/api/invoices/{invoice.id}',
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 404)
        
        # Verify invoice still exists
        existing_invoice = Invoice.query.get(invoice.id)
        self.assertIsNotNone(existing_invoice)
    
    def test_delete_invoice_unauthenticated(self):
        """Test DELETE /<id> returns 401 without JWT token."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.delete(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_cascades_items(self):
        """Test DELETE /<id> also deletes associated invoice items."""
        invoice = self._create_test_invoice(self.user1.id)
        invoice_id = invoice.id
        
        # Verify items exist before deletion
        items_before = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items_before), 2)
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers1
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify items are also deleted
        items_after = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items_after), 0)

    # ==================== User Isolation Tests ====================
    
    def test_invoice_user_isolation_comprehensive(self):
        """Test comprehensive user isolation across all operations."""
        # Create invoices for both users
        invoice1 = self._create_test_invoice(self.user1.id, 'User1 Invoice')
        invoice2 = self._create_test_invoice(self.user2.id, 'User2 Invoice')
        
        # User1 cannot see User2's invoice in list
        response = self.client.get('/api/invoices/', headers=self.auth_headers1)
        data = response.get_json()
        invoice_ids = [inv['id'] for inv in data['invoices']]
        self.assertIn(invoice1.id, invoice_ids)
        self.assertNotIn(invoice2.id, invoice_ids)
        
        # User1 cannot get User2's invoice by ID
        response = self.client.get(f'/api/invoices/{invoice2.id}', headers=self.auth_headers1)
        self.assertEqual(response.status_code, 404)
        
        # User1 cannot update User2's invoice
        response = self.client.put(
            f'/api/invoices/{invoice2.id}',
            json={'customer_name': 'Hacked'},
            headers=self.auth_headers1
        )
        self.assertEqual(response.status_code, 404)
        
        # Verify User2's invoice is unchanged
        unchanged_invoice = Invoice.query.get(invoice2.id)
        self.assertEqual(unchanged_invoice.customer_name, 'User2 Invoice')
        
        # User1 cannot delete User2's invoice
        response = self.client.delete(
            f'/api/invoices/{invoice2.id}',
            headers=self.auth_headers1
        )
        self.assertEqual(response.status_code, 404)
        
        # Verify User2's invoice still exists
        still_exists = Invoice.query.get(invoice2.id)
        self.assertIsNotNone(still_exists)


def run_invoice_tests():
    """Run all invoice tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoiceRoutes)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run the tests
    success = run_invoice_tests()
    if success:
        print("\nAll invoice tests passed!")
        sys.exit(0)
    else:
        print("\nSome invoice tests failed!")
        sys.exit(1)

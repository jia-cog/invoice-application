#!/usr/bin/env python3
"""
Invoice API Routes Tests

Tests for all invoice API endpoints including CRUD operations,
authentication, authorization, and business logic validation.
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
from datetime import datetime, timedelta


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for invoice API routes."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        
        # Initialize extensions
        db.init_app(self.app)
        self.jwt = JWTManager(self.app)
        
        # Register blueprint
        self.app.register_blueprint(invoices_bp, url_prefix='/api/invoices')
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create tables
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
        
        # Create JWT tokens for test users
        self.token1 = create_access_token(identity=str(self.user1.id))
        self.token2 = create_access_token(identity=str(self.user2.id))
        
        # Create test client
        self.client = self.app.test_client()
        
        # Sample invoice data
        self.valid_invoice_data = {
            'customer_name': 'Test Customer',
            'customer_email': 'customer@example.com',
            'customer_address': '123 Test Street',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 10.0,
            'notes': 'Test invoice notes',
            'status': 'draft',
            'items': [
                {
                    'description': 'Test Item 1',
                    'quantity': 2,
                    'unit_price': 100.00
                },
                {
                    'description': 'Test Item 2',
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
    
    def _get_auth_headers(self, token):
        """Helper method to get authorization headers."""
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    def _create_test_invoice(self, user_id, customer_name='Test Customer'):
        """Helper method to create a test invoice in the database."""
        invoice = Invoice(
            invoice_number=f'INV-{datetime.now().strftime("%Y%m%d")}-TEST{user_id}',
            user_id=user_id,
            customer_name=customer_name,
            customer_email='customer@example.com',
            customer_address='123 Test St',
            due_date=(datetime.now() + timedelta(days=30)).date(),
            tax_rate=10.0,
            status='draft'
        )
        db.session.add(invoice)
        db.session.flush()
        
        # Add items
        item = InvoiceItem(
            invoice_id=invoice.id,
            description='Test Item',
            quantity=2,
            unit_price=100.00
        )
        item.calculate_total()
        db.session.add(item)
        
        invoice.calculate_totals()
        db.session.commit()
        
        return invoice

    # ==================== GET /api/invoices/ Tests ====================
    
    def test_get_invoices_authenticated(self):
        """Test GET / with valid JWT returns user's invoices."""
        # Create an invoice for user1
        self._create_test_invoice(self.user1.id)
        
        response = self.client.get(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 1)
    
    def test_get_invoices_empty_list(self):
        """Test GET / returns empty list when no invoices exist."""
        response = self.client.get(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_user_isolation(self):
        """Test GET / only returns invoices for the authenticated user."""
        # Create invoices for both users
        self._create_test_invoice(self.user1.id, 'User1 Customer')
        self._create_test_invoice(self.user2.id, 'User2 Customer')
        
        # User1 should only see their invoice
        response = self.client.get(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'User1 Customer')
    
    def test_get_invoices_without_auth(self):
        """Test GET / without JWT returns 401."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        # Flask-JWT-Extended uses 'msg' key by default for missing auth
        self.assertTrue('error' in data or 'msg' in data)
    
    def test_get_invoices_invalid_token(self):
        """Test GET / with invalid JWT returns error status."""
        response = self.client.get(
            '/api/invoices/',
            headers={'Authorization': 'Bearer invalid-token'}
        )
        
        # Flask-JWT-Extended returns 422 for malformed tokens
        self.assertIn(response.status_code, [401, 422])

    # ==================== GET /api/invoices/<id> Tests ====================
    
    def test_get_invoice_by_id_success(self):
        """Test GET /<id> with valid invoice returns invoice details."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice.id)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_get_invoice_not_found(self):
        """Test GET /<id> with non-existent invoice returns 404."""
        response = self.client.get(
            '/api/invoices/99999',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_other_user_returns_404(self):
        """Test GET /<id> for another user's invoice returns 404."""
        # Create invoice for user1
        invoice = self._create_test_invoice(self.user1.id)
        
        # Try to access with user2's token
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers=self._get_auth_headers(self.token2)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_without_auth(self):
        """Test GET /<id> without JWT returns 401."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.get(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)

    # ==================== POST /api/invoices/ Tests ====================
    
    def test_create_invoice_valid_data(self):
        """Test POST / with valid data creates invoice successfully."""
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(self.valid_invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Invoice created successfully')
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_create_invoice_generates_invoice_number(self):
        """Test POST / generates unique invoice number."""
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(self.valid_invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice_number = data['invoice']['invoice_number']
        self.assertTrue(invoice_number.startswith('INV-'))
        self.assertIn(datetime.now().strftime('%Y%m%d'), invoice_number)
    
    def test_create_invoice_calculates_totals(self):
        """Test POST / correctly calculates invoice totals."""
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(self.valid_invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice = data['invoice']
        
        # Expected: (2 * 100) + (1 * 50) = 250 subtotal
        # Tax: 250 * 0.10 = 25
        # Total: 250 + 25 = 275
        self.assertEqual(invoice['subtotal'], 250.0)
        self.assertEqual(invoice['tax_amount'], 25.0)
        self.assertEqual(invoice['total_amount'], 275.0)
    
    def test_create_invoice_missing_customer_name(self):
        """Test POST / without customer_name returns 400."""
        invalid_data = self.valid_invoice_data.copy()
        del invalid_data['customer_name']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(invalid_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'])
    
    def test_create_invoice_missing_due_date(self):
        """Test POST / without due_date returns 400."""
        invalid_data = self.valid_invoice_data.copy()
        del invalid_data['due_date']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(invalid_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'])
    
    def test_create_invoice_missing_items(self):
        """Test POST / without items returns 400."""
        invalid_data = self.valid_invoice_data.copy()
        del invalid_data['items']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(invalid_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('items', data['error'])
    
    def test_create_invoice_invalid_item_missing_description(self):
        """Test POST / with item missing description returns 400."""
        invalid_data = self.valid_invoice_data.copy()
        invalid_data['items'] = [{'quantity': 1, 'unit_price': 100}]
        
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(invalid_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_quantity(self):
        """Test POST / with item missing quantity returns 400."""
        invalid_data = self.valid_invoice_data.copy()
        invalid_data['items'] = [{'description': 'Test', 'unit_price': 100}]
        
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(invalid_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_unit_price(self):
        """Test POST / with item missing unit_price returns 400."""
        invalid_data = self.valid_invoice_data.copy()
        invalid_data['items'] = [{'description': 'Test', 'quantity': 1}]
        
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(invalid_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_without_auth(self):
        """Test POST / without JWT returns 401."""
        response = self.client.post(
            '/api/invoices/',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(self.valid_invoice_data)
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_invoice_with_optional_fields(self):
        """Test POST / with only required fields succeeds."""
        minimal_data = {
            'customer_name': 'Minimal Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [
                {
                    'description': 'Test Item',
                    'quantity': 1,
                    'unit_price': 100.00
                }
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(minimal_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['customer_name'], 'Minimal Customer')
        self.assertEqual(data['invoice']['status'], 'draft')  # Default status

    # ==================== PUT /api/invoices/<id> Tests ====================
    
    def test_update_invoice_success(self):
        """Test PUT /<id> with valid data updates invoice successfully."""
        invoice = self._create_test_invoice(self.user1.id)
        
        update_data = {
            'customer_name': 'Updated Customer',
            'status': 'sent'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invoice updated successfully')
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'sent')
    
    def test_update_invoice_with_items(self):
        """Test PUT /<id> with new items updates and recalculates totals."""
        invoice = self._create_test_invoice(self.user1.id)
        
        update_data = {
            'items': [
                {
                    'description': 'New Item 1',
                    'quantity': 3,
                    'unit_price': 200.00
                }
            ],
            'tax_rate': 5.0
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        invoice_data = data['invoice']
        
        # Expected: 3 * 200 = 600 subtotal
        # Tax: 600 * 0.05 = 30
        # Total: 600 + 30 = 630
        self.assertEqual(invoice_data['subtotal'], 600.0)
        self.assertEqual(invoice_data['tax_amount'], 30.0)
        self.assertEqual(invoice_data['total_amount'], 630.0)
        self.assertEqual(len(invoice_data['items']), 1)
    
    def test_update_invoice_not_found(self):
        """Test PUT /<id> with non-existent invoice returns 404."""
        update_data = {'customer_name': 'Updated Customer'}
        
        response = self.client.put(
            '/api/invoices/99999',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_other_user_returns_404(self):
        """Test PUT /<id> for another user's invoice returns 404."""
        invoice = self._create_test_invoice(self.user1.id)
        
        update_data = {'customer_name': 'Hacked Customer'}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers=self._get_auth_headers(self.token2),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_without_auth(self):
        """Test PUT /<id> without JWT returns 401."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'customer_name': 'Updated'})
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_update_invoice_all_fields(self):
        """Test PUT /<id> can update all editable fields."""
        invoice = self._create_test_invoice(self.user1.id)
        
        new_due_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
        update_data = {
            'customer_name': 'New Customer Name',
            'customer_email': 'new@example.com',
            'customer_address': '456 New Street',
            'due_date': new_due_date,
            'tax_rate': 15.0,
            'notes': 'Updated notes',
            'status': 'paid'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        invoice_data = data['invoice']
        
        self.assertEqual(invoice_data['customer_name'], 'New Customer Name')
        self.assertEqual(invoice_data['customer_email'], 'new@example.com')
        self.assertEqual(invoice_data['customer_address'], '456 New Street')
        self.assertEqual(invoice_data['due_date'], new_due_date)
        self.assertEqual(invoice_data['tax_rate'], 15.0)
        self.assertEqual(invoice_data['notes'], 'Updated notes')
        self.assertEqual(invoice_data['status'], 'paid')

    # ==================== DELETE /api/invoices/<id> Tests ====================
    
    def test_delete_invoice_success(self):
        """Test DELETE /<id> with valid invoice deletes successfully."""
        invoice = self._create_test_invoice(self.user1.id)
        invoice_id = invoice.id
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invoice deleted successfully')
        
        # Verify invoice is actually deleted
        deleted_invoice = Invoice.query.get(invoice_id)
        self.assertIsNone(deleted_invoice)
    
    def test_delete_invoice_not_found(self):
        """Test DELETE /<id> with non-existent invoice returns 404."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_delete_invoice_other_user_returns_404(self):
        """Test DELETE /<id> for another user's invoice returns 404."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.delete(
            f'/api/invoices/{invoice.id}',
            headers=self._get_auth_headers(self.token2)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
        
        # Verify invoice still exists
        existing_invoice = Invoice.query.get(invoice.id)
        self.assertIsNotNone(existing_invoice)
    
    def test_delete_invoice_without_auth(self):
        """Test DELETE /<id> without JWT returns 401."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.delete(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_cascades_items(self):
        """Test DELETE /<id> also deletes associated invoice items."""
        invoice = self._create_test_invoice(self.user1.id)
        invoice_id = invoice.id
        
        # Verify items exist before deletion
        items_before = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertGreater(len(items_before), 0)
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify items are also deleted
        items_after = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items_after), 0)

    # ==================== User Isolation Tests ====================
    
    def test_invoice_user_isolation(self):
        """Test that users can only access their own invoices across all operations."""
        # Create invoices for both users
        invoice1 = self._create_test_invoice(self.user1.id, 'User1 Customer')
        invoice2 = self._create_test_invoice(self.user2.id, 'User2 Customer')
        
        # User1 tries to GET user2's invoice
        response = self.client.get(
            f'/api/invoices/{invoice2.id}',
            headers=self._get_auth_headers(self.token1)
        )
        self.assertEqual(response.status_code, 404)
        
        # User1 tries to UPDATE user2's invoice
        response = self.client.put(
            f'/api/invoices/{invoice2.id}',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps({'customer_name': 'Hacked'})
        )
        self.assertEqual(response.status_code, 404)
        
        # User1 tries to DELETE user2's invoice
        response = self.client.delete(
            f'/api/invoices/{invoice2.id}',
            headers=self._get_auth_headers(self.token1)
        )
        self.assertEqual(response.status_code, 404)
        
        # Verify user2's invoice is unchanged
        unchanged_invoice = Invoice.query.get(invoice2.id)
        self.assertIsNotNone(unchanged_invoice)
        self.assertEqual(unchanged_invoice.customer_name, 'User2 Customer')

    # ==================== Business Logic Tests ====================
    
    def test_invoice_item_total_calculation(self):
        """Test that invoice item totals are calculated correctly."""
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(self.valid_invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        items = data['invoice']['items']
        
        # Item 1: 2 * 100 = 200
        self.assertEqual(items[0]['total'], 200.0)
        # Item 2: 1 * 50 = 50
        self.assertEqual(items[1]['total'], 50.0)
    
    def test_invoice_zero_tax_rate(self):
        """Test invoice with zero tax rate calculates correctly."""
        invoice_data = self.valid_invoice_data.copy()
        invoice_data['tax_rate'] = 0.0
        
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice = data['invoice']
        
        self.assertEqual(invoice['subtotal'], 250.0)
        self.assertEqual(invoice['tax_amount'], 0.0)
        self.assertEqual(invoice['total_amount'], 250.0)
    
    def test_invoice_multiple_items_calculation(self):
        """Test invoice with multiple items calculates totals correctly."""
        invoice_data = {
            'customer_name': 'Multi Item Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 20.0,
            'items': [
                {'description': 'Item A', 'quantity': 5, 'unit_price': 10.00},
                {'description': 'Item B', 'quantity': 3, 'unit_price': 25.00},
                {'description': 'Item C', 'quantity': 1, 'unit_price': 100.00}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice = data['invoice']
        
        # Subtotal: (5*10) + (3*25) + (1*100) = 50 + 75 + 100 = 225
        # Tax: 225 * 0.20 = 45
        # Total: 225 + 45 = 270
        self.assertEqual(invoice['subtotal'], 225.0)
        self.assertEqual(invoice['tax_amount'], 45.0)
        self.assertEqual(invoice['total_amount'], 270.0)


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

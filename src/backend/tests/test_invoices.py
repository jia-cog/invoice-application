#!/usr/bin/env python3
"""
Invoice API Routes Tests

Tests for all invoice API endpoints including CRUD operations,
authentication, user isolation, and business logic validation.
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
from config import Config


class TestConfig(Config):
    """Test configuration with in-memory SQLite database."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
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
        
        # Register blueprint
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
        
        # Create JWT tokens for test users
        self.token_user1 = create_access_token(identity=str(self.user1.id))
        self.token_user2 = create_access_token(identity=str(self.user2.id))
        
        # Create test client
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def get_auth_headers(self, token):
        """Helper method to create authorization headers."""
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    def create_test_invoice(self, user_id, customer_name='Test Customer', status='draft'):
        """Helper method to create a test invoice."""
        import uuid
        invoice = Invoice(
            invoice_number=f'INV-{datetime.now().strftime("%Y%m%d")}-{str(uuid.uuid4())[:8].upper()}',
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
        
        # Add test item
        item = InvoiceItem(
            invoice_id=invoice.id,
            description='Test Item',
            quantity=2.0,
            unit_price=50.0
        )
        item.calculate_total()
        db.session.add(item)
        
        invoice.calculate_totals()
        db.session.commit()
        
        return invoice

    # ==================== GET /api/invoices/ Tests ====================
    
    def test_get_invoices_authenticated(self):
        """Test GET / returns invoices for authenticated user."""
        # Create invoices for user1
        self.create_test_invoice(self.user1.id, 'Customer A')
        self.create_test_invoice(self.user1.id, 'Customer B')
        
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_invoices_empty_list(self):
        """Test GET / returns empty list when no invoices exist."""
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_user_isolation(self):
        """Test GET / only returns invoices belonging to authenticated user."""
        # Create invoice for user1
        self.create_test_invoice(self.user1.id, 'User1 Customer')
        # Create invoice for user2
        self.create_test_invoice(self.user2.id, 'User2 Customer')
        
        # User1 should only see their own invoice
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'User1 Customer')
    
    def test_get_invoices_without_auth(self):
        """Test GET / rejects requests without JWT token."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertTrue('error' in data or 'msg' in data)

    # ==================== GET /api/invoices/<id> Tests ====================
    
    def test_get_invoice_by_id_success(self):
        """Test GET /<id> returns invoice for valid ID."""
        invoice = self.create_test_invoice(self.user1.id)
        
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice.id)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_get_invoice_by_id_not_found(self):
        """Test GET /<id> returns 404 for non-existent invoice."""
        response = self.client.get(
            '/api/invoices/99999',
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_by_id_other_user(self):
        """Test GET /<id> returns 404 for invoice belonging to another user."""
        # Create invoice for user2
        invoice = self.create_test_invoice(self.user2.id)
        
        # User1 tries to access user2's invoice
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_by_id_without_auth(self):
        """Test GET /<id> rejects requests without JWT token."""
        invoice = self.create_test_invoice(self.user1.id)
        
        response = self.client.get(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)

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
                {'description': 'Service A', 'quantity': 1, 'unit_price': 100.0},
                {'description': 'Service B', 'quantity': 2, 'unit_price': 50.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertIn('message', data)
        self.assertEqual(data['invoice']['customer_name'], 'New Customer')
        self.assertTrue(data['invoice']['invoice_number'].startswith('INV-'))
    
    def test_create_invoice_missing_customer_name(self):
        """Test POST / returns 400 when customer_name is missing."""
        invoice_data = {
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.token_user1)
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
            headers=self.get_auth_headers(self.token_user1)
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
            headers=self.get_auth_headers(self.token_user1)
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
            headers=self.get_auth_headers(self.token_user1)
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
            headers=self.get_auth_headers(self.token_user1)
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
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_calculates_totals(self):
        """Test POST / correctly calculates invoice totals."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 10.0,
            'items': [
                {'description': 'Item A', 'quantity': 2, 'unit_price': 100.0},  # 200
                {'description': 'Item B', 'quantity': 3, 'unit_price': 50.0}    # 150
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        invoice = data['invoice']
        
        # Subtotal: 200 + 150 = 350
        self.assertEqual(invoice['subtotal'], 350.0)
        # Tax: 350 * 0.10 = 35
        self.assertEqual(invoice['tax_amount'], 35.0)
        # Total: 350 + 35 = 385
        self.assertEqual(invoice['total_amount'], 385.0)
    
    def test_create_invoice_generates_unique_number(self):
        """Test POST / generates unique invoice numbers."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        # Create two invoices
        response1 = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        response2 = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        
        invoice1 = response1.get_json()['invoice']
        invoice2 = response2.get_json()['invoice']
        
        self.assertNotEqual(invoice1['invoice_number'], invoice2['invoice_number'])
    
    def test_create_invoice_without_auth(self):
        """Test POST / rejects requests without JWT token."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post('/api/invoices/', json=invoice_data)
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_invoice_with_default_status(self):
        """Test POST / creates invoice with default 'draft' status."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['invoice']['status'], 'draft')
    
    def test_create_invoice_with_custom_status(self):
        """Test POST / creates invoice with specified status."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'status': 'sent',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['invoice']['status'], 'sent')

    # ==================== PUT /api/invoices/<id> Tests ====================
    
    def test_update_invoice_success(self):
        """Test PUT /<id> updates invoice fields."""
        invoice = self.create_test_invoice(self.user1.id)
        
        update_data = {
            'customer_name': 'Updated Customer',
            'status': 'sent'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'sent')
    
    def test_update_invoice_not_found(self):
        """Test PUT /<id> returns 404 for non-existent invoice."""
        update_data = {'customer_name': 'Updated'}
        
        response = self.client.put(
            '/api/invoices/99999',
            json=update_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_other_user(self):
        """Test PUT /<id> returns 404 for invoice belonging to another user."""
        invoice = self.create_test_invoice(self.user2.id)
        
        update_data = {'customer_name': 'Hacked'}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_items_recalculates_totals(self):
        """Test PUT /<id> recalculates totals when items are updated."""
        invoice = self.create_test_invoice(self.user1.id)
        
        update_data = {
            'items': [
                {'description': 'New Item', 'quantity': 5, 'unit_price': 100.0}  # 500
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        invoice = data['invoice']
        
        # Subtotal: 500
        self.assertEqual(invoice['subtotal'], 500.0)
        # Tax: 500 * 0.10 = 50 (original tax_rate was 10%)
        self.assertEqual(invoice['tax_amount'], 50.0)
        # Total: 500 + 50 = 550
        self.assertEqual(invoice['total_amount'], 550.0)
    
    def test_update_invoice_partial_fields(self):
        """Test PUT /<id> only updates provided fields."""
        invoice = self.create_test_invoice(self.user1.id)
        original_email = invoice.customer_email
        
        update_data = {'customer_name': 'Partial Update'}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['invoice']['customer_name'], 'Partial Update')
        self.assertEqual(data['invoice']['customer_email'], original_email)
    
    def test_update_invoice_without_auth(self):
        """Test PUT /<id> rejects requests without JWT token."""
        invoice = self.create_test_invoice(self.user1.id)
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json={'customer_name': 'Updated'}
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_update_invoice_due_date(self):
        """Test PUT /<id> updates due_date correctly."""
        invoice = self.create_test_invoice(self.user1.id)
        new_due_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
        
        update_data = {'due_date': new_due_date}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['invoice']['due_date'], new_due_date)
    
    def test_update_invoice_tax_rate(self):
        """Test PUT /<id> updates tax_rate and recalculates totals."""
        invoice = self.create_test_invoice(self.user1.id)
        
        update_data = {'tax_rate': 20.0}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['invoice']['tax_rate'], 20.0)
        # Original subtotal was 100 (2 * 50), new tax = 100 * 0.20 = 20
        self.assertEqual(data['invoice']['tax_amount'], 20.0)

    # ==================== DELETE /api/invoices/<id> Tests ====================
    
    def test_delete_invoice_success(self):
        """Test DELETE /<id> deletes invoice successfully."""
        invoice = self.create_test_invoice(self.user1.id)
        invoice_id = invoice.id
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.token_user1)
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
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_delete_invoice_other_user(self):
        """Test DELETE /<id> returns 404 for invoice belonging to another user."""
        invoice = self.create_test_invoice(self.user2.id)
        
        response = self.client.delete(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error'], 'Invoice not found')
        
        # Verify invoice still exists
        existing_invoice = Invoice.query.get(invoice.id)
        self.assertIsNotNone(existing_invoice)
    
    def test_delete_invoice_without_auth(self):
        """Test DELETE /<id> rejects requests without JWT token."""
        invoice = self.create_test_invoice(self.user1.id)
        
        response = self.client.delete(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_cascades_items(self):
        """Test DELETE /<id> also deletes associated invoice items."""
        invoice = self.create_test_invoice(self.user1.id)
        invoice_id = invoice.id
        
        # Verify items exist before deletion
        items_before = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertTrue(len(items_before) > 0)
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.token_user1)
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify items are deleted
        items_after = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items_after), 0)

    # ==================== User Isolation Tests ====================
    
    def test_invoice_user_isolation(self):
        """Test that users cannot access, modify, or delete other users' invoices."""
        # Create invoice for user2
        invoice = self.create_test_invoice(self.user2.id, 'User2 Private Customer')
        
        # User1 tries to GET
        get_response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token_user1)
        )
        self.assertEqual(get_response.status_code, 404)
        
        # User1 tries to PUT
        put_response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json={'customer_name': 'Hacked'},
            headers=self.get_auth_headers(self.token_user1)
        )
        self.assertEqual(put_response.status_code, 404)
        
        # User1 tries to DELETE
        delete_response = self.client.delete(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token_user1)
        )
        self.assertEqual(delete_response.status_code, 404)
        
        # Verify invoice is unchanged
        unchanged_invoice = Invoice.query.get(invoice.id)
        self.assertIsNotNone(unchanged_invoice)
        self.assertEqual(unchanged_invoice.customer_name, 'User2 Private Customer')

    # ==================== Invalid Token Tests ====================
    
    def test_get_invoices_invalid_token(self):
        """Test GET / rejects requests with invalid JWT token."""
        response = self.client.get(
            '/api/invoices/',
            headers={'Authorization': 'Bearer invalid.token.here'}
        )
        
        # Flask-JWT-Extended returns 422 for malformed tokens, 401 for missing/expired
        self.assertIn(response.status_code, [401, 422])
    
    def test_create_invoice_invalid_token(self):
        """Test POST / rejects requests with invalid JWT token."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers={'Authorization': 'Bearer invalid.token.here'}
        )
        
        # Flask-JWT-Extended returns 422 for malformed tokens, 401 for missing/expired
        self.assertIn(response.status_code, [401, 422])


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

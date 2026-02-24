#!/usr/bin/env python3
"""
Invoice API Routes Tests

Tests for all invoice API endpoints including CRUD operations,
authentication, user isolation, and business logic validation.
"""

import sys
import os
import unittest
import json

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from config import Config
from models import db, User, Invoice, InvoiceItem
from routes.invoices import invoices_bp


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
        
        # Create JWT tokens for both users
        self.token1 = create_access_token(identity=str(self.user1.id))
        self.token2 = create_access_token(identity=str(self.user2.id))
        
        # Create test client
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def get_auth_headers(self, token):
        """Helper method to get authorization headers."""
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    def create_test_invoice(self, user_id, customer_name='Test Customer'):
        """Helper method to create a test invoice."""
        import uuid
        invoice = Invoice(
            invoice_number=f'INV-TEST-{user_id}-{str(uuid.uuid4())[:8].upper()}',
            user_id=user_id,
            customer_name=customer_name,
            customer_email='customer@example.com',
            customer_address='123 Test St',
            due_date=db.func.date('now'),
            tax_rate=10.0,
            status='draft'
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
        """Test GET / with valid JWT returns user's invoices."""
        # Create invoices for user1
        self.create_test_invoice(self.user1.id, 'Customer A')
        self.create_test_invoice(self.user1.id, 'Customer B')
        
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_invoices_empty_list(self):
        """Test GET / returns empty list when no invoices exist."""
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_user_isolation(self):
        """Test GET / only returns invoices for authenticated user."""
        # Create invoices for both users
        self.create_test_invoice(self.user1.id, 'User1 Customer')
        self.create_test_invoice(self.user2.id, 'User2 Customer')
        
        # User1 should only see their invoice
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'User1 Customer')
    
    def test_get_invoices_unauthenticated(self):
        """Test GET / without JWT returns 401."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_invoices_invalid_token(self):
        """Test GET / with invalid JWT returns error status."""
        response = self.client.get(
            '/api/invoices/',
            headers={'Authorization': 'Bearer invalid.token.here'}
        )
        
        # Flask-JWT-Extended returns 422 for malformed tokens
        self.assertIn(response.status_code, [401, 422])

    # ==================== GET /api/invoices/<id> Tests ====================
    
    def test_get_invoice_by_id_success(self):
        """Test GET /<id> with valid invoice returns invoice details."""
        invoice = self.create_test_invoice(self.user1.id)
        
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice.id)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_get_invoice_by_id_not_found(self):
        """Test GET /<id> with non-existent invoice returns 404."""
        response = self.client.get(
            '/api/invoices/99999',
            headers=self.get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_by_id_wrong_user(self):
        """Test GET /<id> for another user's invoice returns 404."""
        # Create invoice for user1
        invoice = self.create_test_invoice(self.user1.id)
        
        # Try to access with user2's token
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token2)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_by_id_unauthenticated(self):
        """Test GET /<id> without JWT returns 401."""
        invoice = self.create_test_invoice(self.user1.id)
        
        response = self.client.get(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)

    # ==================== POST /api/invoices/ Tests ====================
    
    def test_create_invoice_valid_data(self):
        """Test POST / with valid data creates invoice successfully."""
        invoice_data = {
            'customer_name': 'New Customer',
            'customer_email': 'new@example.com',
            'customer_address': '456 New St',
            'due_date': '2025-12-31',
            'tax_rate': 8.5,
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 100.0},
                {'description': 'Item 2', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Invoice created successfully')
        self.assertEqual(data['invoice']['customer_name'], 'New Customer')
        self.assertTrue(data['invoice']['invoice_number'].startswith('INV-'))
    
    def test_create_invoice_missing_customer_name(self):
        """Test POST / without customer_name returns 400."""
        invoice_data = {
            'due_date': '2025-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'])
    
    def test_create_invoice_missing_due_date(self):
        """Test POST / without due_date returns 400."""
        invoice_data = {
            'customer_name': 'Customer',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'])
    
    def test_create_invoice_missing_items(self):
        """Test POST / without items returns 400."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31'
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('items', data['error'])
    
    def test_create_invoice_invalid_item_missing_description(self):
        """Test POST / with item missing description returns 400."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'items': [{'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_quantity(self):
        """Test POST / with item missing quantity returns 400."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'items': [{'description': 'Item', 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_unit_price(self):
        """Test POST / with item missing unit_price returns 400."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'items': [{'description': 'Item', 'quantity': 1}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_calculates_totals(self):
        """Test POST / correctly calculates subtotal, tax, and total."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'tax_rate': 10.0,
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 100.0},  # 200
                {'description': 'Item 2', 'quantity': 3, 'unit_price': 50.0}    # 150
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice = data['invoice']
        
        # Subtotal should be 350 (200 + 150)
        self.assertEqual(invoice['subtotal'], 350.0)
        # Tax should be 35 (350 * 10%)
        self.assertEqual(invoice['tax_amount'], 35.0)
        # Total should be 385 (350 + 35)
        self.assertEqual(invoice['total_amount'], 385.0)
    
    def test_create_invoice_generates_unique_number(self):
        """Test POST / generates unique invoice numbers."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        # Create two invoices
        response1 = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        response2 = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)
        
        # Invoice numbers should be different
        self.assertNotEqual(
            data1['invoice']['invoice_number'],
            data2['invoice']['invoice_number']
        )
    
    def test_create_invoice_unauthenticated(self):
        """Test POST / without JWT returns 401."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_invoice_default_status(self):
        """Test POST / sets default status to 'draft'."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['status'], 'draft')
    
    def test_create_invoice_custom_status(self):
        """Test POST / allows setting custom status."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'status': 'sent',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['status'], 'sent')

    # ==================== PUT /api/invoices/<id> Tests ====================
    
    def test_update_invoice_success(self):
        """Test PUT /<id> with valid data updates invoice successfully."""
        invoice = self.create_test_invoice(self.user1.id)
        
        update_data = {
            'customer_name': 'Updated Customer',
            'status': 'sent'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'sent')
    
    def test_update_invoice_not_found(self):
        """Test PUT /<id> with non-existent invoice returns 404."""
        update_data = {'customer_name': 'Updated'}
        
        response = self.client.put(
            '/api/invoices/99999',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_wrong_user(self):
        """Test PUT /<id> for another user's invoice returns 404."""
        invoice = self.create_test_invoice(self.user1.id)
        
        update_data = {'customer_name': 'Hacked'}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token2),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_items(self):
        """Test PUT /<id> updates items and recalculates totals."""
        invoice = self.create_test_invoice(self.user1.id)
        
        update_data = {
            'tax_rate': 5.0,
            'items': [
                {'description': 'New Item 1', 'quantity': 4, 'unit_price': 25.0},  # 100
                {'description': 'New Item 2', 'quantity': 2, 'unit_price': 75.0}   # 150
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        invoice_data = data['invoice']
        
        # Verify items were updated
        self.assertEqual(len(invoice_data['items']), 2)
        
        # Verify totals recalculated
        self.assertEqual(invoice_data['subtotal'], 250.0)  # 100 + 150
        self.assertEqual(invoice_data['tax_amount'], 12.5)  # 250 * 5%
        self.assertEqual(invoice_data['total_amount'], 262.5)  # 250 + 12.5
    
    def test_update_invoice_partial_fields(self):
        """Test PUT /<id> only updates provided fields."""
        invoice = self.create_test_invoice(self.user1.id)
        original_email = invoice.customer_email
        
        update_data = {'customer_name': 'Only Name Updated'}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Name should be updated
        self.assertEqual(data['invoice']['customer_name'], 'Only Name Updated')
        # Email should remain unchanged
        self.assertEqual(data['invoice']['customer_email'], original_email)
    
    def test_update_invoice_unauthenticated(self):
        """Test PUT /<id> without JWT returns 401."""
        invoice = self.create_test_invoice(self.user1.id)
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'customer_name': 'Updated'})
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_update_invoice_due_date(self):
        """Test PUT /<id> updates due_date correctly."""
        invoice = self.create_test_invoice(self.user1.id)
        
        update_data = {'due_date': '2026-06-15'}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['due_date'], '2026-06-15')

    # ==================== DELETE /api/invoices/<id> Tests ====================
    
    def test_delete_invoice_success(self):
        """Test DELETE /<id> with valid invoice deletes successfully."""
        invoice = self.create_test_invoice(self.user1.id)
        invoice_id = invoice.id
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invoice deleted successfully')
        
        # Verify invoice is actually deleted
        deleted_invoice = db.session.get(Invoice, invoice_id)
        self.assertIsNone(deleted_invoice)
    
    def test_delete_invoice_not_found(self):
        """Test DELETE /<id> with non-existent invoice returns 404."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers=self.get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_delete_invoice_wrong_user(self):
        """Test DELETE /<id> for another user's invoice returns 404."""
        invoice = self.create_test_invoice(self.user1.id)
        
        response = self.client.delete(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.token2)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
        
        # Verify invoice still exists
        existing_invoice = db.session.get(Invoice, invoice.id)
        self.assertIsNotNone(existing_invoice)
    
    def test_delete_invoice_unauthenticated(self):
        """Test DELETE /<id> without JWT returns 401."""
        invoice = self.create_test_invoice(self.user1.id)
        
        response = self.client.delete(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_cascades_items(self):
        """Test DELETE /<id> also deletes associated invoice items."""
        invoice = self.create_test_invoice(self.user1.id)
        invoice_id = invoice.id
        
        # Verify items exist before deletion
        items_before = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertGreater(len(items_before), 0)
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify items are also deleted
        items_after = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items_after), 0)

    # ==================== User Isolation Tests ====================
    
    def test_invoice_user_isolation_comprehensive(self):
        """Test that users cannot access, modify, or delete other users' invoices."""
        # Create invoices for both users
        invoice1 = self.create_test_invoice(self.user1.id, 'User1 Invoice')
        invoice2 = self.create_test_invoice(self.user2.id, 'User2 Invoice')
        
        # User1 trying to GET user2's invoice
        response = self.client.get(
            f'/api/invoices/{invoice2.id}',
            headers=self.get_auth_headers(self.token1)
        )
        self.assertEqual(response.status_code, 404)
        
        # User1 trying to UPDATE user2's invoice
        response = self.client.put(
            f'/api/invoices/{invoice2.id}',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps({'customer_name': 'Hacked'})
        )
        self.assertEqual(response.status_code, 404)
        
        # User1 trying to DELETE user2's invoice
        response = self.client.delete(
            f'/api/invoices/{invoice2.id}',
            headers=self.get_auth_headers(self.token1)
        )
        self.assertEqual(response.status_code, 404)
        
        # Verify user2's invoice is unchanged
        db.session.refresh(invoice2)
        self.assertEqual(invoice2.customer_name, 'User2 Invoice')

    # ==================== Business Logic Tests ====================
    
    def test_invoice_number_format(self):
        """Test that invoice numbers follow the expected format."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        data = json.loads(response.data)
        invoice_number = data['invoice']['invoice_number']
        
        # Should start with INV-
        self.assertTrue(invoice_number.startswith('INV-'))
        # Should have date component (YYYYMMDD format)
        parts = invoice_number.split('-')
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[1]), 8)  # YYYYMMDD
    
    def test_item_total_calculation(self):
        """Test that item totals are calculated correctly."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'items': [
                {'description': 'Item 1', 'quantity': 3, 'unit_price': 33.33},
                {'description': 'Item 2', 'quantity': 2.5, 'unit_price': 40.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        data = json.loads(response.data)
        items = data['invoice']['items']
        
        # Item 1: 3 * 33.33 = 99.99
        item1 = next(i for i in items if i['description'] == 'Item 1')
        self.assertAlmostEqual(item1['total'], 99.99, places=2)
        
        # Item 2: 2.5 * 40.0 = 100.0
        item2 = next(i for i in items if i['description'] == 'Item 2')
        self.assertEqual(item2['total'], 100.0)
    
    def test_zero_tax_rate(self):
        """Test invoice with zero tax rate."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2025-12-31',
            'tax_rate': 0.0,
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.token1),
            data=json.dumps(invoice_data)
        )
        
        data = json.loads(response.data)
        invoice = data['invoice']
        
        self.assertEqual(invoice['subtotal'], 100.0)
        self.assertEqual(invoice['tax_amount'], 0.0)
        self.assertEqual(invoice['total_amount'], 100.0)


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
        print("\nAll invoice tests passed!")
        sys.exit(0)
    else:
        print("\nSome invoice tests failed!")
        sys.exit(1)

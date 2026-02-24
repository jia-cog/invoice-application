#!/usr/bin/env python3
"""
Invoice API Routes Tests

Tests for all invoice CRUD operations including authentication,
authorization, validation, and business logic.
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
from app import create_app


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for invoice API routes."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create app with test configuration
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        # Reinitialize database with test config
        with self.app.app_context():
            db.drop_all()
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
            
            # Store user IDs for token creation
            self.user1_id = self.user1.id
            self.user2_id = self.user2.id
            
            # Create JWT tokens
            self.user1_token = create_access_token(identity=str(self.user1_id))
            self.user2_token = create_access_token(identity=str(self.user2_id))
        
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Clean up after each test method."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def get_auth_headers(self, token):
        """Helper method to create authorization headers."""
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    def create_test_invoice_data(self, customer_name='Test Customer'):
        """Helper method to create valid invoice data."""
        return {
            'customer_name': customer_name,
            'customer_email': 'customer@example.com',
            'customer_address': '123 Test Street',
            'due_date': '2026-02-15',
            'tax_rate': 10.0,
            'notes': 'Test invoice notes',
            'status': 'draft',
            'items': [
                {
                    'description': 'Test Item 1',
                    'quantity': 2,
                    'unit_price': 50.00
                },
                {
                    'description': 'Test Item 2',
                    'quantity': 1,
                    'unit_price': 100.00
                }
            ]
        }
    
    # ==================== GET /api/invoices/ Tests ====================
    
    def test_get_invoices_authenticated(self):
        """Test GET / with valid JWT returns invoices for authenticated user."""
        # First create an invoice
        invoice_data = self.create_test_invoice_data()
        self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        # Get invoices
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'Test Customer')
    
    def test_get_invoices_empty_list(self):
        """Test GET / returns empty list when no invoices exist."""
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_user_isolation(self):
        """Test GET / only returns invoices belonging to authenticated user."""
        # Create invoice for user1
        invoice_data = self.create_test_invoice_data('User1 Customer')
        self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        # Create invoice for user2
        invoice_data2 = self.create_test_invoice_data('User2 Customer')
        self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user2_token),
            data=json.dumps(invoice_data2)
        )
        
        # User1 should only see their invoice
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'User1 Customer')
    
    def test_get_invoices_without_token(self):
        """Test GET / without JWT token returns 401."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_get_invoices_with_invalid_token(self):
        """Test GET / with invalid JWT token returns 401."""
        response = self.client.get(
            '/api/invoices/',
            headers={'Authorization': 'Bearer invalid.token.here'}
        )
        
        self.assertEqual(response.status_code, 401)
    
    # ==================== GET /api/invoices/<id> Tests ====================
    
    def test_get_invoice_by_id_success(self):
        """Test GET /<id> with valid invoice returns invoice details."""
        # Create an invoice
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']
        
        # Get the invoice by ID
        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice_id)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_get_invoice_by_id_not_found(self):
        """Test GET /<id> with non-existent invoice returns 404."""
        response = self.client.get(
            '/api/invoices/99999',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_by_id_other_user(self):
        """Test GET /<id> for invoice belonging to another user returns 404."""
        # Create invoice for user1
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']
        
        # Try to get it as user2
        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user2_token)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_by_id_without_token(self):
        """Test GET /<id> without JWT token returns 401."""
        response = self.client.get('/api/invoices/1')
        
        self.assertEqual(response.status_code, 401)
    
    # ==================== POST /api/invoices/ Tests ====================
    
    def test_create_invoice_valid_data(self):
        """Test POST / with valid data creates invoice successfully."""
        invoice_data = self.create_test_invoice_data()
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Invoice created successfully')
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
        self.assertEqual(data['invoice']['status'], 'draft')
    
    def test_create_invoice_generates_invoice_number(self):
        """Test POST / generates unique invoice number."""
        invoice_data = self.create_test_invoice_data()
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice_number = data['invoice']['invoice_number']
        
        # Verify invoice number format: INV-YYYYMMDD-XXXXXXXX
        self.assertTrue(invoice_number.startswith('INV-'))
        self.assertEqual(len(invoice_number), 21)  # INV- + 8 digits + - + 8 chars
    
    def test_create_invoice_calculates_totals(self):
        """Test POST / correctly calculates subtotal, tax, and total."""
        invoice_data = self.create_test_invoice_data()
        # Items: 2 x $50 = $100, 1 x $100 = $100
        # Subtotal: $200, Tax (10%): $20, Total: $220
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice = data['invoice']
        
        self.assertEqual(invoice['subtotal'], 200.0)
        self.assertEqual(invoice['tax_rate'], 10.0)
        self.assertEqual(invoice['tax_amount'], 20.0)
        self.assertEqual(invoice['total_amount'], 220.0)
    
    def test_create_invoice_with_items(self):
        """Test POST / creates invoice items correctly."""
        invoice_data = self.create_test_invoice_data()
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        items = data['invoice']['items']
        
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['description'], 'Test Item 1')
        self.assertEqual(items[0]['quantity'], 2)
        self.assertEqual(items[0]['unit_price'], 50.0)
        self.assertEqual(items[0]['total'], 100.0)
    
    def test_create_invoice_missing_customer_name(self):
        """Test POST / with missing customer_name returns 400."""
        invoice_data = self.create_test_invoice_data()
        del invoice_data['customer_name']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'])
    
    def test_create_invoice_missing_due_date(self):
        """Test POST / with missing due_date returns 400."""
        invoice_data = self.create_test_invoice_data()
        del invoice_data['due_date']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'])
    
    def test_create_invoice_missing_items(self):
        """Test POST / with missing items returns 400."""
        invoice_data = self.create_test_invoice_data()
        del invoice_data['items']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('items', data['error'])
    
    def test_create_invoice_empty_items(self):
        """Test POST / with empty items list returns 400."""
        invoice_data = self.create_test_invoice_data()
        invoice_data['items'] = []
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_description(self):
        """Test POST / with item missing description returns 400."""
        invoice_data = self.create_test_invoice_data()
        invoice_data['items'] = [{'quantity': 1, 'unit_price': 50.0}]
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_quantity(self):
        """Test POST / with item missing quantity returns 400."""
        invoice_data = self.create_test_invoice_data()
        invoice_data['items'] = [{'description': 'Test', 'unit_price': 50.0}]
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_unit_price(self):
        """Test POST / with item missing unit_price returns 400."""
        invoice_data = self.create_test_invoice_data()
        invoice_data['items'] = [{'description': 'Test', 'quantity': 1}]
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_without_token(self):
        """Test POST / without JWT token returns 401."""
        invoice_data = self.create_test_invoice_data()
        
        response = self.client.post(
            '/api/invoices/',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_invoice_default_status(self):
        """Test POST / without status defaults to 'draft'."""
        invoice_data = self.create_test_invoice_data()
        del invoice_data['status']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['status'], 'draft')
    
    def test_create_invoice_default_tax_rate(self):
        """Test POST / without tax_rate defaults to 0."""
        invoice_data = self.create_test_invoice_data()
        del invoice_data['tax_rate']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['tax_rate'], 0.0)
        self.assertEqual(data['invoice']['tax_amount'], 0.0)
    
    # ==================== PUT /api/invoices/<id> Tests ====================
    
    def test_update_invoice_success(self):
        """Test PUT /<id> with valid data updates invoice successfully."""
        # Create an invoice first
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update the invoice
        update_data = {'customer_name': 'Updated Customer', 'status': 'sent'}
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invoice updated successfully')
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'sent')
    
    def test_update_invoice_customer_email(self):
        """Test PUT /<id> updates customer email."""
        # Create an invoice
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update customer email
        update_data = {'customer_email': 'newemail@example.com'}
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['customer_email'], 'newemail@example.com')
    
    def test_update_invoice_due_date(self):
        """Test PUT /<id> updates due date."""
        # Create an invoice
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update due date
        update_data = {'due_date': '2026-03-01'}
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['due_date'], '2026-03-01')
    
    def test_update_invoice_items_recalculates_totals(self):
        """Test PUT /<id> with new items recalculates totals."""
        # Create an invoice
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update with new items
        update_data = {
            'items': [
                {'description': 'New Item', 'quantity': 5, 'unit_price': 100.0}
            ]
        }
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # 5 x $100 = $500, Tax (10%): $50, Total: $550
        self.assertEqual(data['invoice']['subtotal'], 500.0)
        self.assertEqual(data['invoice']['tax_amount'], 50.0)
        self.assertEqual(data['invoice']['total_amount'], 550.0)
        self.assertEqual(len(data['invoice']['items']), 1)
    
    def test_update_invoice_not_found(self):
        """Test PUT /<id> with non-existent invoice returns 404."""
        update_data = {'customer_name': 'Updated Customer'}
        response = self.client.put(
            '/api/invoices/99999',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_other_user(self):
        """Test PUT /<id> for invoice belonging to another user returns 404."""
        # Create invoice for user1
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Try to update as user2
        update_data = {'customer_name': 'Hacked Customer'}
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user2_token),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_without_token(self):
        """Test PUT /<id> without JWT token returns 401."""
        update_data = {'customer_name': 'Updated Customer'}
        response = self.client.put(
            '/api/invoices/1',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_update_invoice_tax_rate(self):
        """Test PUT /<id> updates tax rate and recalculates totals."""
        # Create an invoice
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update tax rate to 20%
        update_data = {'tax_rate': 20.0}
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Subtotal: $200, Tax (20%): $40, Total: $240
        self.assertEqual(data['invoice']['tax_rate'], 20.0)
        self.assertEqual(data['invoice']['tax_amount'], 40.0)
        self.assertEqual(data['invoice']['total_amount'], 240.0)
    
    def test_update_invoice_notes(self):
        """Test PUT /<id> updates notes field."""
        # Create an invoice
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update notes
        update_data = {'notes': 'Updated notes for this invoice'}
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['notes'], 'Updated notes for this invoice')
    
    # ==================== DELETE /api/invoices/<id> Tests ====================
    
    def test_delete_invoice_success(self):
        """Test DELETE /<id> with valid invoice deletes successfully."""
        # Create an invoice
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Delete the invoice
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invoice deleted successfully')
        
        # Verify it's actually deleted
        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        self.assertEqual(get_response.status_code, 404)
    
    def test_delete_invoice_not_found(self):
        """Test DELETE /<id> with non-existent invoice returns 404."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_delete_invoice_other_user(self):
        """Test DELETE /<id> for invoice belonging to another user returns 404."""
        # Create invoice for user1
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Try to delete as user2
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user2_token)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
        
        # Verify invoice still exists for user1
        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        self.assertEqual(get_response.status_code, 200)
    
    def test_delete_invoice_without_token(self):
        """Test DELETE /<id> without JWT token returns 401."""
        response = self.client.delete('/api/invoices/1')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_cascades_items(self):
        """Test DELETE /<id> also deletes associated invoice items."""
        # Create an invoice with items
        invoice_data = self.create_test_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Verify items exist
        with self.app.app_context():
            items_before = InvoiceItem.query.filter_by(invoice_id=invoice_id).count()
            self.assertEqual(items_before, 2)
        
        # Delete the invoice
        self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        # Verify items are also deleted
        with self.app.app_context():
            items_after = InvoiceItem.query.filter_by(invoice_id=invoice_id).count()
            self.assertEqual(items_after, 0)
    
    # ==================== User Isolation Tests ====================
    
    def test_invoice_user_isolation_comprehensive(self):
        """Verify users cannot access, modify, or delete other users' invoices."""
        # Create invoice for user1
        invoice_data = self.create_test_invoice_data('User1 Private Invoice')
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token),
            data=json.dumps(invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # User2 cannot GET the invoice
        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user2_token)
        )
        self.assertEqual(get_response.status_code, 404)
        
        # User2 cannot UPDATE the invoice
        update_response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user2_token),
            data=json.dumps({'customer_name': 'Hacked'})
        )
        self.assertEqual(update_response.status_code, 404)
        
        # User2 cannot DELETE the invoice
        delete_response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user2_token)
        )
        self.assertEqual(delete_response.status_code, 404)
        
        # Verify invoice is unchanged for user1
        verify_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        self.assertEqual(verify_response.status_code, 200)
        data = json.loads(verify_response.data)
        self.assertEqual(data['invoice']['customer_name'], 'User1 Private Invoice')
    
    # ==================== Multiple Invoices Tests ====================
    
    def test_create_multiple_invoices_unique_numbers(self):
        """Test creating multiple invoices generates unique invoice numbers."""
        invoice_numbers = set()
        
        for i in range(5):
            invoice_data = self.create_test_invoice_data(f'Customer {i}')
            response = self.client.post(
                '/api/invoices/',
                headers=self.get_auth_headers(self.user1_token),
                data=json.dumps(invoice_data)
            )
            self.assertEqual(response.status_code, 201)
            invoice_number = json.loads(response.data)['invoice']['invoice_number']
            invoice_numbers.add(invoice_number)
        
        # All invoice numbers should be unique
        self.assertEqual(len(invoice_numbers), 5)
    
    def test_get_invoices_ordered_by_created_at_desc(self):
        """Test GET / returns invoices ordered by created_at descending."""
        # Create multiple invoices
        for i in range(3):
            invoice_data = self.create_test_invoice_data(f'Customer {i}')
            self.client.post(
                '/api/invoices/',
                headers=self.get_auth_headers(self.user1_token),
                data=json.dumps(invoice_data)
            )
        
        # Get all invoices
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        invoices = data['invoices']
        
        # Verify order (most recent first)
        self.assertEqual(len(invoices), 3)
        self.assertEqual(invoices[0]['customer_name'], 'Customer 2')
        self.assertEqual(invoices[1]['customer_name'], 'Customer 1')
        self.assertEqual(invoices[2]['customer_name'], 'Customer 0')


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

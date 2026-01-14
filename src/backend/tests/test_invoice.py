#!/usr/bin/env python3
"""
Invoice CRUD Operations Tests

Tests for invoice Create, Read, Update, and Delete functionality.
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


class TestInvoiceCRUD(unittest.TestCase):
    """Test cases for Invoice CRUD operations."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        db.init_app(self.app)
        self.jwt = JWTManager(self.app)
        
        # Register the invoices blueprint
        from routes.invoices import invoices_bp
        self.app.register_blueprint(invoices_bp, url_prefix='/api/invoices')
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create all tables
        db.create_all()
        
        # Create a test user
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            company_name='Test Company'
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        db.session.commit()
        
        # Create access token for the test user
        self.access_token = create_access_token(identity=str(self.test_user.id))
        
        # Create test client
        self.client = self.app.test_client()
        
        # Common headers for authenticated requests
        self.auth_headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Sample invoice data for tests
        self.sample_invoice_data = {
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'customer_address': '123 Main St, City, Country',
            'due_date': '2026-02-15',
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
    
    # ==================== CREATE Tests ====================
    
    def test_create_invoice_success(self):
        """Test successful invoice creation with valid data."""
        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Invoice created successfully')
        
        # Verify invoice data
        invoice = data['invoice']
        self.assertEqual(invoice['customer_name'], 'John Doe')
        self.assertEqual(invoice['customer_email'], 'john@example.com')
        self.assertEqual(invoice['status'], 'draft')
        self.assertIn('INV-', invoice['invoice_number'])
    
    def test_create_invoice_calculates_totals_correctly(self):
        """Test that invoice totals are calculated correctly."""
        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        
        self.assertEqual(response.status_code, 201)
        invoice = json.loads(response.data)['invoice']
        
        # Expected: (2 * 100) + (1 * 50) = 250 subtotal
        # Tax: 250 * 0.10 = 25
        # Total: 250 + 25 = 275
        self.assertEqual(invoice['subtotal'], 250.0)
        self.assertEqual(invoice['tax_amount'], 25.0)
        self.assertEqual(invoice['total_amount'], 275.0)
    
    def test_create_invoice_missing_customer_name(self):
        """Test invoice creation fails without customer_name."""
        invalid_data = self.sample_invoice_data.copy()
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
        invalid_data = self.sample_invoice_data.copy()
        del invalid_data['due_date']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invalid_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_missing_items(self):
        """Test invoice creation fails without items."""
        invalid_data = self.sample_invoice_data.copy()
        del invalid_data['items']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invalid_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_item_missing_description(self):
        """Test invoice creation fails when item lacks description."""
        invalid_data = self.sample_invoice_data.copy()
        invalid_data['items'] = [{'quantity': 1, 'unit_price': 100}]
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(invalid_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_without_authentication(self):
        """Test invoice creation fails without authentication token."""
        response = self.client.post(
            '/api/invoices/',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(self.sample_invoice_data)
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_invoice_with_default_status(self):
        """Test invoice creation uses default status when not provided."""
        data = self.sample_invoice_data.copy()
        del data['status']
        
        response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(data)
        )
        
        self.assertEqual(response.status_code, 201)
        invoice = json.loads(response.data)['invoice']
        self.assertEqual(invoice['status'], 'draft')
    
    # ==================== READ Tests ====================
    
    def test_get_all_invoices_empty(self):
        """Test getting all invoices when none exist."""
        response = self.client.get(
            '/api/invoices/',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_all_invoices_with_data(self):
        """Test getting all invoices when invoices exist."""
        # Create two invoices
        self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        
        second_invoice = self.sample_invoice_data.copy()
        second_invoice['customer_name'] = 'Jane Doe'
        self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(second_invoice)
        )
        
        response = self.client.get(
            '/api/invoices/',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_single_invoice_success(self):
        """Test getting a single invoice by ID."""
        # Create an invoice first
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Get the invoice
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
        """Test getting a non-existent invoice returns 404."""
        response = self.client.get(
            '/api/invoices/99999',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_without_authentication(self):
        """Test getting invoices fails without authentication."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_invoice_returns_items(self):
        """Test that getting an invoice includes its items."""
        # Create an invoice
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Get the invoice
        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        
        invoice = json.loads(response.data)['invoice']
        self.assertIn('items', invoice)
        self.assertEqual(len(invoice['items']), 2)
        self.assertEqual(invoice['items'][0]['description'], 'Service A')
    
    # ==================== UPDATE Tests ====================
    
    def test_update_invoice_customer_name(self):
        """Test updating invoice customer name."""
        # Create an invoice
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update the invoice
        update_data = {'customer_name': 'Updated Customer'}
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        invoice = json.loads(response.data)['invoice']
        self.assertEqual(invoice['customer_name'], 'Updated Customer')
    
    def test_update_invoice_status(self):
        """Test updating invoice status."""
        # Create an invoice
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update status to 'sent'
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps({'status': 'sent'})
        )
        
        self.assertEqual(response.status_code, 200)
        invoice = json.loads(response.data)['invoice']
        self.assertEqual(invoice['status'], 'sent')
    
    def test_update_invoice_items(self):
        """Test updating invoice items recalculates totals."""
        # Create an invoice
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update with new items
        new_items = {
            'items': [
                {'description': 'New Service', 'quantity': 5, 'unit_price': 200.00}
            ]
        }
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps(new_items)
        )
        
        self.assertEqual(response.status_code, 200)
        invoice = json.loads(response.data)['invoice']
        
        # New subtotal: 5 * 200 = 1000
        # Tax: 1000 * 0.10 = 100
        # Total: 1000 + 100 = 1100
        self.assertEqual(invoice['subtotal'], 1000.0)
        self.assertEqual(invoice['total_amount'], 1100.0)
        self.assertEqual(len(invoice['items']), 1)
    
    def test_update_invoice_not_found(self):
        """Test updating a non-existent invoice returns 404."""
        response = self.client.put(
            '/api/invoices/99999',
            headers=self.auth_headers,
            data=json.dumps({'customer_name': 'Test'})
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_multiple_fields(self):
        """Test updating multiple invoice fields at once."""
        # Create an invoice
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update multiple fields
        update_data = {
            'customer_name': 'New Customer',
            'customer_email': 'new@example.com',
            'status': 'paid',
            'notes': 'Updated notes'
        }
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers,
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        invoice = json.loads(response.data)['invoice']
        self.assertEqual(invoice['customer_name'], 'New Customer')
        self.assertEqual(invoice['customer_email'], 'new@example.com')
        self.assertEqual(invoice['status'], 'paid')
        self.assertEqual(invoice['notes'], 'Updated notes')
    
    def test_update_invoice_without_authentication(self):
        """Test updating invoice fails without authentication."""
        response = self.client.put(
            '/api/invoices/1',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'customer_name': 'Test'})
        )
        
        self.assertEqual(response.status_code, 401)
    
    # ==================== DELETE Tests ====================
    
    def test_delete_invoice_success(self):
        """Test successful invoice deletion."""
        # Create an invoice
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Delete the invoice
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invoice deleted successfully')
        
        # Verify invoice is deleted
        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        self.assertEqual(get_response.status_code, 404)
    
    def test_delete_invoice_not_found(self):
        """Test deleting a non-existent invoice returns 404."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_delete_invoice_without_authentication(self):
        """Test deleting invoice fails without authentication."""
        response = self.client.delete('/api/invoices/1')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_removes_items(self):
        """Test that deleting an invoice also removes its items."""
        # Create an invoice
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Verify items exist
        invoice_items_count = InvoiceItem.query.filter_by(invoice_id=invoice_id).count()
        self.assertEqual(invoice_items_count, 2)
        
        # Delete the invoice
        self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        
        # Verify items are deleted (cascade delete)
        invoice_items_count = InvoiceItem.query.filter_by(invoice_id=invoice_id).count()
        self.assertEqual(invoice_items_count, 0)
    
    # ==================== User Isolation Tests ====================
    
    def test_user_cannot_access_other_users_invoice(self):
        """Test that users cannot access invoices belonging to other users."""
        # Create an invoice for the first user
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Create a second user
        second_user = User(
            username='seconduser',
            email='second@example.com',
            company_name='Second Company'
        )
        second_user.set_password('password')
        db.session.add(second_user)
        db.session.commit()
        
        # Create token for second user
        second_token = create_access_token(identity=str(second_user.id))
        second_headers = {
            'Authorization': f'Bearer {second_token}',
            'Content-Type': 'application/json'
        }
        
        # Try to access first user's invoice
        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=second_headers
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_user_cannot_update_other_users_invoice(self):
        """Test that users cannot update invoices belonging to other users."""
        # Create an invoice for the first user
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Create a second user
        second_user = User(
            username='seconduser2',
            email='second2@example.com',
            company_name='Second Company'
        )
        second_user.set_password('password')
        db.session.add(second_user)
        db.session.commit()
        
        # Create token for second user
        second_token = create_access_token(identity=str(second_user.id))
        second_headers = {
            'Authorization': f'Bearer {second_token}',
            'Content-Type': 'application/json'
        }
        
        # Try to update first user's invoice
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=second_headers,
            data=json.dumps({'customer_name': 'Hacked'})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_user_cannot_delete_other_users_invoice(self):
        """Test that users cannot delete invoices belonging to other users."""
        # Create an invoice for the first user
        create_response = self.client.post(
            '/api/invoices/',
            headers=self.auth_headers,
            data=json.dumps(self.sample_invoice_data)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Create a second user
        second_user = User(
            username='seconduser3',
            email='second3@example.com',
            company_name='Second Company'
        )
        second_user.set_password('password')
        db.session.add(second_user)
        db.session.commit()
        
        # Create token for second user
        second_token = create_access_token(identity=str(second_user.id))
        second_headers = {
            'Authorization': f'Bearer {second_token}',
            'Content-Type': 'application/json'
        }
        
        # Try to delete first user's invoice
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=second_headers
        )
        
        self.assertEqual(response.status_code, 404)
        
        # Verify invoice still exists for original user
        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        self.assertEqual(get_response.status_code, 200)


def run_invoice_tests():
    """Run all invoice tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoiceCRUD)
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

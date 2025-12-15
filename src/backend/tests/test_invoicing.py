#!/usr/bin/env python3
"""
Invoice Routes Tests

Tests for invoice CRUD operations and API endpoints.
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


class TestConfig(Config):
    """Test configuration with in-memory SQLite database."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for invoice CRUD operations and API endpoints."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        from app import create_app
        
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        
        db.init_app(self.app)
        self.jwt = JWTManager(self.app)
        
        # Register the invoices blueprint
        from routes.invoices import invoices_bp
        self.app.register_blueprint(invoices_bp, url_prefix='/api/invoices')
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
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
        self.auth_headers = {'Authorization': f'Bearer {self.access_token}'}
        
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _create_sample_invoice_data(self):
        """Helper method to create sample invoice data."""
        return {
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
    
    # ==================== CREATE INVOICE TESTS ====================
    
    def test_create_invoice_success(self):
        """Test successful invoice creation with valid data."""
        invoice_data = self._create_sample_invoice_data()
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
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
        self.assertIn('INV-', invoice['invoice_number'])
    
    def test_create_invoice_calculates_totals_correctly(self):
        """Test that invoice totals are calculated correctly."""
        invoice_data = self._create_sample_invoice_data()
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 201)
        invoice = json.loads(response.data)['invoice']
        
        # Subtotal: (2 * 100) + (1 * 50) = 250
        self.assertEqual(invoice['subtotal'], 250.0)
        # Tax: 250 * 0.10 = 25
        self.assertEqual(invoice['tax_amount'], 25.0)
        # Total: 250 + 25 = 275
        self.assertEqual(invoice['total_amount'], 275.0)
    
    def test_create_invoice_missing_customer_name(self):
        """Test invoice creation fails without customer_name."""
        invoice_data = self._create_sample_invoice_data()
        del invoice_data['customer_name']
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'])
    
    def test_create_invoice_missing_due_date(self):
        """Test invoice creation fails without due_date."""
        invoice_data = self._create_sample_invoice_data()
        del invoice_data['due_date']
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'])
    
    def test_create_invoice_missing_items(self):
        """Test invoice creation fails without items."""
        invoice_data = self._create_sample_invoice_data()
        del invoice_data['items']
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('items', data['error'])
    
    def test_create_invoice_invalid_item_missing_description(self):
        """Test invoice creation fails when item is missing description."""
        invoice_data = self._create_sample_invoice_data()
        invoice_data['items'] = [{'quantity': 1, 'unit_price': 100}]
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_quantity(self):
        """Test invoice creation fails when item is missing quantity."""
        invoice_data = self._create_sample_invoice_data()
        invoice_data['items'] = [{'description': 'Test', 'unit_price': 100}]
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_missing_unit_price(self):
        """Test invoice creation fails when item is missing unit_price."""
        invoice_data = self._create_sample_invoice_data()
        invoice_data['items'] = [{'description': 'Test', 'quantity': 1}]
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_without_auth(self):
        """Test invoice creation fails without authentication."""
        invoice_data = self._create_sample_invoice_data()
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    # ==================== GET ALL INVOICES TESTS ====================
    
    def test_get_invoices_empty_list(self):
        """Test getting invoices when none exist."""
        response = self.client.get(
            '/api/invoices/',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_returns_user_invoices(self):
        """Test getting all invoices for authenticated user."""
        # Create two invoices
        invoice_data = self._create_sample_invoice_data()
        self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        invoice_data['customer_name'] = 'Jane Doe'
        self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        response = self.client.get(
            '/api/invoices/',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_invoices_without_auth(self):
        """Test getting invoices fails without authentication."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_invoices_user_isolation(self):
        """Test that users can only see their own invoices."""
        # Create invoice for first user
        invoice_data = self._create_sample_invoice_data()
        self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        # Create second user
        second_user = User(
            username='seconduser',
            email='second@example.com',
            company_name='Second Company'
        )
        second_user.set_password('password')
        db.session.add(second_user)
        db.session.commit()
        
        second_token = create_access_token(identity=str(second_user.id))
        second_headers = {'Authorization': f'Bearer {second_token}'}
        
        # Second user should see no invoices
        response = self.client.get(
            '/api/invoices/',
            headers=second_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoices']), 0)
    
    # ==================== GET SINGLE INVOICE TESTS ====================
    
    def test_get_invoice_by_id_success(self):
        """Test getting a single invoice by ID."""
        # Create an invoice
        invoice_data = self._create_sample_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        created_invoice = json.loads(create_response.data)['invoice']
        invoice_id = created_invoice['id']
        
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
    
    def test_get_invoice_not_found(self):
        """Test getting a non-existent invoice returns 404."""
        response = self.client.get(
            '/api/invoices/99999',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_belongs_to_another_user(self):
        """Test that users cannot access other users' invoices."""
        # Create invoice for first user
        invoice_data = self._create_sample_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Create second user
        second_user = User(
            username='seconduser',
            email='second@example.com',
            company_name='Second Company'
        )
        second_user.set_password('password')
        db.session.add(second_user)
        db.session.commit()
        
        second_token = create_access_token(identity=str(second_user.id))
        second_headers = {'Authorization': f'Bearer {second_token}'}
        
        # Second user tries to access first user's invoice
        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=second_headers
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_get_invoice_without_auth(self):
        """Test getting invoice fails without authentication."""
        response = self.client.get('/api/invoices/1')
        
        self.assertEqual(response.status_code, 401)
    
    # ==================== UPDATE INVOICE TESTS ====================
    
    def test_update_invoice_success(self):
        """Test successful invoice update."""
        # Create an invoice
        invoice_data = self._create_sample_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update the invoice
        update_data = {
            'customer_name': 'Updated Customer',
            'status': 'sent'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'sent')
    
    def test_update_invoice_items(self):
        """Test updating invoice items recalculates totals."""
        # Create an invoice
        invoice_data = self._create_sample_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Update with new items
        update_data = {
            'items': [
                {
                    'description': 'New Service',
                    'quantity': 5,
                    'unit_price': 200.00
                }
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 200)
        invoice = json.loads(response.data)['invoice']
        
        # New subtotal: 5 * 200 = 1000
        self.assertEqual(invoice['subtotal'], 1000.0)
        # Tax: 1000 * 0.10 = 100
        self.assertEqual(invoice['tax_amount'], 100.0)
        # Total: 1000 + 100 = 1100
        self.assertEqual(invoice['total_amount'], 1100.0)
        self.assertEqual(len(invoice['items']), 1)
    
    def test_update_invoice_not_found(self):
        """Test updating a non-existent invoice returns 404."""
        update_data = {'customer_name': 'Updated'}
        
        response = self.client.put(
            '/api/invoices/99999',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_invoice_belongs_to_another_user(self):
        """Test that users cannot update other users' invoices."""
        # Create invoice for first user
        invoice_data = self._create_sample_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Create second user
        second_user = User(
            username='seconduser',
            email='second@example.com',
            company_name='Second Company'
        )
        second_user.set_password('password')
        db.session.add(second_user)
        db.session.commit()
        
        second_token = create_access_token(identity=str(second_user.id))
        second_headers = {'Authorization': f'Bearer {second_token}'}
        
        # Second user tries to update first user's invoice
        update_data = {'customer_name': 'Hacked'}
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=second_headers
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_invoice_without_auth(self):
        """Test updating invoice fails without authentication."""
        response = self.client.put(
            '/api/invoices/1',
            data=json.dumps({'customer_name': 'Test'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    # ==================== DELETE INVOICE TESTS ====================
    
    def test_delete_invoice_success(self):
        """Test successful invoice deletion."""
        # Create an invoice
        invoice_data = self._create_sample_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
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
    
    def test_delete_invoice_belongs_to_another_user(self):
        """Test that users cannot delete other users' invoices."""
        # Create invoice for first user
        invoice_data = self._create_sample_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Create second user
        second_user = User(
            username='seconduser',
            email='second@example.com',
            company_name='Second Company'
        )
        second_user.set_password('password')
        db.session.add(second_user)
        db.session.commit()
        
        second_token = create_access_token(identity=str(second_user.id))
        second_headers = {'Authorization': f'Bearer {second_token}'}
        
        # Second user tries to delete first user's invoice
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
    
    def test_delete_invoice_without_auth(self):
        """Test deleting invoice fails without authentication."""
        response = self.client.delete('/api/invoices/1')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_cascades_to_items(self):
        """Test that deleting an invoice also deletes its items."""
        # Create an invoice with items
        invoice_data = self._create_sample_invoice_data()
        create_response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.auth_headers
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        # Verify items exist
        invoice = db.session.get(Invoice, invoice_id)
        item_count = len(invoice.items)
        self.assertGreater(item_count, 0)
        
        # Delete the invoice
        self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers
        )
        
        # Verify items are also deleted
        items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items), 0)


def run_invoicing_tests():
    """Run all invoicing tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoiceRoutes)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_invoicing_tests()
    if success:
        print("\nAll invoicing tests passed!")
        sys.exit(0)
    else:
        print("\nSome invoicing tests failed!")
        sys.exit(1)

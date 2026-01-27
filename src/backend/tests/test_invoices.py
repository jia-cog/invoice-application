#!/usr/bin/env python3
"""
Invoice Routes Tests

Tests for invoice API endpoints functionality.
"""

import sys
import os
import unittest

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from config import Config
from models import db, User, Invoice, InvoiceItem


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for invoice API endpoints."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        
        self.jwt = JWTManager(self.app)
        db.init_app(self.app)
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        from routes.invoices import invoices_bp
        self.app.register_blueprint(invoices_bp, url_prefix='/api/invoices')
        
        self.client = self.app.test_client()
        
        self.user1 = User(
            username='testuser1',
            email='test1@example.com',
            company_name='Test Company 1'
        )
        self.user1.set_password('password123')
        db.session.add(self.user1)
        
        self.user2 = User(
            username='testuser2',
            email='test2@example.com',
            company_name='Test Company 2'
        )
        self.user2.set_password('password456')
        db.session.add(self.user2)
        
        db.session.commit()
        
        self.token_user1 = create_access_token(identity=str(self.user1.id))
        self.token_user2 = create_access_token(identity=str(self.user2.id))
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _create_test_invoice(self, user_id, customer_name='Test Customer'):
        """Helper method to create a test invoice with items."""
        from datetime import datetime
        import uuid
        
        invoice = Invoice(
            invoice_number=f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
            user_id=user_id,
            customer_name=customer_name,
            customer_email='customer@example.com',
            customer_address='123 Test St',
            due_date=datetime.strptime('2026-12-31', '%Y-%m-%d').date(),
            tax_rate=10.0,
            status='draft'
        )
        db.session.add(invoice)
        db.session.flush()
        
        item1 = InvoiceItem(
            invoice_id=invoice.id,
            description='Test Item 1',
            quantity=2.0,
            unit_price=50.0
        )
        item1.calculate_total()
        db.session.add(item1)
        
        item2 = InvoiceItem(
            invoice_id=invoice.id,
            description='Test Item 2',
            quantity=1.0,
            unit_price=100.0
        )
        item2.calculate_total()
        db.session.add(item2)
        
        invoice.calculate_totals()
        db.session.commit()
        
        return invoice

    # ==================== GET /api/invoices/ Tests ====================
    
    def test_get_invoices_success(self):
        """Test successful retrieval of invoices with valid JWT."""
        self._create_test_invoice(self.user1.id, 'Customer A')
        self._create_test_invoice(self.user1.id, 'Customer B')
        
        response = self.client.get(
            '/api/invoices/',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_invoices_requires_auth(self):
        """Test that 401 is returned without JWT token."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertTrue('error' in data or 'msg' in data)
    
    def test_get_invoices_empty_list(self):
        """Test that user with no invoices returns empty array."""
        response = self.client.get(
            '/api/invoices/',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_user_isolation(self):
        """Test that user only sees their own invoices."""
        self._create_test_invoice(self.user1.id, 'User1 Customer')
        self._create_test_invoice(self.user2.id, 'User2 Customer')
        
        response = self.client.get(
            '/api/invoices/',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'User1 Customer')

    # ==================== GET /api/invoices/<id> Tests ====================
    
    def test_get_single_invoice_success(self):
        """Test successful retrieval of a single invoice with valid JWT and invoice ID."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice.id)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_get_single_invoice_not_found(self):
        """Test 404 for non-existent invoice ID."""
        response = self.client.get(
            '/api/invoices/99999',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_single_invoice_unauthorized_access(self):
        """Test 404 when accessing another user's invoice."""
        invoice = self._create_test_invoice(self.user2.id)
        
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_get_single_invoice_requires_auth(self):
        """Test 401 without JWT token."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.get(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertTrue('error' in data or 'msg' in data)

    # ==================== POST /api/invoices/ Tests ====================
    
    def test_create_invoice_success(self):
        """Test successful creation of invoice with all required fields."""
        invoice_data = {
            'customer_name': 'New Customer',
            'customer_email': 'new@example.com',
            'customer_address': '456 New St',
            'due_date': '2026-12-31',
            'tax_rate': 8.0,
            'items': [
                {'description': 'Service A', 'quantity': 2, 'unit_price': 100.0},
                {'description': 'Service B', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertIn('message', data)
        self.assertEqual(data['invoice']['customer_name'], 'New Customer')
        self.assertIsNotNone(data['invoice']['invoice_number'])
    
    def test_create_invoice_missing_customer_name(self):
        """Test 400 error for missing customer_name."""
        invoice_data = {
            'due_date': '2026-12-31',
            'items': [
                {'description': 'Service A', 'quantity': 2, 'unit_price': 100.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'])
    
    def test_create_invoice_missing_due_date(self):
        """Test 400 error for missing due_date."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'items': [
                {'description': 'Service A', 'quantity': 2, 'unit_price': 100.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'])
    
    def test_create_invoice_missing_items(self):
        """Test 400 error for missing items array."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': '2026-12-31'
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('items', data['error'])
    
    def test_create_invoice_invalid_items(self):
        """Test 400 error for items missing description/quantity/unit_price."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': '2026-12-31',
            'items': [
                {'description': 'Service A'}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('description, quantity, and unit_price', data['error'])
    
    def test_create_invoice_requires_auth(self):
        """Test 401 without JWT token."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': '2026-12-31',
            'items': [
                {'description': 'Service A', 'quantity': 2, 'unit_price': 100.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertTrue('error' in data or 'msg' in data)
    
    def test_create_invoice_calculates_totals(self):
        """Test that subtotal, tax, and total calculations are correct."""
        invoice_data = {
            'customer_name': 'Calculation Test',
            'due_date': '2026-12-31',
            'tax_rate': 10.0,
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 100.0},
                {'description': 'Item 2', 'quantity': 3, 'unit_price': 50.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        invoice = data['invoice']
        
        expected_subtotal = (2 * 100.0) + (3 * 50.0)
        expected_tax = expected_subtotal * 0.10
        expected_total = expected_subtotal + expected_tax
        
        self.assertEqual(invoice['subtotal'], expected_subtotal)
        self.assertEqual(invoice['tax_amount'], expected_tax)
        self.assertEqual(invoice['total_amount'], expected_total)

    # ==================== PUT /api/invoices/<id> Tests ====================
    
    def test_update_invoice_success(self):
        """Test successful full update of an invoice."""
        invoice = self._create_test_invoice(self.user1.id)
        
        update_data = {
            'customer_name': 'Updated Customer',
            'customer_email': 'updated@example.com',
            'customer_address': '789 Updated St',
            'due_date': '2027-01-15',
            'tax_rate': 15.0,
            'status': 'sent',
            'items': [
                {'description': 'Updated Item', 'quantity': 5, 'unit_price': 200.0}
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'sent')
    
    def test_update_invoice_partial_update(self):
        """Test successful partial field update."""
        invoice = self._create_test_invoice(self.user1.id)
        original_customer_name = invoice.customer_name
        
        update_data = {
            'status': 'paid'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['invoice']['status'], 'paid')
        self.assertEqual(data['invoice']['customer_name'], original_customer_name)
    
    def test_update_invoice_not_found(self):
        """Test 404 for non-existent invoice."""
        update_data = {
            'customer_name': 'Updated Customer'
        }
        
        response = self.client.put(
            '/api/invoices/99999',
            json=update_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_update_invoice_unauthorized_access(self):
        """Test 404 when updating another user's invoice."""
        invoice = self._create_test_invoice(self.user2.id)
        
        update_data = {
            'customer_name': 'Hacked Customer'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_update_invoice_requires_auth(self):
        """Test 401 without JWT token."""
        invoice = self._create_test_invoice(self.user1.id)
        
        update_data = {
            'customer_name': 'Updated Customer'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertTrue('error' in data or 'msg' in data)
    
    def test_update_invoice_recalculates_totals(self):
        """Test that totals are recalculated when items are updated."""
        invoice = self._create_test_invoice(self.user1.id)
        
        update_data = {
            'tax_rate': 20.0,
            'items': [
                {'description': 'New Item 1', 'quantity': 10, 'unit_price': 25.0},
                {'description': 'New Item 2', 'quantity': 5, 'unit_price': 30.0}
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        invoice_data = data['invoice']
        
        expected_subtotal = (10 * 25.0) + (5 * 30.0)
        expected_tax = expected_subtotal * 0.20
        expected_total = expected_subtotal + expected_tax
        
        self.assertEqual(invoice_data['subtotal'], expected_subtotal)
        self.assertEqual(invoice_data['tax_amount'], expected_tax)
        self.assertEqual(invoice_data['total_amount'], expected_total)

    # ==================== DELETE /api/invoices/<id> Tests ====================
    
    def test_delete_invoice_success(self):
        """Test successful deletion of an invoice."""
        invoice = self._create_test_invoice(self.user1.id)
        invoice_id = invoice.id
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Invoice deleted successfully')
        
        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        self.assertEqual(get_response.status_code, 404)
    
    def test_delete_invoice_not_found(self):
        """Test 404 for non-existent invoice."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_delete_invoice_unauthorized_access(self):
        """Test 404 when deleting another user's invoice."""
        invoice = self._create_test_invoice(self.user2.id)
        
        response = self.client.delete(
            f'/api/invoices/{invoice.id}',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_delete_invoice_requires_auth(self):
        """Test 401 without JWT token."""
        invoice = self._create_test_invoice(self.user1.id)
        
        response = self.client.delete(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertTrue('error' in data or 'msg' in data)


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
        print("\n✅ All invoice tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some invoice tests failed!")
        sys.exit(1)

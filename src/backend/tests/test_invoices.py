#!/usr/bin/env python3
"""
Invoice API Tests

Tests for all invoice CRUD operations including authentication and authorization.
"""

import sys
import os
import unittest
from datetime import datetime, timedelta
import json
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_jwt_extended import create_access_token
from app import create_app
from models import db, User, Invoice, InvoiceItem


class TestInvoiceAPI(unittest.TestCase):
    """Test cases for invoice API endpoints."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            self.test_user = User(
                username='testuser',
                email='test@example.com',
                company_name='Test Company'
            )
            self.test_user.set_password('testpass123')
            db.session.add(self.test_user)
            db.session.commit()
            
            self.user_id = self.test_user.id
            self.access_token = create_access_token(identity=str(self.user_id))
            
            self.test_user2 = User(
                username='testuser2',
                email='test2@example.com',
                company_name='Test Company 2'
            )
            self.test_user2.set_password('testpass456')
            db.session.add(self.test_user2)
            db.session.commit()
            
            self.user_id2 = self.test_user2.id
            self.access_token2 = create_access_token(identity=str(self.user_id2))
    
    def tearDown(self):
        """Clean up after each test method."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def get_auth_headers(self, token=None):
        """Get authorization headers with JWT token."""
        if token is None:
            token = self.access_token
        return {'Authorization': f'Bearer {token}'}
    
    def create_test_invoice(self, user_id=None, customer_name='Test Customer'):
        """Create a test invoice in the database."""
        if user_id is None:
            user_id = self.user_id
            
        invoice = Invoice(
            invoice_number=f'INV-TEST-{datetime.now().strftime("%Y%m%d")}-{str(uuid.uuid4())[:8].upper()}',
            user_id=user_id,
            customer_name=customer_name,
            customer_email='customer@example.com',
            customer_address='123 Test St',
            due_date=(datetime.now() + timedelta(days=30)).date(),
            tax_rate=10.0,
            notes='Test notes',
            status='draft'
        )
        db.session.add(invoice)
        db.session.flush()
        
        item = InvoiceItem(
            invoice_id=invoice.id,
            description='Test Item',
            quantity=2.0,
            unit_price=100.0
        )
        item.calculate_total()
        db.session.add(item)
        
        invoice.calculate_totals()
        db.session.commit()
        
        return invoice
    
    def test_get_invoices_success(self):
        """Test successful retrieval of user's invoices."""
        with self.app.app_context():
            invoice1 = self.create_test_invoice(customer_name='Customer 1')
            invoice2 = self.create_test_invoice(customer_name='Customer 2')
        
        response = self.client.get('/api/invoices/', headers=self.get_auth_headers())
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)
        self.assertEqual(data['invoices'][0]['customer_name'], 'Customer 2')
        self.assertEqual(data['invoices'][1]['customer_name'], 'Customer 1')
    
    def test_get_invoices_empty(self):
        """Test retrieval when user has no invoices."""
        response = self.client.get('/api/invoices/', headers=self.get_auth_headers())
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_unauthorized(self):
        """Test that unauthorized access is rejected."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_get_invoices_filters_by_user(self):
        """Test that users only see their own invoices."""
        with self.app.app_context():
            invoice1 = self.create_test_invoice(user_id=self.user_id, customer_name='User 1 Invoice')
            invoice2 = self.create_test_invoice(user_id=self.user_id2, customer_name='User 2 Invoice')
        
        response = self.client.get('/api/invoices/', headers=self.get_auth_headers())
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'User 1 Invoice')
    
    def test_get_invoice_success(self):
        """Test successful retrieval of a single invoice."""
        with self.app.app_context():
            invoice = self.create_test_invoice(customer_name='Test Customer')
            invoice_id = invoice.id
        
        response = self.client.get(f'/api/invoices/{invoice_id}', headers=self.get_auth_headers())
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice_id)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_get_invoice_not_found(self):
        """Test retrieval of non-existent invoice."""
        response = self.client.get('/api/invoices/99999', headers=self.get_auth_headers())
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invoice not found')
    
    def test_get_invoice_wrong_user(self):
        """Test that users cannot access other users' invoices."""
        with self.app.app_context():
            invoice = self.create_test_invoice(user_id=self.user_id2)
            invoice_id = invoice.id
        
        response = self.client.get(f'/api/invoices/{invoice_id}', headers=self.get_auth_headers())
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_get_invoice_unauthorized(self):
        """Test that unauthorized access to single invoice is rejected."""
        with self.app.app_context():
            invoice = self.create_test_invoice()
            invoice_id = invoice.id
        
        response = self.client.get(f'/api/invoices/{invoice_id}')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_success(self):
        """Test successful invoice creation with required fields."""
        invoice_data = {
            'customer_name': 'New Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [
                {
                    'description': 'Test Item 1',
                    'quantity': 2,
                    'unit_price': 50.0
                },
                {
                    'description': 'Test Item 2',
                    'quantity': 1,
                    'unit_price': 100.0
                }
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'New Customer')
        self.assertEqual(len(data['invoice']['items']), 2)
        self.assertIn('message', data)
    
    def test_create_invoice_with_optional_fields(self):
        """Test invoice creation with all optional fields."""
        invoice_data = {
            'customer_name': 'Full Customer',
            'customer_email': 'full@example.com',
            'customer_address': '456 Full St',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 8.5,
            'notes': 'Important notes',
            'status': 'sent',
            'items': [
                {
                    'description': 'Full Item',
                    'quantity': 1,
                    'unit_price': 200.0
                }
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['invoice']['customer_email'], 'full@example.com')
        self.assertEqual(data['invoice']['customer_address'], '456 Full St')
        self.assertEqual(data['invoice']['tax_rate'], 8.5)
        self.assertEqual(data['invoice']['notes'], 'Important notes')
        self.assertEqual(data['invoice']['status'], 'sent')
    
    def test_create_invoice_missing_customer_name(self):
        """Test that missing customer_name returns 400 error."""
        invoice_data = {
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Test', 'quantity': 1, 'unit_price': 100}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_missing_due_date(self):
        """Test that missing due_date returns 400 error."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'items': [{'description': 'Test', 'quantity': 1, 'unit_price': 100}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_missing_items(self):
        """Test that missing items returns 400 error."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_data(self):
        """Test that invalid item data returns 400 error."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [
                {
                    'description': 'Test Item'
                }
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_calculates_totals(self):
        """Test that invoice totals are calculated correctly."""
        invoice_data = {
            'customer_name': 'Math Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 10.0,
            'items': [
                {
                    'description': 'Item 1',
                    'quantity': 2,
                    'unit_price': 50.0
                },
                {
                    'description': 'Item 2',
                    'quantity': 1,
                    'unit_price': 100.0
                }
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['invoice']['subtotal'], 200.0)
        self.assertEqual(data['invoice']['tax_amount'], 20.0)
        self.assertEqual(data['invoice']['total_amount'], 220.0)
    
    def test_create_invoice_generates_invoice_number(self):
        """Test that unique invoice number is generated."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Test', 'quantity': 1, 'unit_price': 100}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('invoice_number', data['invoice'])
        self.assertTrue(data['invoice']['invoice_number'].startswith('INV-'))
    
    def test_create_invoice_unauthorized(self):
        """Test that unauthorized invoice creation is rejected."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Test', 'quantity': 1, 'unit_price': 100}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            data=json.dumps(invoice_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_update_invoice_success(self):
        """Test successful invoice update."""
        with self.app.app_context():
            invoice = self.create_test_invoice(customer_name='Original Name')
            invoice_id = invoice.id
        
        update_data = {
            'customer_name': 'Updated Name'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Name')
    
    def test_update_invoice_multiple_fields(self):
        """Test updating multiple invoice fields."""
        with self.app.app_context():
            invoice = self.create_test_invoice()
            invoice_id = invoice.id
        
        update_data = {
            'customer_name': 'New Name',
            'customer_email': 'newemail@example.com',
            'customer_address': '789 New St',
            'due_date': (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d'),
            'tax_rate': 15.0,
            'notes': 'Updated notes',
            'status': 'paid'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['invoice']['customer_name'], 'New Name')
        self.assertEqual(data['invoice']['customer_email'], 'newemail@example.com')
        self.assertEqual(data['invoice']['tax_rate'], 15.0)
        self.assertEqual(data['invoice']['status'], 'paid')
    
    def test_update_invoice_with_items(self):
        """Test updating invoice with new items."""
        with self.app.app_context():
            invoice = self.create_test_invoice()
            invoice_id = invoice.id
        
        update_data = {
            'items': [
                {
                    'description': 'New Item 1',
                    'quantity': 3,
                    'unit_price': 75.0
                },
                {
                    'description': 'New Item 2',
                    'quantity': 2,
                    'unit_price': 50.0
                }
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['invoice']['items']), 2)
        self.assertEqual(data['invoice']['items'][0]['description'], 'New Item 1')
    
    def test_update_invoice_recalculates_totals(self):
        """Test that updating items recalculates totals."""
        with self.app.app_context():
            invoice = self.create_test_invoice()
            invoice_id = invoice.id
        
        update_data = {
            'tax_rate': 5.0,
            'items': [
                {
                    'description': 'Item',
                    'quantity': 2,
                    'unit_price': 100.0
                }
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['invoice']['subtotal'], 200.0)
        self.assertEqual(data['invoice']['tax_amount'], 10.0)
        self.assertEqual(data['invoice']['total_amount'], 210.0)
    
    def test_update_invoice_not_found(self):
        """Test updating non-existent invoice."""
        update_data = {
            'customer_name': 'Updated Name'
        }
        
        response = self.client.put(
            '/api/invoices/99999',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_update_invoice_wrong_user(self):
        """Test that users cannot update other users' invoices."""
        with self.app.app_context():
            invoice = self.create_test_invoice(user_id=self.user_id2)
            invoice_id = invoice.id
        
        update_data = {
            'customer_name': 'Hacked Name'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_update_invoice_unauthorized(self):
        """Test that unauthorized invoice update is rejected."""
        with self.app.app_context():
            invoice = self.create_test_invoice()
            invoice_id = invoice.id
        
        update_data = {
            'customer_name': 'Updated Name'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_delete_invoice_success(self):
        """Test successful invoice deletion."""
        with self.app.app_context():
            invoice = self.create_test_invoice()
            invoice_id = invoice.id
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        
        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers()
        )
        self.assertEqual(get_response.status_code, 404)
    
    def test_delete_invoice_not_found(self):
        """Test deleting non-existent invoice."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_delete_invoice_wrong_user(self):
        """Test that users cannot delete other users' invoices."""
        with self.app.app_context():
            invoice = self.create_test_invoice(user_id=self.user_id2)
            invoice_id = invoice.id
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_delete_invoice_unauthorized(self):
        """Test that unauthorized invoice deletion is rejected."""
        with self.app.app_context():
            invoice = self.create_test_invoice()
            invoice_id = invoice.id
        
        response = self.client.delete(f'/api/invoices/{invoice_id}')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)


def run_invoice_tests():
    """Run all invoice tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoiceAPI)
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

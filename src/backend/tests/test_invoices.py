#!/usr/bin/env python3
"""
Invoice API Routes Tests

Tests for all invoice CRUD endpoints including authentication, authorization,
validation, and business logic.
"""

import sys
import os
import unittest
from datetime import date, datetime, timedelta
import json
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_jwt_extended import create_access_token
from app import create_app
from models import db, User, Invoice, InvoiceItem


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for invoice API endpoints."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        self.user1 = User(username='testuser1', email='test1@example.com', company_name='Test Company 1')
        self.user1.set_password('password123')
        
        self.user2 = User(username='testuser2', email='test2@example.com', company_name='Test Company 2')
        self.user2.set_password('password123')
        
        db.session.add(self.user1)
        db.session.add(self.user2)
        db.session.commit()
        
        self.token1 = create_access_token(identity=str(self.user1.id))
        self.token2 = create_access_token(identity=str(self.user2.id))
        self.headers1 = {'Authorization': f'Bearer {self.token1}'}
        self.headers2 = {'Authorization': f'Bearer {self.token2}'}
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _create_test_invoice(self, user_id, customer_name='Test Customer', status='draft'):
        """Helper method to create a test invoice with items."""
        invoice_data = {
            'customer_name': customer_name,
            'customer_email': 'customer@example.com',
            'customer_address': '123 Test St',
            'due_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 10.0,
            'notes': 'Test invoice',
            'status': status,
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 50.0},
                {'description': 'Item 2', 'quantity': 1, 'unit_price': 100.0}
            ]
        }
        
        headers = self.headers1 if user_id == self.user1.id else self.headers2
        response = self.client.post('/api/invoices/', 
                                    data=json.dumps(invoice_data),
                                    content_type='application/json',
                                    headers=headers)
        return response
    
    def test_get_invoices_authenticated(self):
        """Test GET /api/invoices/ with valid JWT token."""
        self._create_test_invoice(self.user1.id)
        self._create_test_invoice(self.user1.id, customer_name='Another Customer')
        
        response = self.client.get('/api/invoices/', headers=self.headers1)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_invoices_empty(self):
        """Test GET /api/invoices/ returns empty list when no invoices exist."""
        response = self.client.get('/api/invoices/', headers=self.headers1)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_unauthenticated(self):
        """Test GET /api/invoices/ rejects requests without JWT token."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_invoices_user_isolation(self):
        """Test that users only see their own invoices."""
        self._create_test_invoice(self.user1.id)
        self._create_test_invoice(self.user2.id)
        
        response = self.client.get('/api/invoices/', headers=self.headers1)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoices']), 1)
    
    def test_get_invoice_by_id_success(self):
        """Test GET /api/invoices/<id> successfully retrieves invoice."""
        create_response = self._create_test_invoice(self.user1.id)
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        response = self.client.get(f'/api/invoices/{invoice_id}', headers=self.headers1)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice_id)
    
    def test_get_invoice_by_id_not_found(self):
        """Test GET /api/invoices/<id> returns 404 for non-existent invoice."""
        response = self.client.get('/api/invoices/99999', headers=self.headers1)
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_get_invoice_by_id_other_user(self):
        """Test GET /api/invoices/<id> returns 404 for another user's invoice."""
        create_response = self._create_test_invoice(self.user1.id)
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        response = self.client.get(f'/api/invoices/{invoice_id}', headers=self.headers2)
        
        self.assertEqual(response.status_code, 404)
    
    def test_get_invoice_by_id_unauthenticated(self):
        """Test GET /api/invoices/<id> rejects requests without JWT token."""
        response = self.client.get('/api/invoices/1')
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_invoice_valid_data(self):
        """Test POST /api/invoices/ successfully creates invoice with valid data."""
        invoice_data = {
            'customer_name': 'New Customer',
            'customer_email': 'new@example.com',
            'customer_address': '456 New St',
            'due_date': (date.today() + timedelta(days=15)).strftime('%Y-%m-%d'),
            'tax_rate': 8.0,
            'notes': 'New invoice',
            'status': 'sent',
            'items': [
                {'description': 'Product A', 'quantity': 3, 'unit_price': 25.0},
                {'description': 'Product B', 'quantity': 2, 'unit_price': 40.0}
            ]
        }
        
        response = self.client.post('/api/invoices/',
                                    data=json.dumps(invoice_data),
                                    content_type='application/json',
                                    headers=self.headers1)
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'New Customer')
        self.assertEqual(len(data['invoice']['items']), 2)
    
    def test_create_invoice_missing_customer_name(self):
        """Test POST /api/invoices/ returns 400 for missing customer_name."""
        invoice_data = {
            'due_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 10.0}]
        }
        
        response = self.client.post('/api/invoices/',
                                    data=json.dumps(invoice_data),
                                    content_type='application/json',
                                    headers=self.headers1)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_missing_due_date(self):
        """Test POST /api/invoices/ returns 400 for missing due_date."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 10.0}]
        }
        
        response = self.client.post('/api/invoices/',
                                    data=json.dumps(invoice_data),
                                    content_type='application/json',
                                    headers=self.headers1)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_missing_items(self):
        """Test POST /api/invoices/ returns 400 for missing items."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        
        response = self.client.post('/api/invoices/',
                                    data=json.dumps(invoice_data),
                                    content_type='application/json',
                                    headers=self.headers1)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_items(self):
        """Test POST /api/invoices/ returns 400 for items missing required fields."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1}]
        }
        
        response = self.client.post('/api/invoices/',
                                    data=json.dumps(invoice_data),
                                    content_type='application/json',
                                    headers=self.headers1)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_unauthenticated(self):
        """Test POST /api/invoices/ rejects requests without JWT token."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 10.0}]
        }
        
        response = self.client.post('/api/invoices/',
                                    data=json.dumps(invoice_data),
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_invoice_number_generation(self):
        """Test that invoice numbers follow the INV-YYYYMMDD-XXXXXXXX pattern."""
        response = self._create_test_invoice(self.user1.id)
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice_number = data['invoice']['invoice_number']
        
        pattern = r'^INV-\d{8}-[A-Z0-9]{8}$'
        self.assertIsNotNone(re.match(pattern, invoice_number))
        
        today_str = datetime.now().strftime('%Y%m%d')
        self.assertTrue(invoice_number.startswith(f'INV-{today_str}'))
    
    def test_create_invoice_totals_calculation(self):
        """Test that subtotal, tax, and total are calculated correctly."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 10.0,
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 50.0},
                {'description': 'Item 2', 'quantity': 3, 'unit_price': 30.0}
            ]
        }
        
        response = self.client.post('/api/invoices/',
                                    data=json.dumps(invoice_data),
                                    content_type='application/json',
                                    headers=self.headers1)
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        invoice = data['invoice']
        
        expected_subtotal = (2 * 50.0) + (3 * 30.0)
        expected_tax = expected_subtotal * 0.10
        expected_total = expected_subtotal + expected_tax
        
        self.assertEqual(invoice['subtotal'], expected_subtotal)
        self.assertEqual(invoice['tax_amount'], expected_tax)
        self.assertEqual(invoice['total_amount'], expected_total)
    
    def test_update_invoice_success(self):
        """Test PUT /api/invoices/<id> successfully updates invoice fields."""
        create_response = self._create_test_invoice(self.user1.id)
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        update_data = {
            'customer_name': 'Updated Customer',
            'status': 'paid',
            'notes': 'Updated notes'
        }
        
        response = self.client.put(f'/api/invoices/{invoice_id}',
                                   data=json.dumps(update_data),
                                   content_type='application/json',
                                   headers=self.headers1)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'paid')
        self.assertEqual(data['invoice']['notes'], 'Updated notes')
    
    def test_update_invoice_not_found(self):
        """Test PUT /api/invoices/<id> returns 404 for non-existent invoice."""
        update_data = {'customer_name': 'Updated Customer'}
        
        response = self.client.put('/api/invoices/99999',
                                   data=json.dumps(update_data),
                                   content_type='application/json',
                                   headers=self.headers1)
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_invoice_other_user(self):
        """Test PUT /api/invoices/<id> returns 404 for another user's invoice."""
        create_response = self._create_test_invoice(self.user1.id)
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        update_data = {'customer_name': 'Updated Customer'}
        
        response = self.client.put(f'/api/invoices/{invoice_id}',
                                   data=json.dumps(update_data),
                                   content_type='application/json',
                                   headers=self.headers2)
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_invoice_items(self):
        """Test PUT /api/invoices/<id> successfully updates invoice items."""
        create_response = self._create_test_invoice(self.user1.id)
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        update_data = {
            'items': [
                {'description': 'New Item 1', 'quantity': 5, 'unit_price': 20.0},
                {'description': 'New Item 2', 'quantity': 1, 'unit_price': 150.0}
            ]
        }
        
        response = self.client.put(f'/api/invoices/{invoice_id}',
                                   data=json.dumps(update_data),
                                   content_type='application/json',
                                   headers=self.headers1)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoice']['items']), 2)
        self.assertEqual(data['invoice']['items'][0]['description'], 'New Item 1')
    
    def test_update_invoice_totals_recalculation(self):
        """Test that totals are recalculated after updating items."""
        create_response = self._create_test_invoice(self.user1.id)
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        update_data = {
            'tax_rate': 15.0,
            'items': [
                {'description': 'Item A', 'quantity': 4, 'unit_price': 25.0}
            ]
        }
        
        response = self.client.put(f'/api/invoices/{invoice_id}',
                                   data=json.dumps(update_data),
                                   content_type='application/json',
                                   headers=self.headers1)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        invoice = data['invoice']
        
        expected_subtotal = 4 * 25.0
        expected_tax = expected_subtotal * 0.15
        expected_total = expected_subtotal + expected_tax
        
        self.assertEqual(invoice['subtotal'], expected_subtotal)
        self.assertEqual(invoice['tax_amount'], expected_tax)
        self.assertEqual(invoice['total_amount'], expected_total)
    
    def test_update_invoice_unauthenticated(self):
        """Test PUT /api/invoices/<id> rejects requests without JWT token."""
        update_data = {'customer_name': 'Updated Customer'}
        
        response = self.client.put('/api/invoices/1',
                                   data=json.dumps(update_data),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_success(self):
        """Test DELETE /api/invoices/<id> successfully deletes invoice."""
        create_response = self._create_test_invoice(self.user1.id)
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        response = self.client.delete(f'/api/invoices/{invoice_id}', headers=self.headers1)
        
        self.assertEqual(response.status_code, 200)
        
        get_response = self.client.get(f'/api/invoices/{invoice_id}', headers=self.headers1)
        self.assertEqual(get_response.status_code, 404)
    
    def test_delete_invoice_not_found(self):
        """Test DELETE /api/invoices/<id> returns 404 for non-existent invoice."""
        response = self.client.delete('/api/invoices/99999', headers=self.headers1)
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_invoice_other_user(self):
        """Test DELETE /api/invoices/<id> returns 404 for another user's invoice."""
        create_response = self._create_test_invoice(self.user1.id)
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        response = self.client.delete(f'/api/invoices/{invoice_id}', headers=self.headers2)
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_invoice_unauthenticated(self):
        """Test DELETE /api/invoices/<id> rejects requests without JWT token."""
        response = self.client.delete('/api/invoices/1')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_cascades_to_items(self):
        """Test that deleting an invoice also deletes its items (cascade delete)."""
        create_response = self._create_test_invoice(self.user1.id)
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        invoice = Invoice.query.get(invoice_id)
        item_count = len(invoice.items)
        self.assertGreater(item_count, 0)
        
        response = self.client.delete(f'/api/invoices/{invoice_id}', headers=self.headers1)
        self.assertEqual(response.status_code, 200)
        
        items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items), 0)


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

#!/usr/bin/env python3
"""
Invoice API Tests

Tests for all invoice CRUD operations and authentication.
"""

import sys
import os
import unittest
import json
from datetime import datetime, date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Invoice, InvoiceItem
from flask_jwt_extended import create_access_token
from config import Config


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
        
        with self.app.app_context():
            self.token1 = create_access_token(identity=str(self.user1.id))
            self.token2 = create_access_token(identity=str(self.user2.id))
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _get_auth_headers(self, token):
        """Helper to create authorization headers."""
        return {'Authorization': f'Bearer {token}'}
    
    def _create_test_invoice(self, user_id, customer_name='Test Customer'):
        """Helper to create a test invoice."""
        invoice_data = {
            'customer_name': customer_name,
            'customer_email': 'customer@example.com',
            'customer_address': '123 Test St',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'tax_rate': 10.0,
            'status': 'draft',
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
        return invoice_data
    
    def test_get_invoices_authenticated(self):
        """Test GET /api/invoices/ with valid JWT returns user's invoices."""
        invoice_data = self._create_test_invoice(self.user1.id)
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        self.assertEqual(response.status_code, 201)
        
        response = self.client.get(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'Test Customer')
    
    def test_get_invoices_empty_list(self):
        """Test GET /api/invoices/ returns empty list when no invoices exist."""
        response = self.client.get(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_unauthenticated(self):
        """Test GET /api/invoices/ without JWT returns 401."""
        response = self.client.get('/api/invoices/')
        self.assertEqual(response.status_code, 401)
    
    def test_get_invoices_user_isolation(self):
        """Test users only see their own invoices."""
        invoice_data = self._create_test_invoice(self.user1.id)
        self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        
        response = self.client.get(
            '/api/invoices/',
            headers=self._get_auth_headers(self.token2)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoice_by_id_success(self):
        """Test GET /api/invoices/<id> with valid invoice ID."""
        invoice_data = self._create_test_invoice(self.user1.id)
        create_response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice_id)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_get_invoice_not_found(self):
        """Test GET /api/invoices/<id> with non-existent ID returns 404."""
        response = self.client.get(
            '/api/invoices/99999',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_get_invoice_wrong_user(self):
        """Test GET /api/invoices/<id> for another user's invoice returns 404."""
        invoice_data = self._create_test_invoice(self.user1.id)
        create_response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self._get_auth_headers(self.token2)
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_create_invoice_valid_data(self):
        """Test POST /api/invoices/ with valid data creates invoice."""
        invoice_data = self._create_test_invoice(self.user1.id)
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('invoice', data)
        
        invoice = data['invoice']
        self.assertEqual(invoice['customer_name'], 'Test Customer')
        self.assertEqual(len(invoice['items']), 2)
        
        self.assertEqual(invoice['subtotal'], 200.0)
        self.assertEqual(invoice['tax_amount'], 20.0)
        self.assertEqual(invoice['total_amount'], 220.0)
        
        self.assertTrue(invoice['invoice_number'].startswith('INV-'))
    
    def test_create_invoice_missing_customer_name(self):
        """Test POST /api/invoices/ without customer_name returns 400."""
        invoice_data = self._create_test_invoice(self.user1.id)
        del invoice_data['customer_name']
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'])
    
    def test_create_invoice_missing_due_date(self):
        """Test POST /api/invoices/ without due_date returns 400."""
        invoice_data = self._create_test_invoice(self.user1.id)
        del invoice_data['due_date']
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'])
    
    def test_create_invoice_missing_items(self):
        """Test POST /api/invoices/ without items returns 400."""
        invoice_data = self._create_test_invoice(self.user1.id)
        del invoice_data['items']
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('items', data['error'])
    
    def test_create_invoice_invalid_item_data(self):
        """Test POST /api/invoices/ with invalid item data returns 400."""
        invoice_data = self._create_test_invoice(self.user1.id)
        invoice_data['items'][0] = {
            'description': 'Test Item',
            'unit_price': 50.0
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_unauthenticated(self):
        """Test POST /api/invoices/ without JWT returns 401."""
        invoice_data = self._create_test_invoice(self.user1.id)
        
        response = self.client.post('/api/invoices/', json=invoice_data)
        self.assertEqual(response.status_code, 401)
    
    def test_update_invoice_success(self):
        """Test PUT /api/invoices/<id> updates invoice successfully."""
        invoice_data = self._create_test_invoice(self.user1.id)
        create_response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        update_data = {
            'customer_name': 'Updated Customer',
            'status': 'sent',
            'notes': 'Updated notes'
        }
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json=update_data,
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'sent')
        self.assertEqual(data['invoice']['notes'], 'Updated notes')
    
    def test_update_invoice_items(self):
        """Test PUT /api/invoices/<id> updates items and recalculates totals."""
        invoice_data = self._create_test_invoice(self.user1.id)
        create_response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        update_data = {
            'items': [
                {
                    'description': 'New Item',
                    'quantity': 3,
                    'unit_price': 75.0
                }
            ]
        }
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json=update_data,
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['invoice']['items']), 1)
        self.assertEqual(data['invoice']['subtotal'], 225.0)
        self.assertEqual(data['invoice']['tax_amount'], 22.5)
        self.assertEqual(data['invoice']['total_amount'], 247.5)
    
    def test_update_invoice_not_found(self):
        """Test PUT /api/invoices/<id> with non-existent ID returns 404."""
        update_data = {'customer_name': 'Updated Name'}
        response = self.client.put(
            '/api/invoices/99999',
            json=update_data,
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_invoice_wrong_user(self):
        """Test PUT /api/invoices/<id> for another user's invoice returns 404."""
        invoice_data = self._create_test_invoice(self.user1.id)
        create_response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        update_data = {'customer_name': 'Hacked Name'}
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json=update_data,
            headers=self._get_auth_headers(self.token2)
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_invoice_success(self):
        """Test DELETE /api/invoices/<id> deletes invoice successfully."""
        invoice_data = self._create_test_invoice(self.user1.id)
        create_response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        
        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self._get_auth_headers(self.token1)
        )
        self.assertEqual(get_response.status_code, 404)
    
    def test_delete_invoice_not_found(self):
        """Test DELETE /api/invoices/<id> with non-existent ID returns 404."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_invoice_wrong_user(self):
        """Test DELETE /api/invoices/<id> for another user's invoice returns 404."""
        invoice_data = self._create_test_invoice(self.user1.id)
        create_response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self._get_auth_headers(self.token1)
        )
        invoice_id = json.loads(create_response.data)['invoice']['id']
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self._get_auth_headers(self.token2)
        )
        
        self.assertEqual(response.status_code, 404)


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

#!/usr/bin/env python3
"""
Invoice Routes Tests

Tests for invoice API endpoints including CRUD operations, authentication, and validation.
"""

import sys
import os
import unittest
from datetime import datetime, timedelta
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Invoice, InvoiceItem
from flask_jwt_extended import create_access_token
from config import Config


class TestConfig(Config):
    """Test configuration with in-memory database"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'
    SECRET_KEY = 'test-secret-key'


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for invoice API endpoints"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config.from_object(TestConfig)
        
        self.client = self.app.test_client()
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            company_name='Test Company'
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        db.session.commit()
        
        self.token = create_access_token(identity=str(self.test_user.id))
        self.auth_headers = {
            'Authorization': f'Bearer {self.token}'
        }
        
        self.test_user_2 = User(
            username='testuser2',
            email='test2@example.com',
            company_name='Test Company 2'
        )
        self.test_user_2.set_password('testpassword2')
        db.session.add(self.test_user_2)
        db.session.commit()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _create_test_invoice_data(self):
        """Helper method to create test invoice data"""
        return {
            'customer_name': 'Test Customer',
            'customer_email': 'customer@example.com',
            'customer_address': '123 Test St',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'tax_rate': 10.0,
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
    
    def _create_invoice_in_db(self, user_id=None):
        """Helper method to create an invoice directly in the database"""
        if user_id is None:
            user_id = self.test_user.id
        
        invoice = Invoice(
            invoice_number=f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
            user_id=user_id,
            customer_name='DB Test Customer',
            customer_email='dbtest@example.com',
            customer_address='456 DB Test St',
            due_date=(datetime.now() + timedelta(days=30)).date(),
            tax_rate=10.0,
            status='draft'
        )
        db.session.add(invoice)
        db.session.flush()
        
        item1 = InvoiceItem(
            invoice_id=invoice.id,
            description='DB Test Item 1',
            quantity=3,
            unit_price=25.0
        )
        item1.calculate_total()
        db.session.add(item1)
        
        item2 = InvoiceItem(
            invoice_id=invoice.id,
            description='DB Test Item 2',
            quantity=2,
            unit_price=75.0
        )
        item2.calculate_total()
        db.session.add(item2)
        
        invoice.calculate_totals()
        db.session.commit()
        
        return invoice
    
    def test_get_all_invoices_empty(self):
        """Test GET /api/invoices/ returns empty list when no invoices exist"""
        response = self.client.get('/api/invoices/', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_all_invoices_with_data(self):
        """Test GET /api/invoices/ returns list of user's invoices"""
        invoice1 = self._create_invoice_in_db()
        invoice2 = self._create_invoice_in_db()
        
        response = self.client.get('/api/invoices/', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)
        
        invoice_ids = [inv['id'] for inv in data['invoices']]
        self.assertIn(invoice1.id, invoice_ids)
        self.assertIn(invoice2.id, invoice_ids)
    
    def test_get_all_invoices_unauthorized(self):
        """Test GET /api/invoices/ returns 401 without auth token"""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_get_invoice_by_id_success(self):
        """Test GET /api/invoices/<id> returns correct invoice with 200 status"""
        invoice = self._create_invoice_in_db()
        
        response = self.client.get(f'/api/invoices/{invoice.id}', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice.id)
        self.assertEqual(data['invoice']['customer_name'], 'DB Test Customer')
        self.assertIn('items', data['invoice'])
        self.assertEqual(len(data['invoice']['items']), 2)
    
    def test_get_invoice_not_found(self):
        """Test GET /api/invoices/<id> returns 404 for non-existent ID"""
        response = self.client.get('/api/invoices/99999', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('not found', data['error'].lower())
    
    def test_get_invoice_unauthorized(self):
        """Test GET /api/invoices/<id> returns 401 without auth token"""
        invoice = self._create_invoice_in_db()
        
        response = self.client.get(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_get_invoice_wrong_user(self):
        """Test GET /api/invoices/<id> returns 404 when trying to access another user's invoice"""
        invoice = self._create_invoice_in_db(user_id=self.test_user_2.id)
        
        response = self.client.get(f'/api/invoices/{invoice.id}', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_success(self):
        """Test POST /api/invoices/ creates invoice with valid data, returns 201"""
        invoice_data = self._create_test_invoice_data()
        
        response = self.client.post('/api/invoices/', json=invoice_data, headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
        self.assertIn('invoice_number', data['invoice'])
        self.assertTrue(data['invoice']['invoice_number'].startswith('INV-'))
        
        invoice_id = data['invoice']['id']
        invoice_in_db = Invoice.query.get(invoice_id)
        self.assertIsNotNone(invoice_in_db)
        self.assertEqual(invoice_in_db.customer_name, 'Test Customer')
    
    def test_create_invoice_missing_customer_name(self):
        """Test POST /api/invoices/ returns 400 when customer_name missing"""
        invoice_data = self._create_test_invoice_data()
        del invoice_data['customer_name']
        
        response = self.client.post('/api/invoices/', json=invoice_data, headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'].lower())
    
    def test_create_invoice_missing_due_date(self):
        """Test POST /api/invoices/ returns 400 when due_date missing"""
        invoice_data = self._create_test_invoice_data()
        del invoice_data['due_date']
        
        response = self.client.post('/api/invoices/', json=invoice_data, headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'].lower())
    
    def test_create_invoice_missing_items(self):
        """Test POST /api/invoices/ returns 400 when items missing"""
        invoice_data = self._create_test_invoice_data()
        del invoice_data['items']
        
        response = self.client.post('/api/invoices/', json=invoice_data, headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('items', data['error'].lower())
    
    def test_create_invoice_missing_item_fields(self):
        """Test POST /api/invoices/ returns 400 when item lacks description/quantity/unit_price"""
        invoice_data = self._create_test_invoice_data()
        invoice_data['items'][0] = {'description': 'Incomplete Item'}
        
        response = self.client.post('/api/invoices/', json=invoice_data, headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_calculates_totals(self):
        """Test POST /api/invoices/ verifies subtotal, tax_amount, and total_amount are calculated correctly"""
        invoice_data = self._create_test_invoice_data()
        
        response = self.client.post('/api/invoices/', json=invoice_data, headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        invoice = data['invoice']
        
        expected_subtotal = (2 * 50.0) + (1 * 100.0)
        expected_tax_amount = expected_subtotal * (10.0 / 100)
        expected_total = expected_subtotal + expected_tax_amount
        
        self.assertEqual(invoice['subtotal'], expected_subtotal)
        self.assertEqual(invoice['tax_amount'], expected_tax_amount)
        self.assertEqual(invoice['total_amount'], expected_total)
    
    def test_create_invoice_unauthorized(self):
        """Test POST /api/invoices/ returns 401 without auth token"""
        invoice_data = self._create_test_invoice_data()
        
        response = self.client.post('/api/invoices/', json=invoice_data)
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_update_invoice_success(self):
        """Test PUT /api/invoices/<id> updates invoice fields successfully"""
        invoice = self._create_invoice_in_db()
        
        update_data = {
            'customer_name': 'Updated Customer',
            'customer_email': 'updated@example.com',
            'status': 'sent'
        }
        
        response = self.client.put(f'/api/invoices/{invoice.id}', json=update_data, headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['customer_email'], 'updated@example.com')
        self.assertEqual(data['invoice']['status'], 'sent')
        
        updated_invoice = Invoice.query.get(invoice.id)
        self.assertEqual(updated_invoice.customer_name, 'Updated Customer')
    
    def test_update_invoice_items(self):
        """Test PUT /api/invoices/<id> updates invoice items and recalculates totals"""
        invoice = self._create_invoice_in_db()
        
        update_data = {
            'items': [
                {
                    'description': 'New Item 1',
                    'quantity': 5,
                    'unit_price': 20.0
                }
            ]
        }
        
        response = self.client.put(f'/api/invoices/{invoice.id}', json=update_data, headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        invoice_data = data['invoice']
        
        self.assertEqual(len(invoice_data['items']), 1)
        self.assertEqual(invoice_data['items'][0]['description'], 'New Item 1')
        
        expected_subtotal = 5 * 20.0
        self.assertEqual(invoice_data['subtotal'], expected_subtotal)
    
    def test_update_invoice_not_found(self):
        """Test PUT /api/invoices/<id> returns 404 for non-existent ID"""
        update_data = {'customer_name': 'Updated Customer'}
        
        response = self.client.put('/api/invoices/99999', json=update_data, headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_update_invoice_unauthorized(self):
        """Test PUT /api/invoices/<id> returns 401 without auth token"""
        invoice = self._create_invoice_in_db()
        update_data = {'customer_name': 'Updated Customer'}
        
        response = self.client.put(f'/api/invoices/{invoice.id}', json=update_data)
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_delete_invoice_success(self):
        """Test DELETE /api/invoices/<id> deletes invoice and returns 200"""
        invoice = self._create_invoice_in_db()
        invoice_id = invoice.id
        
        response = self.client.delete(f'/api/invoices/{invoice_id}', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        
        deleted_invoice = Invoice.query.get(invoice_id)
        self.assertIsNone(deleted_invoice)
    
    def test_delete_invoice_not_found(self):
        """Test DELETE /api/invoices/<id> returns 404 for non-existent ID"""
        response = self.client.delete('/api/invoices/99999', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_delete_invoice_unauthorized(self):
        """Test DELETE /api/invoices/<id> returns 401 without auth token"""
        invoice = self._create_invoice_in_db()
        
        response = self.client.delete(f'/api/invoices/{invoice.id}')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_delete_invoice_verifies_deletion(self):
        """Test DELETE /api/invoices/<id> verifies invoice is actually removed from database"""
        invoice = self._create_invoice_in_db()
        invoice_id = invoice.id
        
        self.assertIsNotNone(Invoice.query.get(invoice_id))
        
        response = self.client.delete(f'/api/invoices/{invoice_id}', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        
        deleted_invoice = Invoice.query.get(invoice_id)
        self.assertIsNone(deleted_invoice)
        
        items_count = InvoiceItem.query.filter_by(invoice_id=invoice_id).count()
        self.assertEqual(items_count, 0)


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

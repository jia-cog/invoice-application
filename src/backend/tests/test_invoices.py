#!/usr/bin/env python3
"""
Invoice Route Tests

Comprehensive tests for invoice CRUD endpoints.
"""

import sys
import os
import unittest
import json
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import Config
from models import db, User, Invoice, InvoiceItem
from app import create_app


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for invoice routes."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id
        
        response = self.client.post('/api/auth/login',
            json={'username': 'testuser', 'password': 'password123'})
        data = json.loads(response.data)
        self.token = data['access_token']
        self.headers = {'Authorization': f'Bearer {self.token}'}
    
    def tearDown(self):
        """Clean up after each test method."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_create_invoice_success(self):
        """Test successful invoice creation."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'customer_email': 'customer@example.com',
            'customer_address': '123 Test St',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'tax_rate': 10.0,
            'notes': 'Test invoice',
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 50.0},
                {'description': 'Item 2', 'quantity': 1, 'unit_price': 100.0}
            ]
        }
        
        response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        
        self.assertIn('message', data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
        self.assertEqual(len(data['invoice']['items']), 2)
        self.assertEqual(data['invoice']['subtotal'], 200.0)
        self.assertEqual(data['invoice']['tax_amount'], 20.0)
        self.assertEqual(data['invoice']['total_amount'], 220.0)
    
    def test_create_invoice_missing_customer_name(self):
        """Test invoice creation with missing customer_name."""
        invoice_data = {
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        
        response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('customer_name', data['error'].lower())
    
    def test_create_invoice_missing_due_date(self):
        """Test invoice creation with missing due_date."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        
        response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('due_date', data['error'].lower())
    
    def test_create_invoice_missing_items(self):
        """Test invoice creation with missing items."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('items', data['error'].lower())
    
    def test_create_invoice_invalid_item(self):
        """Test invoice creation with invalid item data."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'items': [
                {'description': 'Item 1', 'quantity': 1}  # Missing unit_price
            ]
        }
        
        response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_invoice_without_token(self):
        """Test invoice creation without authentication token."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        
        response = self.client.post('/api/invoices/', json=invoice_data)
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_invoices_empty(self):
        """Test getting invoices when none exist."""
        response = self.client.get('/api/invoices/', headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_success(self):
        """Test getting all invoices for a user."""
        for i in range(2):
            invoice_data = {
                'customer_name': f'Customer {i+1}',
                'due_date': (date.today() + timedelta(days=30)).isoformat(),
                'items': [
                    {'description': 'Item 1', 'quantity': 1, 'unit_price': 50.0}
                ]
            }
            self.client.post('/api/invoices/',
                json=invoice_data,
                headers=self.headers)
        
        response = self.client.get('/api/invoices/', headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_invoice_by_id_success(self):
        """Test getting a specific invoice by ID."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 50.0}
            ]
        }
        
        create_response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        create_data = json.loads(create_response.data)
        invoice_id = create_data['invoice']['id']
        
        response = self.client.get(f'/api/invoices/{invoice_id}',
            headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice_id)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_get_invoice_not_found(self):
        """Test getting a non-existent invoice."""
        response = self.client.get('/api/invoices/99999',
            headers=self.headers)
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_get_invoice_without_token(self):
        """Test getting invoice without authentication token."""
        response = self.client.get('/api/invoices/1')
        
        self.assertEqual(response.status_code, 401)
    
    def test_update_invoice_success(self):
        """Test successful invoice update."""
        invoice_data = {
            'customer_name': 'Original Customer',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        
        create_response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        create_data = json.loads(create_response.data)
        invoice_id = create_data['invoice']['id']
        
        update_data = {
            'customer_name': 'Updated Customer',
            'status': 'sent',
            'notes': 'Updated notes'
        }
        
        response = self.client.put(f'/api/invoices/{invoice_id}',
            json=update_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('message', data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'sent')
        self.assertEqual(data['invoice']['notes'], 'Updated notes')
    
    def test_update_invoice_items(self):
        """Test updating invoice items."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        
        create_response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        create_data = json.loads(create_response.data)
        invoice_id = create_data['invoice']['id']
        
        update_data = {
            'items': [
                {'description': 'New Item 1', 'quantity': 2, 'unit_price': 75.0},
                {'description': 'New Item 2', 'quantity': 1, 'unit_price': 100.0}
            ]
        }
        
        response = self.client.put(f'/api/invoices/{invoice_id}',
            json=update_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(len(data['invoice']['items']), 2)
        self.assertEqual(data['invoice']['subtotal'], 250.0)
    
    def test_update_invoice_not_found(self):
        """Test updating a non-existent invoice."""
        update_data = {
            'customer_name': 'Updated Customer'
        }
        
        response = self.client.put('/api/invoices/99999',
            json=update_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_update_invoice_without_token(self):
        """Test updating invoice without authentication token."""
        update_data = {
            'customer_name': 'Updated Customer'
        }
        
        response = self.client.put('/api/invoices/1', json=update_data)
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_success(self):
        """Test successful invoice deletion."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        
        create_response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        create_data = json.loads(create_response.data)
        invoice_id = create_data['invoice']['id']
        
        response = self.client.delete(f'/api/invoices/{invoice_id}',
            headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        
        get_response = self.client.get(f'/api/invoices/{invoice_id}',
            headers=self.headers)
        self.assertEqual(get_response.status_code, 404)
    
    def test_delete_invoice_not_found(self):
        """Test deleting a non-existent invoice."""
        response = self.client.delete('/api/invoices/99999',
            headers=self.headers)
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_delete_invoice_without_token(self):
        """Test deleting invoice without authentication token."""
        response = self.client.delete('/api/invoices/1')
        
        self.assertEqual(response.status_code, 401)
    
    def test_invoice_number_generation(self):
        """Test that invoice numbers are generated correctly."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        
        response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        
        data = json.loads(response.data)
        invoice_number = data['invoice']['invoice_number']
        
        self.assertTrue(invoice_number.startswith('INV-'))
        self.assertIn(date.today().strftime('%Y%m%d'), invoice_number)
    
    def test_invoice_status_values(self):
        """Test different invoice status values."""
        statuses = ['draft', 'sent', 'paid', 'overdue']
        
        for status in statuses:
            invoice_data = {
                'customer_name': f'Customer {status}',
                'due_date': (date.today() + timedelta(days=30)).isoformat(),
                'status': status,
                'items': [
                    {'description': 'Item 1', 'quantity': 1, 'unit_price': 50.0}
                ]
            }
            
            response = self.client.post('/api/invoices/',
                json=invoice_data,
                headers=self.headers)
            
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.data)
            self.assertEqual(data['invoice']['status'], status)
    
    def test_invoice_tax_calculation(self):
        """Test invoice tax calculation with different tax rates."""
        tax_rates = [0.0, 5.0, 10.0, 15.0]
        
        for tax_rate in tax_rates:
            invoice_data = {
                'customer_name': 'Test Customer',
                'due_date': (date.today() + timedelta(days=30)).isoformat(),
                'tax_rate': tax_rate,
                'items': [
                    {'description': 'Item 1', 'quantity': 1, 'unit_price': 100.0}
                ]
            }
            
            response = self.client.post('/api/invoices/',
                json=invoice_data,
                headers=self.headers)
            
            data = json.loads(response.data)
            expected_tax = 100.0 * (tax_rate / 100)
            expected_total = 100.0 + expected_tax
            
            self.assertAlmostEqual(data['invoice']['tax_amount'], expected_tax, places=2)
            self.assertAlmostEqual(data['invoice']['total_amount'], expected_total, places=2)
    
    def test_user_isolation(self):
        """Test that users can only access their own invoices."""
        with self.app.app_context():
            user2 = User(username='testuser2', email='test2@example.com')
            user2.set_password('password123')
            db.session.add(user2)
            db.session.commit()
        
        response = self.client.post('/api/auth/login',
            json={'username': 'testuser2', 'password': 'password123'})
        data = json.loads(response.data)
        token2 = data['access_token']
        headers2 = {'Authorization': f'Bearer {token2}'}
        
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        
        create_response = self.client.post('/api/invoices/',
            json=invoice_data,
            headers=self.headers)
        create_data = json.loads(create_response.data)
        invoice_id = create_data['invoice']['id']
        
        response = self.client.get(f'/api/invoices/{invoice_id}',
            headers=headers2)
        
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

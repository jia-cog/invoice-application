#!/usr/bin/env python3
"""
Invoice Routes Tests

Tests for invoice CRUD operations and API endpoints.
"""

import sys
import os
import unittest
from datetime import datetime, date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Invoice, InvoiceItem
from flask_jwt_extended import create_access_token


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for invoice CRUD operations."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        self.test_user1 = User(username='testuser1', email='test1@example.com', company_name='Test Co 1')
        self.test_user1.set_password('password123')
        db.session.add(self.test_user1)
        
        self.test_user2 = User(username='testuser2', email='test2@example.com', company_name='Test Co 2')
        self.test_user2.set_password('password456')
        db.session.add(self.test_user2)
        
        db.session.commit()
        
        with self.app.app_context():
            self.token_user1 = create_access_token(identity=str(self.test_user1.id))
            self.token_user2 = create_access_token(identity=str(self.test_user2.id))
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _create_test_invoice(self, user_token, status='draft'):
        """Helper method to create a test invoice."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'customer_email': 'customer@example.com',
            'customer_address': '123 Test St',
            'due_date': '2024-12-31',
            'tax_rate': 10.0,
            'status': status,
            'notes': 'Test invoice',
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 100.0},
                {'description': 'Item 2', 'quantity': 1, 'unit_price': 50.0}
            ]
        }
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers={'Authorization': f'Bearer {user_token}'}
        )
        return response
    
    def test_create_invoice_success(self):
        """Test successful invoice creation with items."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'customer_email': 'customer@example.com',
            'customer_address': '123 Test St',
            'due_date': '2024-12-31',
            'tax_rate': 10.0,
            'status': 'draft',
            'notes': 'Test invoice',
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 100.0},
                {'description': 'Item 2', 'quantity': 1, 'unit_price': 50.0}
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
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
        self.assertEqual(len(data['invoice']['items']), 2)
    
    def test_create_invoice_missing_customer_name(self):
        """Test invoice creation fails when customer_name is missing."""
        invoice_data = {
            'due_date': '2024-12-31',
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 100.0}
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
    
    def test_create_invoice_missing_due_date(self):
        """Test invoice creation fails when due_date is missing."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 100.0}
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
    
    def test_create_invoice_missing_items(self):
        """Test invoice creation fails when items are missing."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': '2024-12-31'
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_missing_item_description(self):
        """Test invoice creation fails when item description is missing."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': '2024-12-31',
            'items': [
                {'quantity': 1, 'unit_price': 100.0}
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
    
    def test_create_invoice_missing_item_quantity(self):
        """Test invoice creation fails when item quantity is missing."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': '2024-12-31',
            'items': [
                {'description': 'Item 1', 'unit_price': 100.0}
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
    
    def test_create_invoice_missing_item_unit_price(self):
        """Test invoice creation fails when item unit_price is missing."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': '2024-12-31',
            'items': [
                {'description': 'Item 1', 'quantity': 1}
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
    
    def test_create_invoice_calculations(self):
        """Test that invoice calculations are correct."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': '2024-12-31',
            'tax_rate': 10.0,
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 100.0},
                {'description': 'Item 2', 'quantity': 1, 'unit_price': 50.0}
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
        
        expected_subtotal = 250.0
        expected_tax_amount = 25.0
        expected_total = 275.0
        
        self.assertEqual(invoice['subtotal'], expected_subtotal)
        self.assertEqual(invoice['tax_amount'], expected_tax_amount)
        self.assertEqual(invoice['total_amount'], expected_total)
    
    def test_create_invoice_unauthorized(self):
        """Test invoice creation fails without JWT token."""
        invoice_data = {
            'customer_name': 'Test Customer',
            'due_date': '2024-12-31',
            'items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 100.0}
            ]
        }
        
        response = self.client.post('/api/invoices/', json=invoice_data)
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_all_invoices_success(self):
        """Test getting all invoices for a user."""
        self._create_test_invoice(self.token_user1)
        self._create_test_invoice(self.token_user1, status='sent')
        
        response = self.client.get(
            '/api/invoices/',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_all_invoices_empty(self):
        """Test getting invoices returns empty list when user has no invoices."""
        response = self.client.get(
            '/api/invoices/',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_all_invoices_user_isolation(self):
        """Test that users only see their own invoices."""
        self._create_test_invoice(self.token_user1)
        self._create_test_invoice(self.token_user1)
        self._create_test_invoice(self.token_user2)
        
        response = self.client.get(
            '/api/invoices/',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_all_invoices_unauthorized(self):
        """Test getting invoices fails without JWT token."""
        response = self.client.get('/api/invoices/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_invoice_by_id_success(self):
        """Test getting a specific invoice by ID."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice_id)
    
    def test_get_invoice_not_found(self):
        """Test getting non-existent invoice returns 404."""
        response = self.client.get(
            '/api/invoices/99999',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_get_invoice_wrong_user(self):
        """Test that user cannot access another user's invoice."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers={'Authorization': f'Bearer {self.token_user2}'}
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_get_invoice_unauthorized(self):
        """Test getting invoice fails without JWT token."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        response = self.client.get(f'/api/invoices/{invoice_id}')
        
        self.assertEqual(response.status_code, 401)
    
    def test_update_invoice_success(self):
        """Test successfully updating an invoice."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        update_data = {
            'customer_name': 'Updated Customer',
            'status': 'paid',
            'notes': 'Updated notes'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json=update_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'paid')
        self.assertEqual(data['invoice']['notes'], 'Updated notes')
    
    def test_update_invoice_items(self):
        """Test updating invoice items replaces existing items."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        update_data = {
            'items': [
                {'description': 'New Item', 'quantity': 3, 'unit_price': 75.0}
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json=update_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['invoice']['items']), 1)
        self.assertEqual(data['invoice']['items'][0]['description'], 'New Item')
    
    def test_update_invoice_recalculates_totals(self):
        """Test that updating items recalculates invoice totals."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        update_data = {
            'tax_rate': 15.0,
            'items': [
                {'description': 'New Item', 'quantity': 1, 'unit_price': 100.0}
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json=update_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        invoice = data['invoice']
        
        expected_subtotal = 100.0
        expected_tax_amount = 15.0
        expected_total = 115.0
        
        self.assertEqual(invoice['subtotal'], expected_subtotal)
        self.assertEqual(invoice['tax_amount'], expected_tax_amount)
        self.assertEqual(invoice['total_amount'], expected_total)
    
    def test_update_invoice_not_found(self):
        """Test updating non-existent invoice returns 404."""
        update_data = {'customer_name': 'Updated Customer'}
        
        response = self.client.put(
            '/api/invoices/99999',
            json=update_data,
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_invoice_wrong_user(self):
        """Test that user cannot update another user's invoice."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        update_data = {'customer_name': 'Hacked Customer'}
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json=update_data,
            headers={'Authorization': f'Bearer {self.token_user2}'}
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_invoice_unauthorized(self):
        """Test updating invoice fails without JWT token."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        update_data = {'customer_name': 'Updated Customer'}
        
        response = self.client.put(
            f'/api/invoices/{invoice_id}',
            json=update_data
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_success(self):
        """Test successfully deleting an invoice."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        
        get_response = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        self.assertEqual(get_response.status_code, 404)
    
    def test_delete_invoice_not_found(self):
        """Test deleting non-existent invoice returns 404."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_invoice_wrong_user(self):
        """Test that user cannot delete another user's invoice."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers={'Authorization': f'Bearer {self.token_user2}'}
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_invoice_unauthorized(self):
        """Test deleting invoice fails without JWT token."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        response = self.client.delete(f'/api/invoices/{invoice_id}')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_cascade_items(self):
        """Test that deleting an invoice also deletes its items."""
        create_response = self._create_test_invoice(self.token_user1)
        invoice_id = create_response.get_json()['invoice']['id']
        
        invoice = Invoice.query.get(invoice_id)
        self.assertIsNotNone(invoice)
        self.assertTrue(len(invoice.items) > 0)
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers={'Authorization': f'Bearer {self.token_user1}'}
        )
        
        self.assertEqual(response.status_code, 200)
        
        invoice = Invoice.query.get(invoice_id)
        self.assertIsNone(invoice)
        
        items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items), 0)


def run_invoice_tests():
    """Run all invoice route tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoiceRoutes)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_invoice_tests()
    if success:
        print("\n✅ All invoice route tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some invoice route tests failed!")
        sys.exit(1)

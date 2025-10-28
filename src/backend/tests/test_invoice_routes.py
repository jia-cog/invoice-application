#!/usr/bin/env python3
"""
Invoice Routes Tests

Tests for invoice CRUD operations, authorization, validation, and calculations.
"""

import sys
import os
import unittest
from datetime import datetime, date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import create_access_token
from app import create_app
from models import db, User, Invoice, InvoiceItem
from config import Config


class TestInvoiceRoutes(unittest.TestCase):
    """Test cases for invoice route functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        self.client = self.app.test_client()
        
        user1 = User(username='testuser1', email='test1@example.com', company_name='Test Company 1')
        user1.set_password('password123')
        db.session.add(user1)
        
        user2 = User(username='testuser2', email='test2@example.com', company_name='Test Company 2')
        user2.set_password('password456')
        db.session.add(user2)
        
        db.session.commit()
        
        self.user1_id = user1.id
        self.user2_id = user2.id
        self.user1_token = create_access_token(identity=str(user1.id))
        self.user2_token = create_access_token(identity=str(user2.id))
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def get_auth_headers(self, token):
        """Helper method to create authorization headers."""
        return {'Authorization': f'Bearer {token}'}
    
    def create_test_invoice(self, user_id, customer_name='Test Customer', items=None):
        """Helper method to create a test invoice."""
        if items is None:
            items = [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 100.0},
                {'description': 'Item 2', 'quantity': 1, 'unit_price': 50.0}
            ]
        
        invoice = Invoice(
            invoice_number=f'INV-TEST-{datetime.now().timestamp()}',
            user_id=user_id,
            customer_name=customer_name,
            customer_email='customer@example.com',
            customer_address='123 Test St',
            due_date=date(2024, 12, 31),
            tax_rate=10.0,
            status='draft'
        )
        db.session.add(invoice)
        db.session.flush()
        
        for item_data in items:
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=item_data['description'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price']
            )
            item.calculate_total()
            db.session.add(item)
        
        invoice.calculate_totals()
        db.session.commit()
        
        return invoice
    
    def test_get_invoices_empty(self):
        """Test GET /api/invoices/ with no invoices returns empty list."""
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 0)
    
    def test_get_invoices_with_data(self):
        """Test GET /api/invoices/ returns user's invoices."""
        self.create_test_invoice(self.user1_id, 'Customer A')
        self.create_test_invoice(self.user1_id, 'Customer B')
        
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoices', data)
        self.assertEqual(len(data['invoices']), 2)
    
    def test_get_invoices_user_isolation(self):
        """Test that users only see their own invoices."""
        self.create_test_invoice(self.user1_id, 'User 1 Customer')
        self.create_test_invoice(self.user2_id, 'User 2 Customer')
        
        response = self.client.get(
            '/api/invoices/',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'User 1 Customer')
    
    def test_get_invoices_no_auth(self):
        """Test GET /api/invoices/ without authentication returns 401."""
        response = self.client.get('/api/invoices/')
        self.assertEqual(response.status_code, 401)
    
    def test_get_invoice_by_id_success(self):
        """Test GET /api/invoices/<id> returns the invoice."""
        invoice = self.create_test_invoice(self.user1_id)
        
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], invoice.id)
        self.assertEqual(data['invoice']['customer_name'], 'Test Customer')
    
    def test_get_invoice_not_found(self):
        """Test GET /api/invoices/<id> with non-existent ID returns 404."""
        response = self.client.get(
            '/api/invoices/99999',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_get_invoice_unauthorized_access(self):
        """Test that users cannot access other users' invoices."""
        invoice = self.create_test_invoice(self.user2_id)
        
        response = self.client.get(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_get_invoice_no_auth(self):
        """Test GET /api/invoices/<id> without authentication returns 401."""
        invoice = self.create_test_invoice(self.user1_id)
        response = self.client.get(f'/api/invoices/{invoice.id}')
        self.assertEqual(response.status_code, 401)
    
    def test_create_invoice_success(self):
        """Test POST /api/invoices/ creates an invoice successfully."""
        invoice_data = {
            'customer_name': 'New Customer',
            'customer_email': 'new@example.com',
            'customer_address': '456 New St',
            'due_date': '2024-12-31',
            'tax_rate': 8.5,
            'status': 'draft',
            'items': [
                {'description': 'Product 1', 'quantity': 3, 'unit_price': 25.0},
                {'description': 'Product 2', 'quantity': 1, 'unit_price': 100.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('invoice', data)
        self.assertIn('message', data)
        self.assertEqual(data['invoice']['customer_name'], 'New Customer')
        self.assertEqual(len(data['invoice']['items']), 2)
    
    def test_create_invoice_missing_customer_name(self):
        """Test POST /api/invoices/ without customer_name returns 400."""
        invoice_data = {
            'due_date': '2024-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 10.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_missing_due_date(self):
        """Test POST /api/invoices/ without due_date returns 400."""
        invoice_data = {
            'customer_name': 'Customer',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 10.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_missing_items(self):
        """Test POST /api/invoices/ without items returns 400."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2024-12-31'
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_invalid_item_data(self):
        """Test POST /api/invoices/ with incomplete item data returns 400."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2024-12-31',
            'items': [{'description': 'Item'}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_create_invoice_calculations(self):
        """Test that invoice calculations are correct."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2024-12-31',
            'tax_rate': 10.0,
            'items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 50.0},
                {'description': 'Item 2', 'quantity': 1, 'unit_price': 100.0}
            ]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        invoice = data['invoice']
        
        expected_subtotal = 200.0
        expected_tax = 20.0
        expected_total = 220.0
        
        self.assertEqual(invoice['subtotal'], expected_subtotal)
        self.assertEqual(invoice['tax_amount'], expected_tax)
        self.assertEqual(invoice['total_amount'], expected_total)
    
    def test_create_invoice_number_generation(self):
        """Test that invoice numbers are generated in correct format."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2024-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 10.0}]
        }
        
        response = self.client.post(
            '/api/invoices/',
            json=invoice_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        invoice_number = data['invoice']['invoice_number']
        
        self.assertTrue(invoice_number.startswith('INV-'))
        self.assertIn(datetime.now().strftime('%Y%m%d'), invoice_number)
    
    def test_create_invoice_no_auth(self):
        """Test POST /api/invoices/ without authentication returns 401."""
        invoice_data = {
            'customer_name': 'Customer',
            'due_date': '2024-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 10.0}]
        }
        
        response = self.client.post('/api/invoices/', json=invoice_data)
        self.assertEqual(response.status_code, 401)
    
    def test_update_invoice_success(self):
        """Test PUT /api/invoices/<id> updates invoice fields."""
        invoice = self.create_test_invoice(self.user1_id)
        
        update_data = {
            'customer_name': 'Updated Customer',
            'status': 'sent'
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['invoice']['customer_name'], 'Updated Customer')
        self.assertEqual(data['invoice']['status'], 'sent')
    
    def test_update_invoice_items(self):
        """Test PUT /api/invoices/<id> updates items and recalculates totals."""
        invoice = self.create_test_invoice(self.user1_id)
        
        update_data = {
            'tax_rate': 5.0,
            'items': [
                {'description': 'New Item', 'quantity': 5, 'unit_price': 20.0}
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['invoice']['items']), 1)
        self.assertEqual(data['invoice']['subtotal'], 100.0)
        self.assertEqual(data['invoice']['tax_amount'], 5.0)
        self.assertEqual(data['invoice']['total_amount'], 105.0)
    
    def test_update_invoice_not_found(self):
        """Test PUT /api/invoices/<id> with non-existent ID returns 404."""
        update_data = {'customer_name': 'Updated'}
        
        response = self.client.put(
            '/api/invoices/99999',
            json=update_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_invoice_unauthorized(self):
        """Test that users cannot update other users' invoices."""
        invoice = self.create_test_invoice(self.user2_id)
        
        update_data = {'customer_name': 'Hacked'}
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_invoice_recalculates_totals(self):
        """Test that totals are recalculated after updating items."""
        invoice = self.create_test_invoice(self.user1_id)
        
        update_data = {
            'tax_rate': 15.0,
            'items': [
                {'description': 'Item A', 'quantity': 10, 'unit_price': 10.0}
            ]
        }
        
        response = self.client.put(
            f'/api/invoices/{invoice.id}',
            json=update_data,
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['invoice']['subtotal'], 100.0)
        self.assertEqual(data['invoice']['tax_amount'], 15.0)
        self.assertEqual(data['invoice']['total_amount'], 115.0)
    
    def test_update_invoice_no_auth(self):
        """Test PUT /api/invoices/<id> without authentication returns 401."""
        invoice = self.create_test_invoice(self.user1_id)
        update_data = {'customer_name': 'Updated'}
        
        response = self.client.put(f'/api/invoices/{invoice.id}', json=update_data)
        self.assertEqual(response.status_code, 401)
    
    def test_delete_invoice_success(self):
        """Test DELETE /api/invoices/<id> deletes the invoice."""
        invoice = self.create_test_invoice(self.user1_id)
        invoice_id = invoice.id
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        
        deleted_invoice = Invoice.query.get(invoice_id)
        self.assertIsNone(deleted_invoice)
    
    def test_delete_invoice_not_found(self):
        """Test DELETE /api/invoices/<id> with non-existent ID returns 404."""
        response = self.client.delete(
            '/api/invoices/99999',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_invoice_unauthorized(self):
        """Test that users cannot delete other users' invoices."""
        invoice = self.create_test_invoice(self.user2_id)
        
        response = self.client.delete(
            f'/api/invoices/{invoice.id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_invoice_cascade_items(self):
        """Test that invoice items are deleted when invoice is deleted."""
        invoice = self.create_test_invoice(self.user1_id)
        invoice_id = invoice.id
        
        items_count = InvoiceItem.query.filter_by(invoice_id=invoice_id).count()
        self.assertGreater(items_count, 0)
        
        response = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.get_auth_headers(self.user1_token)
        )
        
        self.assertEqual(response.status_code, 200)
        
        remaining_items = InvoiceItem.query.filter_by(invoice_id=invoice_id).count()
        self.assertEqual(remaining_items, 0)
    
    def test_delete_invoice_no_auth(self):
        """Test DELETE /api/invoices/<id> without authentication returns 401."""
        invoice = self.create_test_invoice(self.user1_id)
        response = self.client.delete(f'/api/invoices/{invoice.id}')
        self.assertEqual(response.status_code, 401)


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
        print("\n✅ All invoice route tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some invoice route tests failed!")
        sys.exit(1)

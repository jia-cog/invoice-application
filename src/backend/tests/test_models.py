#!/usr/bin/env python3
"""
Model Tests

Comprehensive tests for User, Invoice, InvoiceItem, and Report models.
"""

import sys
import os
import unittest
from datetime import datetime, date, timedelta
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import Config
from models import db, User, Invoice, InvoiceItem, Report


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'


class TestUserModel(unittest.TestCase):
    """Test cases for User model."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_user_creation(self):
        """Test creating a new user."""
        user = User(
            username='testuser',
            email='test@example.com',
            company_name='Test Company'
        )
        user.set_password('password123')
        
        db.session.add(user)
        db.session.commit()
        
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.company_name, 'Test Company')
        self.assertIsNotNone(user.password_hash)
        self.assertNotEqual(user.password_hash, 'password123')
    
    def test_set_password(self):
        """Test password hashing."""
        user = User(username='testuser', email='test@example.com')
        user.set_password('mypassword')
        
        self.assertIsNotNone(user.password_hash)
        self.assertNotEqual(user.password_hash, 'mypassword')
        self.assertTrue(len(user.password_hash) > 20)
    
    def test_check_password_correct(self):
        """Test password verification with correct password."""
        user = User(username='testuser', email='test@example.com')
        user.set_password('correctpassword')
        
        self.assertTrue(user.check_password('correctpassword'))
    
    def test_check_password_incorrect(self):
        """Test password verification with incorrect password."""
        user = User(username='testuser', email='test@example.com')
        user.set_password('correctpassword')
        
        self.assertFalse(user.check_password('wrongpassword'))
    
    def test_user_to_dict(self):
        """Test user serialization to dictionary."""
        user = User(
            username='testuser',
            email='test@example.com',
            company_name='Test Company'
        )
        user.set_password('password123')
        
        db.session.add(user)
        db.session.commit()
        
        user_dict = user.to_dict()
        
        self.assertIn('id', user_dict)
        self.assertIn('username', user_dict)
        self.assertIn('email', user_dict)
        self.assertIn('company_name', user_dict)
        self.assertIn('created_at', user_dict)
        self.assertNotIn('password_hash', user_dict)
        
        self.assertEqual(user_dict['username'], 'testuser')
        self.assertEqual(user_dict['email'], 'test@example.com')
    
    def test_user_unique_username(self):
        """Test that usernames must be unique."""
        user1 = User(username='testuser', email='test1@example.com')
        user1.set_password('password123')
        db.session.add(user1)
        db.session.commit()
        
        user2 = User(username='testuser', email='test2@example.com')
        user2.set_password('password456')
        db.session.add(user2)
        
        with self.assertRaises(Exception):
            db.session.commit()
    
    def test_user_unique_email(self):
        """Test that emails must be unique."""
        user1 = User(username='testuser1', email='test@example.com')
        user1.set_password('password123')
        db.session.add(user1)
        db.session.commit()
        
        user2 = User(username='testuser2', email='test@example.com')
        user2.set_password('password456')
        db.session.add(user2)
        
        with self.assertRaises(Exception):
            db.session.commit()
    
    def test_user_invoices_relationship(self):
        """Test user-invoices relationship."""
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        invoice = Invoice(
            invoice_number='INV-001',
            user_id=user.id,
            customer_name='Customer 1',
            due_date=date.today()
        )
        db.session.add(invoice)
        db.session.commit()
        
        self.assertEqual(len(user.invoices), 1)
        self.assertEqual(user.invoices[0].invoice_number, 'INV-001')


class TestInvoiceModel(unittest.TestCase):
    """Test cases for Invoice model."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_invoice_creation(self):
        """Test creating a new invoice."""
        invoice = Invoice(
            invoice_number='INV-001',
            user_id=self.user.id,
            customer_name='Test Customer',
            customer_email='customer@example.com',
            customer_address='123 Test St',
            due_date=date.today() + timedelta(days=30),
            tax_rate=10.0,
            status='draft'
        )
        
        db.session.add(invoice)
        db.session.commit()
        
        self.assertIsNotNone(invoice.id)
        self.assertEqual(invoice.invoice_number, 'INV-001')
        self.assertEqual(invoice.customer_name, 'Test Customer')
        self.assertEqual(invoice.status, 'draft')
    
    def test_invoice_calculate_totals_no_items(self):
        """Test calculate_totals with no items."""
        invoice = Invoice(
            invoice_number='INV-001',
            user_id=self.user.id,
            customer_name='Test Customer',
            due_date=date.today(),
            tax_rate=10.0
        )
        
        db.session.add(invoice)
        db.session.commit()
        
        invoice.calculate_totals()
        
        self.assertEqual(invoice.subtotal, 0.0)
        self.assertEqual(invoice.tax_amount, 0.0)
        self.assertEqual(invoice.total_amount, 0.0)
    
    def test_invoice_calculate_totals_with_items(self):
        """Test calculate_totals with items."""
        invoice = Invoice(
            invoice_number='INV-001',
            user_id=self.user.id,
            customer_name='Test Customer',
            due_date=date.today(),
            tax_rate=10.0
        )
        
        db.session.add(invoice)
        db.session.flush()
        
        item1 = InvoiceItem(
            invoice_id=invoice.id,
            description='Item 1',
            quantity=2.0,
            unit_price=50.0
        )
        item1.calculate_total()
        
        item2 = InvoiceItem(
            invoice_id=invoice.id,
            description='Item 2',
            quantity=1.0,
            unit_price=100.0
        )
        item2.calculate_total()
        
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        
        invoice.calculate_totals()
        
        self.assertEqual(invoice.subtotal, 200.0)
        self.assertEqual(invoice.tax_amount, 20.0)
        self.assertEqual(invoice.total_amount, 220.0)
    
    def test_invoice_to_dict(self):
        """Test invoice serialization to dictionary."""
        invoice = Invoice(
            invoice_number='INV-001',
            user_id=self.user.id,
            customer_name='Test Customer',
            customer_email='customer@example.com',
            due_date=date.today(),
            tax_rate=10.0,
            status='draft'
        )
        
        db.session.add(invoice)
        db.session.commit()
        
        invoice_dict = invoice.to_dict()
        
        self.assertIn('id', invoice_dict)
        self.assertIn('invoice_number', invoice_dict)
        self.assertIn('customer_name', invoice_dict)
        self.assertIn('customer_email', invoice_dict)
        self.assertIn('status', invoice_dict)
        self.assertIn('items', invoice_dict)
        
        self.assertEqual(invoice_dict['invoice_number'], 'INV-001')
        self.assertEqual(invoice_dict['customer_name'], 'Test Customer')
        self.assertIsInstance(invoice_dict['items'], list)
    
    def test_invoice_unique_invoice_number(self):
        """Test that invoice numbers must be unique."""
        invoice1 = Invoice(
            invoice_number='INV-001',
            user_id=self.user.id,
            customer_name='Customer 1',
            due_date=date.today()
        )
        db.session.add(invoice1)
        db.session.commit()
        
        invoice2 = Invoice(
            invoice_number='INV-001',
            user_id=self.user.id,
            customer_name='Customer 2',
            due_date=date.today()
        )
        db.session.add(invoice2)
        
        with self.assertRaises(Exception):
            db.session.commit()
    
    def test_invoice_items_relationship(self):
        """Test invoice-items relationship."""
        invoice = Invoice(
            invoice_number='INV-001',
            user_id=self.user.id,
            customer_name='Test Customer',
            due_date=date.today()
        )
        
        db.session.add(invoice)
        db.session.flush()
        
        item1 = InvoiceItem(
            invoice_id=invoice.id,
            description='Item 1',
            quantity=1.0,
            unit_price=50.0
        )
        item1.calculate_total()
        
        item2 = InvoiceItem(
            invoice_id=invoice.id,
            description='Item 2',
            quantity=2.0,
            unit_price=75.0
        )
        item2.calculate_total()
        
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        
        self.assertEqual(len(invoice.items), 2)
        self.assertEqual(invoice.items[0].description, 'Item 1')
        self.assertEqual(invoice.items[1].description, 'Item 2')
    
    def test_invoice_cascade_delete(self):
        """Test that deleting an invoice deletes its items."""
        invoice = Invoice(
            invoice_number='INV-001',
            user_id=self.user.id,
            customer_name='Test Customer',
            due_date=date.today()
        )
        
        db.session.add(invoice)
        db.session.flush()
        
        item = InvoiceItem(
            invoice_id=invoice.id,
            description='Item 1',
            quantity=1.0,
            unit_price=50.0
        )
        item.calculate_total()
        db.session.add(item)
        db.session.commit()
        
        invoice_id = invoice.id
        
        db.session.delete(invoice)
        db.session.commit()
        
        items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items), 0)


class TestInvoiceItemModel(unittest.TestCase):
    """Test cases for InvoiceItem model."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()
        
        self.invoice = Invoice(
            invoice_number='INV-001',
            user_id=self.user.id,
            customer_name='Test Customer',
            due_date=date.today()
        )
        db.session.add(self.invoice)
        db.session.commit()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_invoice_item_creation(self):
        """Test creating a new invoice item."""
        item = InvoiceItem(
            invoice_id=self.invoice.id,
            description='Test Item',
            quantity=3.0,
            unit_price=25.50
        )
        item.calculate_total()
        
        db.session.add(item)
        db.session.commit()
        
        self.assertIsNotNone(item.id)
        self.assertEqual(item.description, 'Test Item')
        self.assertEqual(item.quantity, 3.0)
        self.assertEqual(item.unit_price, 25.50)
        self.assertEqual(item.total, 76.50)
    
    def test_calculate_total(self):
        """Test calculate_total method."""
        item = InvoiceItem(
            invoice_id=self.invoice.id,
            description='Test Item',
            quantity=5.0,
            unit_price=10.0
        )
        item.calculate_total()
        
        self.assertEqual(item.total, 50.0)
    
    def test_calculate_total_decimal_quantity(self):
        """Test calculate_total with decimal quantity."""
        item = InvoiceItem(
            invoice_id=self.invoice.id,
            description='Test Item',
            quantity=2.5,
            unit_price=20.0
        )
        item.calculate_total()
        
        self.assertEqual(item.total, 50.0)
    
    def test_calculate_total_decimal_price(self):
        """Test calculate_total with decimal price."""
        item = InvoiceItem(
            invoice_id=self.invoice.id,
            description='Test Item',
            quantity=3.0,
            unit_price=15.99
        )
        item.calculate_total()
        
        self.assertAlmostEqual(item.total, 47.97, places=2)
    
    def test_invoice_item_to_dict(self):
        """Test invoice item serialization to dictionary."""
        item = InvoiceItem(
            invoice_id=self.invoice.id,
            description='Test Item',
            quantity=2.0,
            unit_price=50.0
        )
        item.calculate_total()
        
        db.session.add(item)
        db.session.commit()
        
        item_dict = item.to_dict()
        
        self.assertIn('id', item_dict)
        self.assertIn('description', item_dict)
        self.assertIn('quantity', item_dict)
        self.assertIn('unit_price', item_dict)
        self.assertIn('total', item_dict)
        
        self.assertEqual(item_dict['description'], 'Test Item')
        self.assertEqual(item_dict['quantity'], 2.0)
        self.assertEqual(item_dict['unit_price'], 50.0)
        self.assertEqual(item_dict['total'], 100.0)


class TestReportModel(unittest.TestCase):
    """Test cases for Report model."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_report_creation(self):
        """Test creating a new report."""
        report = Report(
            user_id=self.user.id,
            report_type='monthly',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        db.session.add(report)
        db.session.commit()
        
        self.assertIsNotNone(report.id)
        self.assertEqual(report.report_type, 'monthly')
        self.assertEqual(report.start_date, date(2024, 1, 1))
        self.assertEqual(report.end_date, date(2024, 1, 31))
    
    def test_set_data(self):
        """Test set_data method."""
        report = Report(
            user_id=self.user.id,
            report_type='monthly',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        test_data = {
            'total_revenue': 1000.0,
            'total_invoices': 5,
            'status_breakdown': {'paid': 3, 'pending': 2}
        }
        
        report.set_data(test_data)
        
        self.assertIsNotNone(report.data)
        self.assertIsInstance(report.data, str)
    
    def test_get_data(self):
        """Test get_data method."""
        report = Report(
            user_id=self.user.id,
            report_type='monthly',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        test_data = {
            'total_revenue': 1000.0,
            'total_invoices': 5,
            'status_breakdown': {'paid': 3, 'pending': 2}
        }
        
        report.set_data(test_data)
        retrieved_data = report.get_data()
        
        self.assertEqual(retrieved_data, test_data)
        self.assertEqual(retrieved_data['total_revenue'], 1000.0)
        self.assertEqual(retrieved_data['total_invoices'], 5)
    
    def test_get_data_empty(self):
        """Test get_data with no data set."""
        report = Report(
            user_id=self.user.id,
            report_type='monthly',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        data = report.get_data()
        
        self.assertEqual(data, {})
    
    def test_report_to_dict(self):
        """Test report serialization to dictionary."""
        report = Report(
            user_id=self.user.id,
            report_type='quarterly',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31)
        )
        
        test_data = {
            'total_revenue': 5000.0,
            'total_invoices': 20
        }
        report.set_data(test_data)
        
        db.session.add(report)
        db.session.commit()
        
        report_dict = report.to_dict()
        
        self.assertIn('id', report_dict)
        self.assertIn('report_type', report_dict)
        self.assertIn('start_date', report_dict)
        self.assertIn('end_date', report_dict)
        self.assertIn('data', report_dict)
        self.assertIn('created_at', report_dict)
        
        self.assertEqual(report_dict['report_type'], 'quarterly')
        self.assertIsInstance(report_dict['data'], dict)
        self.assertEqual(report_dict['data']['total_revenue'], 5000.0)
    
    def test_report_types(self):
        """Test different report types."""
        report_types = ['monthly', 'quarterly', 'yearly', 'custom']
        
        for report_type in report_types:
            report = Report(
                user_id=self.user.id,
                report_type=report_type,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31)
            )
            db.session.add(report)
        
        db.session.commit()
        
        reports = Report.query.filter_by(user_id=self.user.id).all()
        self.assertEqual(len(reports), 4)


def run_model_tests():
    """Run all model tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestUserModel))
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceModel))
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceItemModel))
    suite.addTests(loader.loadTestsFromTestCase(TestReportModel))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_model_tests()
    if success:
        print("\n✅ All model tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some model tests failed!")
        sys.exit(1)

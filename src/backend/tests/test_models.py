#!/usr/bin/env python3
"""
Model Unit Tests

Tests for Invoice, InvoiceItem, and Report model methods including
calculations and serialization.
"""

import sys
import os
import unittest
from datetime import date, datetime

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from models import db, User, Invoice, InvoiceItem, Report


class TestInvoiceItemCalculateTotal(unittest.TestCase):
    """Test cases for InvoiceItem.calculate_total()."""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _make_item(self, quantity, unit_price):
        """Create an InvoiceItem with given quantity and unit_price, calculate total."""
        item = InvoiceItem(
            invoice_id=1,
            description='Test item',
            quantity=quantity,
            unit_price=unit_price,
            total=0
        )
        item.calculate_total()
        return item

    def test_integer_values(self):
        """Total is correct for integer quantity and unit_price."""
        item = self._make_item(3, 10)
        self.assertAlmostEqual(item.total, 30.0)

    def test_float_values(self):
        """Total is correct for float quantity and unit_price."""
        item = self._make_item(2.5, 4.0)
        self.assertAlmostEqual(item.total, 10.0)

    def test_zero_quantity(self):
        """Total is zero when quantity is zero."""
        item = self._make_item(0, 100.0)
        self.assertAlmostEqual(item.total, 0.0)

    def test_zero_unit_price(self):
        """Total is zero when unit_price is zero."""
        item = self._make_item(5, 0.0)
        self.assertAlmostEqual(item.total, 0.0)

    def test_large_values(self):
        """Total is correct for large values."""
        item = self._make_item(1000, 999.99)
        self.assertAlmostEqual(item.total, 999990.0)

    def test_fractional_precision(self):
        """Total handles fractional precision."""
        item = self._make_item(3, 0.1)
        self.assertAlmostEqual(item.total, 0.3, places=5)


class TestInvoiceCalculateTotals(unittest.TestCase):
    """Test cases for Invoice.calculate_totals()."""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create a user and a base invoice
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _make_invoice(self, tax_rate=0.0, items=None):
        """Create an invoice with given tax_rate and items, then calculate totals."""
        invoice = Invoice(
            invoice_number='INV-TEST-001',
            user_id=self.user.id,
            customer_name='Test Customer',
            due_date=date(2026, 12, 31),
            tax_rate=tax_rate,
        )
        db.session.add(invoice)
        db.session.flush()

        if items:
            for qty, price in items:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description='Item',
                    quantity=qty,
                    unit_price=price,
                    total=qty * price,
                )
                db.session.add(item)
            db.session.flush()

        # Refresh relationship
        db.session.expire(invoice, ['items'])
        invoice.calculate_totals()
        return invoice

    def test_no_items(self):
        """Totals are zero when invoice has no items."""
        invoice = self._make_invoice(tax_rate=10.0, items=None)
        self.assertAlmostEqual(invoice.subtotal, 0.0)
        self.assertAlmostEqual(invoice.tax_amount, 0.0)
        self.assertAlmostEqual(invoice.total_amount, 0.0)

    def test_zero_tax_rate(self):
        """With zero tax, total_amount equals subtotal."""
        invoice = self._make_invoice(tax_rate=0.0, items=[(2, 50.0), (1, 100.0)])
        self.assertAlmostEqual(invoice.subtotal, 200.0)
        self.assertAlmostEqual(invoice.tax_amount, 0.0)
        self.assertAlmostEqual(invoice.total_amount, 200.0)

    def test_nonzero_tax_rate(self):
        """Tax is correctly applied to subtotal."""
        invoice = self._make_invoice(tax_rate=15.0, items=[(1, 200.0)])
        self.assertAlmostEqual(invoice.subtotal, 200.0)
        self.assertAlmostEqual(invoice.tax_amount, 30.0)
        self.assertAlmostEqual(invoice.total_amount, 230.0)

    def test_multiple_items(self):
        """Subtotal is the sum of all item totals."""
        invoice = self._make_invoice(tax_rate=10.0, items=[(1, 100.0), (2, 50.0), (3, 30.0)])
        # 100 + 100 + 90 = 290
        self.assertAlmostEqual(invoice.subtotal, 290.0)
        self.assertAlmostEqual(invoice.tax_amount, 29.0)
        self.assertAlmostEqual(invoice.total_amount, 319.0)


class TestInvoiceToDict(unittest.TestCase):
    """Test cases for Invoice.to_dict() serialization."""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_invoice_to_dict_keys(self):
        """Invoice.to_dict() returns all expected keys."""
        invoice = Invoice(
            invoice_number='INV-TEST-002',
            user_id=self.user.id,
            customer_name='Dict Customer',
            due_date=date(2026, 12, 31),
            issue_date=date(2026, 1, 1),
            tax_rate=0.0,
            subtotal=0.0,
            tax_amount=0.0,
            total_amount=0.0,
        )
        db.session.add(invoice)
        db.session.commit()

        d = invoice.to_dict()
        expected_keys = {
            'id', 'invoice_number', 'customer_name', 'customer_email',
            'customer_address', 'issue_date', 'due_date', 'status',
            'subtotal', 'tax_rate', 'tax_amount', 'total_amount',
            'notes', 'created_at', 'updated_at', 'items'
        }
        self.assertEqual(set(d.keys()), expected_keys)

    def test_invoice_to_dict_values(self):
        """Invoice.to_dict() returns correct values for known fields."""
        invoice = Invoice(
            invoice_number='INV-TEST-003',
            user_id=self.user.id,
            customer_name='Value Customer',
            due_date=date(2026, 6, 15),
            issue_date=date(2026, 1, 1),
            status='sent',
            tax_rate=5.0,
            subtotal=100.0,
            tax_amount=5.0,
            total_amount=105.0,
            notes='Test note',
        )
        db.session.add(invoice)
        db.session.commit()

        d = invoice.to_dict()
        self.assertEqual(d['invoice_number'], 'INV-TEST-003')
        self.assertEqual(d['customer_name'], 'Value Customer')
        self.assertEqual(d['status'], 'sent')
        self.assertAlmostEqual(d['total_amount'], 105.0)
        self.assertEqual(d['items'], [])


class TestInvoiceItemToDict(unittest.TestCase):
    """Test cases for InvoiceItem.to_dict() serialization."""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()

        self.invoice = Invoice(
            invoice_number='INV-TEST-ITEM',
            user_id=self.user.id,
            customer_name='Item Customer',
            due_date=date(2026, 12, 31),
            issue_date=date(2026, 1, 1),
            tax_rate=0.0,
            subtotal=0.0,
            tax_amount=0.0,
            total_amount=0.0,
        )
        db.session.add(self.invoice)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_invoice_item_to_dict_keys(self):
        """InvoiceItem.to_dict() returns all expected keys."""
        item = InvoiceItem(
            invoice_id=self.invoice.id,
            description='Gadget',
            quantity=3,
            unit_price=25.0,
            total=75.0,
        )
        db.session.add(item)
        db.session.commit()

        d = item.to_dict()
        expected_keys = {'id', 'description', 'quantity', 'unit_price', 'total'}
        self.assertEqual(set(d.keys()), expected_keys)

    def test_invoice_item_to_dict_values(self):
        """InvoiceItem.to_dict() returns correct values."""
        item = InvoiceItem(
            invoice_id=self.invoice.id,
            description='Gizmo',
            quantity=4,
            unit_price=12.5,
            total=50.0,
        )
        db.session.add(item)
        db.session.commit()

        d = item.to_dict()
        self.assertEqual(d['description'], 'Gizmo')
        self.assertEqual(d['quantity'], 4)
        self.assertAlmostEqual(d['unit_price'], 12.5)
        self.assertAlmostEqual(d['total'], 50.0)


def run_model_tests():
    """Run all model tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceItemCalculateTotal))
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceCalculateTotals))
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceToDict))
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceItemToDict))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_model_tests()
    if success:
        print("\nAll model tests passed!")
        sys.exit(0)
    else:
        print("\nSome model tests failed!")
        sys.exit(1)

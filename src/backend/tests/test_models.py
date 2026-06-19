"""
Unit tests for database models: User, Invoice, InvoiceItem, Report.
"""

import sys
import os
import unittest
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Invoice, InvoiceItem, Report


class ModelTestCase(unittest.TestCase):
    """Base for model-level tests using an in-memory database."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _make_user(self, username='alice', email='alice@test.com',
                   password='secret'):
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user


class TestUserModel(ModelTestCase):

    def test_set_and_check_password(self):
        user = self._make_user()
        self.assertTrue(user.check_password('secret'))
        self.assertFalse(user.check_password('wrong'))

    def test_password_hash_is_not_plaintext(self):
        user = self._make_user()
        self.assertNotEqual(user.password_hash, 'secret')

    def test_to_dict_excludes_password(self):
        user = self._make_user()
        d = user.to_dict()
        self.assertNotIn('password_hash', d)
        self.assertNotIn('password', d)
        self.assertIn('username', d)
        self.assertIn('email', d)

    def test_user_created_at(self):
        user = self._make_user()
        self.assertIsNotNone(user.created_at)

    def test_unique_username(self):
        self._make_user(username='dup', email='a@a.com')
        with self.assertRaises(Exception):
            self._make_user(username='dup', email='b@b.com')

    def test_unique_email(self):
        self._make_user(username='u1', email='dup@test.com')
        with self.assertRaises(Exception):
            self._make_user(username='u2', email='dup@test.com')


class TestInvoiceModel(ModelTestCase):

    def _make_invoice(self, user):
        invoice = Invoice(
            invoice_number='INV-001',
            user_id=user.id,
            customer_name='Client',
            due_date=date(2026, 12, 31),
        )
        db.session.add(invoice)
        db.session.flush()
        return invoice

    def test_calculate_totals_no_items(self):
        user = self._make_user()
        inv = self._make_invoice(user)
        inv.calculate_totals()

        self.assertAlmostEqual(inv.subtotal, 0.0)
        self.assertAlmostEqual(inv.total_amount, 0.0)

    def test_calculate_totals_with_items(self):
        user = self._make_user()
        inv = self._make_invoice(user)
        inv.tax_rate = 10.0

        item1 = InvoiceItem(invoice_id=inv.id, description='A',
                            quantity=2, unit_price=50, total=100)
        item2 = InvoiceItem(invoice_id=inv.id, description='B',
                            quantity=1, unit_price=100, total=100)
        db.session.add_all([item1, item2])
        db.session.flush()

        inv.calculate_totals()

        self.assertAlmostEqual(inv.subtotal, 200.0)
        self.assertAlmostEqual(inv.tax_amount, 20.0)
        self.assertAlmostEqual(inv.total_amount, 220.0)

    def test_to_dict_fields(self):
        user = self._make_user()
        inv = self._make_invoice(user)
        db.session.commit()
        d = inv.to_dict()

        expected_keys = {
            'id', 'invoice_number', 'customer_name', 'customer_email',
            'customer_address', 'issue_date', 'due_date', 'status',
            'subtotal', 'tax_rate', 'tax_amount', 'total_amount',
            'notes', 'created_at', 'updated_at', 'items',
        }
        self.assertTrue(expected_keys.issubset(d.keys()))

    def test_default_status_is_draft(self):
        user = self._make_user()
        inv = self._make_invoice(user)
        self.assertEqual(inv.status, 'draft')

    def test_cascade_delete_items(self):
        user = self._make_user()
        inv = self._make_invoice(user)
        item = InvoiceItem(invoice_id=inv.id, description='X',
                           quantity=1, unit_price=10, total=10)
        db.session.add(item)
        db.session.commit()

        db.session.delete(inv)
        db.session.commit()

        self.assertEqual(InvoiceItem.query.count(), 0)


class TestInvoiceItemModel(ModelTestCase):

    def test_calculate_total(self):
        item = InvoiceItem(description='Svc', quantity=3, unit_price=25.0,
                           total=0)
        item.calculate_total()
        self.assertAlmostEqual(item.total, 75.0)

    def test_to_dict(self):
        item = InvoiceItem(description='Svc', quantity=1, unit_price=10,
                           total=10)
        d = item.to_dict()
        self.assertIn('description', d)
        self.assertIn('quantity', d)
        self.assertIn('unit_price', d)
        self.assertIn('total', d)


class TestReportModel(ModelTestCase):

    def _make_report(self, user):
        report = Report(
            user_id=user.id,
            report_type='monthly',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.session.add(report)
        db.session.commit()
        return report

    def test_set_and_get_data(self):
        user = self._make_user()
        report = self._make_report(user)
        payload = {'total_invoices': 5, 'total_revenue': 1000.0}
        report.set_data(payload)
        db.session.commit()

        fetched = Report.query.get(report.id)
        self.assertEqual(fetched.get_data(), payload)

    def test_get_data_empty(self):
        user = self._make_user()
        report = self._make_report(user)
        self.assertEqual(report.get_data(), {})

    def test_to_dict(self):
        user = self._make_user()
        report = self._make_report(user)
        report.set_data({'key': 'value'})
        db.session.commit()

        d = report.to_dict()
        self.assertIn('report_type', d)
        self.assertIn('start_date', d)
        self.assertIn('end_date', d)
        self.assertIn('data', d)
        self.assertEqual(d['data']['key'], 'value')


if __name__ == '__main__':
    unittest.main()

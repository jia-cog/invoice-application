#!/usr/bin/env python3
"""
Invoice Export Route Tests

Tests for CSV export endpoints, focusing on edge cases
where no invoices exist.
"""

import sys
import os
import csv
import io
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from config import Config
from models import db, User, Invoice, InvoiceItem
from routes.invoices import invoices_bp


class TestExportRoutes(unittest.TestCase):
    """Test cases for invoice export endpoints."""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True

        db.init_app(self.app)
        JWTManager(self.app)
        self.app.register_blueprint(invoices_bp, url_prefix='/api/invoices')

        with self.app.app_context():
            db.create_all()
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _auth_header(self):
        with self.app.app_context():
            token = create_access_token(identity=str(self.user_id))
            return {'Authorization': f'Bearer {token}'}

    def test_export_all_no_invoices_returns_200_with_header_only(self):
        """GET /export for user with zero invoices returns 200 and CSV header only."""
        resp = self.client.get('/api/invoices/export', headers=self._auth_header())

        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp.content_type)
        self.assertIn('attachment; filename=invoices.csv',
                      resp.headers.get('Content-Disposition', ''))

        reader = csv.reader(io.StringIO(resp.data.decode('utf-8')))
        rows = list(reader)

        # Should have exactly one row: the header
        self.assertEqual(len(rows), 1)
        expected_columns = [
            'id', 'invoice_number', 'customer_name', 'customer_email',
            'customer_address', 'issue_date', 'due_date', 'status',
            'subtotal', 'tax_rate', 'tax_amount', 'total_amount',
            'notes', 'created_at', 'updated_at'
        ]
        self.assertEqual(rows[0], expected_columns)

    def test_export_single_nonexistent_invoice_returns_404(self):
        """GET /<id>/export for non-existent invoice returns 404."""
        resp = self.client.get('/api/invoices/9999/export', headers=self._auth_header())

        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertIn('error', data)

    def test_export_all_no_auth_returns_401(self):
        """GET /export without auth token returns 401."""
        resp = self.client.get('/api/invoices/export')
        self.assertEqual(resp.status_code, 401)

    def test_export_single_no_auth_returns_401(self):
        """GET /<id>/export without auth token returns 401."""
        resp = self.client.get('/api/invoices/1/export')
        self.assertEqual(resp.status_code, 401)

    def test_export_all_with_invoices_returns_data_rows(self):
        """GET /export with invoices returns header + data rows."""
        with self.app.app_context():
            from datetime import datetime
            invoice = Invoice(
                invoice_number='INV-TEST-001',
                user_id=self.user_id,
                customer_name='Test Customer',
                customer_email='customer@test.com',
                customer_address='123 Test St',
                due_date=datetime(2026, 12, 31).date(),
                status='draft',
                subtotal=100.0,
                tax_rate=10.0,
                tax_amount=10.0,
                total_amount=110.0,
            )
            db.session.add(invoice)
            db.session.commit()

        resp = self.client.get('/api/invoices/export', headers=self._auth_header())
        self.assertEqual(resp.status_code, 200)

        reader = csv.reader(io.StringIO(resp.data.decode('utf-8')))
        rows = list(reader)
        self.assertEqual(len(rows), 2)  # header + 1 data row
        self.assertEqual(rows[1][2], 'Test Customer')

    def test_export_single_invoice_returns_csv(self):
        """GET /<id>/export for existing invoice returns CSV with one data row."""
        with self.app.app_context():
            from datetime import datetime
            invoice = Invoice(
                invoice_number='INV-TEST-002',
                user_id=self.user_id,
                customer_name='Single Export',
                customer_email='single@test.com',
                customer_address='456 Export Ave',
                due_date=datetime(2026, 12, 31).date(),
                status='sent',
                subtotal=200.0,
                tax_rate=5.0,
                tax_amount=10.0,
                total_amount=210.0,
            )
            db.session.add(invoice)
            db.session.commit()
            invoice_id = invoice.id

        resp = self.client.get(f'/api/invoices/{invoice_id}/export',
                               headers=self._auth_header())
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp.content_type)

        reader = csv.reader(io.StringIO(resp.data.decode('utf-8')))
        rows = list(reader)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][2], 'Single Export')

    def test_export_single_other_users_invoice_returns_404(self):
        """GET /<id>/export for another user's invoice returns 404."""
        with self.app.app_context():
            from datetime import datetime
            other_user = User(username='other', email='other@example.com')
            other_user.set_password('pass')
            db.session.add(other_user)
            db.session.flush()

            invoice = Invoice(
                invoice_number='INV-OTHER-001',
                user_id=other_user.id,
                customer_name='Other Customer',
                due_date=datetime(2026, 12, 31).date(),
                status='draft',
                subtotal=0.0,
                tax_rate=0.0,
                tax_amount=0.0,
                total_amount=0.0,
            )
            db.session.add(invoice)
            db.session.commit()
            invoice_id = invoice.id

        resp = self.client.get(f'/api/invoices/{invoice_id}/export',
                               headers=self._auth_header())
        self.assertEqual(resp.status_code, 404)


def run_export_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestExportRoutes)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_export_tests()
    sys.exit(0 if success else 1)

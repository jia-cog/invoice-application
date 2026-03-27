#!/usr/bin/env python3
"""
Report Generation Tests

Tests for the report generation endpoint including filtering, status breakdown,
top customers, and edge cases.
"""

import sys
import os
import unittest
import json
from datetime import date

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from models import db, User, Invoice, InvoiceItem
from routes.reports import reports_bp


class TestReportGeneration(unittest.TestCase):
    """Test cases for report generation endpoints."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True

        db.init_app(self.app)
        JWTManager(self.app)
        self.app.register_blueprint(reports_bp, url_prefix='/api/reports')

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

        # Create a test user
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()

        self.token = create_access_token(identity=str(self.user.id))
        self.auth_headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ---- Helpers ----

    def _create_invoice_directly(self, customer_name='Customer', status='draft',
                                  issue_date=None, total_amount=100.0, tax_rate=0.0,
                                  items=None):
        """Create an invoice directly in the database."""
        if issue_date is None:
            issue_date = date(2026, 6, 15)

        invoice = Invoice(
            invoice_number=f'INV-TEST-{Invoice.query.count() + 1:04d}',
            user_id=self.user.id,
            customer_name=customer_name,
            issue_date=issue_date,
            due_date=date(2026, 12, 31),
            status=status,
            tax_rate=tax_rate,
            subtotal=total_amount,
            tax_amount=total_amount * (tax_rate / 100),
            total_amount=total_amount + total_amount * (tax_rate / 100),
        )
        db.session.add(invoice)
        db.session.flush()

        if items:
            for desc, qty, price in items:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=desc,
                    quantity=qty,
                    unit_price=price,
                    total=qty * price,
                )
                db.session.add(item)
        db.session.commit()
        return invoice

    def _generate_report(self, report_type='monthly', start_date='2026-01-01',
                          end_date='2026-12-31'):
        """Call the generate report endpoint."""
        data = {
            'report_type': report_type,
            'start_date': start_date,
            'end_date': end_date,
        }
        return self.client.post(
            '/api/reports/generate',
            data=json.dumps(data),
            headers=self.auth_headers,
        )

    # ---- POST /api/reports/generate — success ----

    def test_generate_report_success(self):
        """POST /api/reports/generate returns 201 with expected structure."""
        self._create_invoice_directly(total_amount=500.0, status='paid')
        resp = self._generate_report()
        self.assertEqual(resp.status_code, 201)

        body = resp.get_json()
        report_data = body['report']['data']

        # Verify top-level keys
        self.assertIn('summary', report_data)
        self.assertIn('status_breakdown', report_data)
        self.assertIn('monthly_data', report_data)
        self.assertIn('top_customers', report_data)
        self.assertIn('date_range', report_data)

    def test_generate_report_summary_fields(self):
        """Summary contains all expected metric fields."""
        self._create_invoice_directly(total_amount=200.0, status='paid')
        resp = self._generate_report()
        summary = resp.get_json()['report']['data']['summary']

        expected_fields = {
            'total_invoices', 'total_revenue', 'paid_revenue',
            'pending_revenue', 'overdue_revenue', 'average_invoice_value'
        }
        self.assertEqual(set(summary.keys()), expected_fields)

    def test_generate_report_summary_values(self):
        """Summary values are correct for a single paid invoice."""
        self._create_invoice_directly(total_amount=300.0, status='paid')
        resp = self._generate_report()
        summary = resp.get_json()['report']['data']['summary']

        self.assertEqual(summary['total_invoices'], 1)
        self.assertAlmostEqual(summary['total_revenue'], 300.0)
        self.assertAlmostEqual(summary['paid_revenue'], 300.0)
        self.assertAlmostEqual(summary['pending_revenue'], 0.0)
        self.assertAlmostEqual(summary['overdue_revenue'], 0.0)
        self.assertAlmostEqual(summary['average_invoice_value'], 300.0)

    # ---- Validation ----

    def test_generate_report_missing_report_type(self):
        """Missing report_type returns 400."""
        resp = self.client.post(
            '/api/reports/generate',
            data=json.dumps({'start_date': '2026-01-01', 'end_date': '2026-12-31'}),
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_missing_start_date(self):
        """Missing start_date returns 400."""
        resp = self.client.post(
            '/api/reports/generate',
            data=json.dumps({'report_type': 'monthly', 'end_date': '2026-12-31'}),
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_missing_end_date(self):
        """Missing end_date returns 400."""
        resp = self.client.post(
            '/api/reports/generate',
            data=json.dumps({'report_type': 'monthly', 'start_date': '2026-01-01'}),
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 400)

    # ---- Date range filtering ----

    def test_date_range_includes_only_matching_invoices(self):
        """Only invoices within the date range are included."""
        self._create_invoice_directly(issue_date=date(2026, 3, 15), total_amount=100.0)
        self._create_invoice_directly(issue_date=date(2026, 6, 15), total_amount=200.0)
        self._create_invoice_directly(issue_date=date(2026, 9, 15), total_amount=400.0)

        # Only include Q2 (April–June)
        resp = self._generate_report(start_date='2026-04-01', end_date='2026-06-30')
        summary = resp.get_json()['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 1)
        self.assertAlmostEqual(summary['total_revenue'], 200.0)

    def test_date_range_boundary_inclusive(self):
        """Invoices on the exact start and end dates are included."""
        self._create_invoice_directly(issue_date=date(2026, 1, 1), total_amount=50.0)
        self._create_invoice_directly(issue_date=date(2026, 12, 31), total_amount=75.0)

        resp = self._generate_report(start_date='2026-01-01', end_date='2026-12-31')
        summary = resp.get_json()['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 2)
        self.assertAlmostEqual(summary['total_revenue'], 125.0)

    # ---- Status breakdown ----

    def test_status_breakdown(self):
        """Status breakdown correctly counts invoices by status."""
        self._create_invoice_directly(status='draft')
        self._create_invoice_directly(status='draft')
        self._create_invoice_directly(status='sent')
        self._create_invoice_directly(status='paid')
        self._create_invoice_directly(status='paid')
        self._create_invoice_directly(status='paid')
        self._create_invoice_directly(status='overdue')

        resp = self._generate_report()
        breakdown = resp.get_json()['report']['data']['status_breakdown']
        self.assertEqual(breakdown['draft'], 2)
        self.assertEqual(breakdown['sent'], 1)
        self.assertEqual(breakdown['paid'], 3)
        self.assertEqual(breakdown['overdue'], 1)

    # ---- Top customers ----

    def test_top_customers_sorted_by_revenue(self):
        """Top customers are sorted by revenue descending."""
        self._create_invoice_directly(customer_name='Low Corp', total_amount=100.0)
        self._create_invoice_directly(customer_name='High Corp', total_amount=500.0)
        self._create_invoice_directly(customer_name='Mid Corp', total_amount=300.0)

        resp = self._generate_report()
        top = resp.get_json()['report']['data']['top_customers']
        names = [c['name'] for c in top]
        self.assertEqual(names, ['High Corp', 'Mid Corp', 'Low Corp'])

    def test_top_customers_limited_to_five(self):
        """Top customers list is limited to 5 entries."""
        for i in range(8):
            self._create_invoice_directly(
                customer_name=f'Customer {i}',
                total_amount=float((i + 1) * 100),
            )

        resp = self._generate_report()
        top = resp.get_json()['report']['data']['top_customers']
        self.assertEqual(len(top), 5)

    def test_top_customers_aggregates_revenue(self):
        """Revenue is aggregated across multiple invoices for the same customer."""
        self._create_invoice_directly(customer_name='Repeat Corp', total_amount=100.0)
        self._create_invoice_directly(customer_name='Repeat Corp', total_amount=200.0)
        self._create_invoice_directly(customer_name='Single Corp', total_amount=250.0)

        resp = self._generate_report()
        top = resp.get_json()['report']['data']['top_customers']
        # Repeat Corp total = 300, Single Corp = 250
        self.assertEqual(top[0]['name'], 'Repeat Corp')
        self.assertAlmostEqual(top[0]['revenue'], 300.0)

    # ---- Empty date range ----

    def test_empty_date_range_no_division_by_zero(self):
        """Report with zero invoices handles gracefully (no division by zero)."""
        resp = self._generate_report(start_date='2020-01-01', end_date='2020-12-31')
        self.assertEqual(resp.status_code, 201)

        summary = resp.get_json()['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 0)
        self.assertAlmostEqual(summary['total_revenue'], 0.0)
        self.assertAlmostEqual(summary['average_invoice_value'], 0)

    # ---- Monthly data ----

    def test_monthly_data_breakdown(self):
        """Monthly data groups invoices by month."""
        self._create_invoice_directly(issue_date=date(2026, 1, 10), total_amount=100.0)
        self._create_invoice_directly(issue_date=date(2026, 1, 20), total_amount=150.0)
        self._create_invoice_directly(issue_date=date(2026, 3, 5), total_amount=200.0)

        resp = self._generate_report()
        monthly = resp.get_json()['report']['data']['monthly_data']

        # Should have 2 months: January and March
        self.assertEqual(len(monthly), 2)
        months = {m['month'] for m in monthly}
        self.assertIn('January 2026', months)
        self.assertIn('March 2026', months)

    # ---- Authentication ----

    def test_generate_report_no_token(self):
        """POST /api/reports/generate returns 401 without JWT."""
        resp = self.client.post(
            '/api/reports/generate',
            data=json.dumps({
                'report_type': 'monthly',
                'start_date': '2026-01-01',
                'end_date': '2026-12-31',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 401)


def run_report_tests():
    """Run all report tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestReportGeneration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_report_tests()
    if success:
        print("\nAll report tests passed!")
        sys.exit(0)
    else:
        print("\nSome report tests failed!")
        sys.exit(1)

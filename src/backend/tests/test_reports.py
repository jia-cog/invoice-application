#!/usr/bin/env python3
"""
Report Endpoint Tests

Comprehensive test suite for all 4 report endpoints:
- GET /api/reports (list)
- POST /api/reports/generate (generate)
- GET /api/reports/dashboard (dashboard)
- DELETE /api/reports/<id> (delete)
"""

import sys
import os
import unittest
import json
from datetime import date, datetime, timedelta

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set DATABASE_URL before importing app so create_app() uses in-memory SQLite
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import create_app
from models import db, Invoice


class TestReportEndpoints(unittest.TestCase):
    """Test cases for all report endpoints."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        # Register a test user and store the access token
        resp = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'password123'
        })
        data = json.loads(resp.data)
        self.token = data['access_token']
        self.user_id = data['user']['id']

    def tearDown(self):
        """Clean up after each test method."""
        db.drop_all()
        self.app_context.pop()

    # ------------------------------------------------------------------ helpers

    def auth_headers(self):
        """Return Authorization and Content-Type headers."""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def create_test_invoice(self, status='draft', customer_name='Test Customer',
                            issue_date=None, total_amount=100.0):
        """Directly insert an Invoice record into the DB for deterministic testing."""
        inv = Invoice(
            invoice_number=f'INV-TEST-{Invoice.query.count() + 1}',
            user_id=self.user_id,
            customer_name=customer_name,
            customer_email='customer@test.com',
            customer_address='123 Test St',
            issue_date=issue_date or date.today(),
            due_date=date(2025, 12, 31),
            status=status,
            subtotal=total_amount,
            tax_rate=0.0,
            tax_amount=0.0,
            total_amount=total_amount,
            notes='Test'
        )
        db.session.add(inv)
        db.session.commit()
        return inv

    def seed_invoices(self):
        """Create several invoices spanning Jan-Mar 2025 with varied statuses and customers."""
        seeds = [
            # January 2025
            {'status': 'paid',    'customer_name': 'Alice', 'issue_date': date(2025, 1, 10), 'total_amount': 500.0},
            {'status': 'draft',   'customer_name': 'Bob',   'issue_date': date(2025, 1, 20), 'total_amount': 300.0},
            # February 2025
            {'status': 'sent',    'customer_name': 'Alice', 'issue_date': date(2025, 2, 5),  'total_amount': 200.0},
            {'status': 'overdue', 'customer_name': 'Carol', 'issue_date': date(2025, 2, 15), 'total_amount': 400.0},
            # March 2025
            {'status': 'paid',    'customer_name': 'Bob',   'issue_date': date(2025, 3, 1),  'total_amount': 600.0},
            {'status': 'draft',   'customer_name': 'Carol', 'issue_date': date(2025, 3, 25), 'total_amount': 150.0},
        ]
        for s in seeds:
            self.create_test_invoice(**s)

    def _register_second_user(self):
        """Register a second user and return (token, user_id)."""
        resp = self.client.post('/api/auth/register', json={
            'username': 'otheruser',
            'email': 'other@test.com',
            'password': 'password456'
        })
        data = json.loads(resp.data)
        return data['access_token'], data['user']['id']

    def _generate_report(self, headers=None, payload=None):
        """Helper to generate a report with sensible defaults."""
        if headers is None:
            headers = self.auth_headers()
        if payload is None:
            payload = {
                'report_type': 'monthly',
                'start_date': '2025-01-01',
                'end_date': '2025-01-31'
            }
        return self.client.post('/api/reports/generate', headers=headers, json=payload)

    # ======================================================================
    # GET /api/reports  (get_reports)
    # ======================================================================

    def test_get_reports_empty(self):
        """1. GET with no reports -> 200, empty list."""
        resp = self.client.get('/api/reports/', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['reports'], [])

    def test_get_reports_returns_all(self):
        """2. Generate 2 reports, GET -> returns 2."""
        self.seed_invoices()
        self._generate_report()
        self._generate_report(payload={
            'report_type': 'monthly',
            'start_date': '2025-02-01',
            'end_date': '2025-02-28'
        })
        resp = self.client.get('/api/reports/', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data['reports']), 2)

    def test_get_reports_without_auth(self):
        """3. GET without token -> 401."""
        resp = self.client.get('/api/reports/')
        self.assertEqual(resp.status_code, 401)

    def test_get_reports_user_isolation(self):
        """4. Each user sees only their own reports."""
        self.seed_invoices()
        self._generate_report()

        token2, user2_id = self._register_second_user()
        headers2 = {'Authorization': f'Bearer {token2}', 'Content-Type': 'application/json'}

        # Create an invoice for user2 so they can generate a report
        inv = Invoice(
            invoice_number='INV-USER2-1',
            user_id=user2_id,
            customer_name='U2 Customer',
            issue_date=date(2025, 1, 15),
            due_date=date(2025, 12, 31),
            status='paid',
            subtotal=100, tax_rate=0, tax_amount=0, total_amount=100
        )
        db.session.add(inv)
        db.session.commit()

        self._generate_report(headers=headers2)

        resp1 = self.client.get('/api/reports/', headers=self.auth_headers())
        resp2 = self.client.get('/api/reports/', headers=headers2)
        self.assertEqual(len(json.loads(resp1.data)['reports']), 1)
        self.assertEqual(len(json.loads(resp2.data)['reports']), 1)

    # ======================================================================
    # POST /api/reports/generate  (generate_report)
    # ======================================================================

    def test_generate_report_success(self):
        """5. Seed invoices, generate monthly report -> 201 with correct fields."""
        self.seed_invoices()
        resp = self._generate_report()
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertIn('message', data)
        self.assertIn('report', data)
        report = data['report']
        self.assertEqual(report['report_type'], 'monthly')
        self.assertEqual(report['start_date'], '2025-01-01')
        self.assertEqual(report['end_date'], '2025-01-31')

    def test_generate_report_data_summary(self):
        """6. Verify data.summary metrics match seeded data."""
        self.seed_invoices()
        resp = self._generate_report(payload={
            'report_type': 'custom',
            'start_date': '2025-01-01',
            'end_date': '2025-03-31'
        })
        self.assertEqual(resp.status_code, 201)
        summary = json.loads(resp.data)['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 6)
        self.assertAlmostEqual(summary['total_revenue'], 2150.0)
        # paid: 500 + 600 = 1100
        self.assertAlmostEqual(summary['paid_revenue'], 1100.0)
        # pending (draft+sent): 300 + 200 + 150 = 650
        self.assertAlmostEqual(summary['pending_revenue'], 650.0)
        # overdue: 400
        self.assertAlmostEqual(summary['overdue_revenue'], 400.0)
        # average: 2150/6 ≈ 358.33
        self.assertAlmostEqual(summary['average_invoice_value'], round(2150.0 / 6, 2))

    def test_generate_report_status_breakdown(self):
        """7. Verify status_breakdown counts."""
        self.seed_invoices()
        resp = self._generate_report(payload={
            'report_type': 'custom',
            'start_date': '2025-01-01',
            'end_date': '2025-03-31'
        })
        breakdown = json.loads(resp.data)['report']['data']['status_breakdown']
        self.assertEqual(breakdown['paid'], 2)
        self.assertEqual(breakdown['draft'], 2)
        self.assertEqual(breakdown['sent'], 1)
        self.assertEqual(breakdown['overdue'], 1)

    def test_generate_report_top_customers(self):
        """8. top_customers sorted by revenue desc, limited to 5."""
        self.seed_invoices()
        resp = self._generate_report(payload={
            'report_type': 'custom',
            'start_date': '2025-01-01',
            'end_date': '2025-03-31'
        })
        top_customers = json.loads(resp.data)['report']['data']['top_customers']
        # Should be sorted by revenue descending
        revenues = [c['revenue'] for c in top_customers]
        self.assertEqual(revenues, sorted(revenues, reverse=True))
        self.assertLessEqual(len(top_customers), 5)

    def test_generate_report_monthly_data(self):
        """9. monthly_data has entries for each month with correct counts and revenue."""
        self.seed_invoices()
        resp = self._generate_report(payload={
            'report_type': 'custom',
            'start_date': '2025-01-01',
            'end_date': '2025-03-31'
        })
        monthly = json.loads(resp.data)['report']['data']['monthly_data']
        # Should have 3 months: Jan, Feb, Mar
        self.assertEqual(len(monthly), 3)
        month_map = {m['month']: m for m in monthly}
        self.assertEqual(month_map['January 2025']['count'], 2)
        self.assertAlmostEqual(month_map['January 2025']['revenue'], 800.0)
        self.assertEqual(month_map['February 2025']['count'], 2)
        self.assertAlmostEqual(month_map['February 2025']['revenue'], 600.0)
        self.assertEqual(month_map['March 2025']['count'], 2)
        self.assertAlmostEqual(month_map['March 2025']['revenue'], 750.0)

    def test_generate_report_empty_date_range(self):
        """10. Report for date range with no invoices -> 201, totals are 0."""
        resp = self._generate_report(payload={
            'report_type': 'monthly',
            'start_date': '2099-01-01',
            'end_date': '2099-01-31'
        })
        self.assertEqual(resp.status_code, 201)
        summary = json.loads(resp.data)['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 0)
        self.assertEqual(summary['total_revenue'], 0)
        self.assertEqual(summary['average_invoice_value'], 0)

    def test_generate_report_missing_report_type(self):
        """11. Omit report_type -> 400."""
        resp = self._generate_report(payload={
            'start_date': '2025-01-01',
            'end_date': '2025-01-31'
        })
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_missing_start_date(self):
        """12. Omit start_date -> 400."""
        resp = self._generate_report(payload={
            'report_type': 'monthly',
            'end_date': '2025-01-31'
        })
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_missing_end_date(self):
        """13. Omit end_date -> 400."""
        resp = self._generate_report(payload={
            'report_type': 'monthly',
            'start_date': '2025-01-01'
        })
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_without_auth(self):
        """14. POST without auth -> 401."""
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31'
        })
        self.assertEqual(resp.status_code, 401)

    def test_generate_report_all_types(self):
        """15. All report_type values accepted: monthly, quarterly, yearly, custom."""
        self.seed_invoices()
        for rtype in ['monthly', 'quarterly', 'yearly', 'custom']:
            resp = self._generate_report(payload={
                'report_type': rtype,
                'start_date': '2025-01-01',
                'end_date': '2025-03-31'
            })
            self.assertEqual(resp.status_code, 201, f'Failed for report_type={rtype}')
            self.assertEqual(json.loads(resp.data)['report']['report_type'], rtype)

    # ======================================================================
    # GET /api/reports/dashboard  (get_dashboard_data)
    # ======================================================================

    def test_dashboard_empty(self):
        """16. Dashboard with no invoices -> overview zeroes, empty recent."""
        resp = self.client.get('/api/reports/dashboard', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['overview']['total_invoices'], 0)
        self.assertEqual(data['overview']['total_revenue'], 0)
        self.assertEqual(data['recent_invoices'], [])

    def test_dashboard_overview_metrics(self):
        """17. Verify overview metrics with known data."""
        self.create_test_invoice(status='paid', total_amount=500.0)
        self.create_test_invoice(status='paid', total_amount=300.0)
        self.create_test_invoice(status='draft', total_amount=200.0)
        self.create_test_invoice(status='sent', total_amount=100.0)
        self.create_test_invoice(status='overdue', total_amount=400.0)

        resp = self.client.get('/api/reports/dashboard', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        overview = json.loads(resp.data)['overview']
        self.assertEqual(overview['total_invoices'], 5)
        self.assertAlmostEqual(overview['total_revenue'], 1500.0)
        self.assertEqual(overview['paid_count'], 2)
        self.assertEqual(overview['pending_count'], 2)  # draft + sent
        self.assertEqual(overview['overdue_count'], 1)

    def test_dashboard_monthly_revenue(self):
        """18. monthly_revenue only counts current month invoices."""
        today = date.today()
        first_of_month = today.replace(day=1)
        last_month = (first_of_month - timedelta(days=1))

        # Invoice in current month
        self.create_test_invoice(issue_date=today, total_amount=250.0)
        # Invoice in previous month
        self.create_test_invoice(issue_date=last_month, total_amount=750.0)

        resp = self.client.get('/api/reports/dashboard', headers=self.auth_headers())
        overview = json.loads(resp.data)['overview']
        self.assertAlmostEqual(overview['monthly_revenue'], 250.0)

    def test_dashboard_recent_invoices_limit(self):
        """19. Create 7 invoices -> recent_invoices returns only 5."""
        for i in range(7):
            self.create_test_invoice(customer_name=f'C{i}', total_amount=float(i * 10))

        resp = self.client.get('/api/reports/dashboard', headers=self.auth_headers())
        recent = json.loads(resp.data)['recent_invoices']
        self.assertEqual(len(recent), 5)

    def test_dashboard_recent_invoices_order(self):
        """20. recent_invoices ordered by created_at descending."""
        for i in range(5):
            self.create_test_invoice(customer_name=f'C{i}')

        resp = self.client.get('/api/reports/dashboard', headers=self.auth_headers())
        recent = json.loads(resp.data)['recent_invoices']
        created_dates = [inv['created_at'] for inv in recent]
        self.assertEqual(created_dates, sorted(created_dates, reverse=True))

    def test_dashboard_without_auth(self):
        """21. GET dashboard without auth -> 401."""
        resp = self.client.get('/api/reports/dashboard')
        self.assertEqual(resp.status_code, 401)

    def test_dashboard_user_isolation(self):
        """22. Dashboard shows only current user's data."""
        self.create_test_invoice(status='paid', total_amount=100.0)

        token2, user2_id = self._register_second_user()
        headers2 = {'Authorization': f'Bearer {token2}', 'Content-Type': 'application/json'}

        # Create invoice for user2 directly
        inv = Invoice(
            invoice_number='INV-U2-1',
            user_id=user2_id,
            customer_name='U2 Cust',
            issue_date=date.today(),
            due_date=date(2025, 12, 31),
            status='paid',
            subtotal=999, tax_rate=0, tax_amount=0, total_amount=999
        )
        db.session.add(inv)
        db.session.commit()

        # User 1 dashboard
        resp1 = self.client.get('/api/reports/dashboard', headers=self.auth_headers())
        overview1 = json.loads(resp1.data)['overview']
        self.assertEqual(overview1['total_invoices'], 1)
        self.assertAlmostEqual(overview1['total_revenue'], 100.0)

        # User 2 dashboard
        resp2 = self.client.get('/api/reports/dashboard', headers=headers2)
        overview2 = json.loads(resp2.data)['overview']
        self.assertEqual(overview2['total_invoices'], 1)
        self.assertAlmostEqual(overview2['total_revenue'], 999.0)

    # ======================================================================
    # DELETE /api/reports/<id>  (delete_report)
    # ======================================================================

    def test_delete_report_success(self):
        """23. Generate a report, DELETE it -> 200, then GET shows it's gone."""
        self.seed_invoices()
        gen_resp = self._generate_report()
        report_id = json.loads(gen_resp.data)['report']['id']
        resp = self.client.delete(f'/api/reports/{report_id}', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)

        # Verify it's gone
        list_resp = self.client.get('/api/reports/', headers=self.auth_headers())
        reports = json.loads(list_resp.data)['reports']
        self.assertEqual(len(reports), 0)

    def test_delete_report_not_found(self):
        """24. DELETE non-existent ID -> 404."""
        resp = self.client.delete('/api/reports/99999', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 404)

    def test_delete_report_other_user(self):
        """25. Delete another user's report -> 404."""
        self.seed_invoices()
        gen_resp = self._generate_report()
        report_id = json.loads(gen_resp.data)['report']['id']

        token2, _ = self._register_second_user()
        headers2 = {'Authorization': f'Bearer {token2}', 'Content-Type': 'application/json'}
        resp = self.client.delete(f'/api/reports/{report_id}', headers=headers2)
        self.assertEqual(resp.status_code, 404)

    def test_delete_report_without_auth(self):
        """26. DELETE without auth -> 401."""
        resp = self.client.delete('/api/reports/1')
        self.assertEqual(resp.status_code, 401)


def run_report_tests():
    """Run all report tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestReportEndpoints)
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

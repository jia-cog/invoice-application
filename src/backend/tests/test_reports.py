#!/usr/bin/env python3
"""
Report Endpoints Tests

Comprehensive tests for all 4 report endpoints:
- GET /api/reports/
- POST /api/reports/generate
- GET /api/reports/dashboard
- DELETE /api/reports/<report_id>
"""

import sys
import os
import unittest
import json
from datetime import datetime, date, timedelta

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Invoice, InvoiceItem, Report


class TestReportEndpoints(unittest.TestCase):
    """Test cases for report endpoints."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.drop_all()
        db.create_all()

        self.client = self.app.test_client()

        # Register test user and obtain JWT token
        resp = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'company_name': 'Test Corp'
        })
        data = resp.get_json()
        self.token = data['access_token']
        self.user_id = data['user']['id']

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def auth_headers(self, token=None):
        """Return authorization headers with the given or default token."""
        return {
            'Authorization': f'Bearer {token or self.token}',
            'Content-Type': 'application/json'
        }

    def _create_invoice(self, **overrides):
        """POST a valid invoice payload and return the response."""
        payload = {
            'customer_name': overrides.get('customer_name', 'Acme Inc'),
            'customer_email': overrides.get('customer_email', 'acme@example.com'),
            'due_date': overrides.get('due_date', '2025-12-31'),
            'tax_rate': overrides.get('tax_rate', 0.0),
            'status': overrides.get('status', 'draft'),
            'items': overrides.get('items', [
                {'description': 'Widget', 'quantity': 2, 'unit_price': 50.0}
            ])
        }
        token = overrides.get('token', self.token)
        return self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self.auth_headers(token)
        )

    def _create_invoice_directly(self, user_id, issue_date, **overrides):
        """Create an Invoice (and items) directly via SQLAlchemy so we can
        control issue_date which the API does not accept."""
        import uuid
        inv = Invoice(
            invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
            user_id=user_id,
            customer_name=overrides.get('customer_name', 'Acme Inc'),
            customer_email=overrides.get('customer_email', 'acme@example.com'),
            customer_address=overrides.get('customer_address', ''),
            issue_date=issue_date,
            due_date=overrides.get('due_date', issue_date + timedelta(days=30)),
            status=overrides.get('status', 'draft'),
            tax_rate=overrides.get('tax_rate', 0.0),
            notes=overrides.get('notes', ''),
        )
        db.session.add(inv)
        db.session.flush()

        items = overrides.get('items', [
            {'description': 'Widget', 'quantity': 2, 'unit_price': 50.0}
        ])
        for item_data in items:
            item = InvoiceItem(
                invoice_id=inv.id,
                description=item_data['description'],
                quantity=float(item_data['quantity']),
                unit_price=float(item_data['unit_price']),
            )
            item.calculate_total()
            db.session.add(item)

        db.session.flush()
        inv.calculate_totals()
        db.session.commit()
        return inv

    def _generate_report(self, **overrides):
        """POST a valid report generation payload and return the response."""
        payload = {
            'report_type': overrides.get('report_type', 'monthly'),
            'start_date': overrides.get('start_date', '2025-01-01'),
            'end_date': overrides.get('end_date', '2025-12-31'),
        }
        token = overrides.get('token', self.token)
        return self.client.post(
            '/api/reports/generate',
            json=payload,
            headers=self.auth_headers(token)
        )

    def _register_user(self, username, email):
        """Register a second user and return (token, user_id)."""
        resp = self.client.post('/api/auth/register', json={
            'username': username,
            'email': email,
            'password': 'password123',
        })
        data = resp.get_json()
        return data['access_token'], data['user']['id']

    # ================================================================== #
    # 1. GET /api/reports/
    # ================================================================== #

    def test_get_reports_empty(self):
        """GET /api/reports/ returns 200 with empty list when no reports exist."""
        resp = self.client.get('/api/reports/', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['reports'], [])

    def test_get_reports_with_data(self):
        """GET /api/reports/ returns reports ordered by created_at desc."""
        # Generate two reports
        self._generate_report(report_type='monthly', start_date='2025-01-01', end_date='2025-06-30')
        self._generate_report(report_type='quarterly', start_date='2025-07-01', end_date='2025-12-31')

        resp = self.client.get('/api/reports/', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        reports = resp.get_json()['reports']
        self.assertEqual(len(reports), 2)
        # Most recently created should come first
        self.assertTrue(reports[0]['created_at'] >= reports[1]['created_at'])

    def test_get_reports_unauthorized(self):
        """GET /api/reports/ without token returns 401."""
        resp = self.client.get('/api/reports/')
        self.assertEqual(resp.status_code, 401)

    def test_get_reports_only_own(self):
        """Each user only sees their own reports."""
        token_b, _ = self._register_user('userB', 'b@example.com')

        # User A generates a report
        self._generate_report(token=self.token)
        # User B generates a report
        self._generate_report(token=token_b)

        # User A should see exactly 1 report
        resp_a = self.client.get('/api/reports/', headers=self.auth_headers(self.token))
        self.assertEqual(len(resp_a.get_json()['reports']), 1)

        # User B should see exactly 1 report
        resp_b = self.client.get('/api/reports/', headers=self.auth_headers(token_b))
        self.assertEqual(len(resp_b.get_json()['reports']), 1)

    # ================================================================== #
    # 2. POST /api/reports/generate
    # ================================================================== #

    def test_generate_report_success_no_invoices(self):
        """Generate report for a date range with no invoices; verify zeroed metrics."""
        resp = self._generate_report()
        self.assertEqual(resp.status_code, 201)
        report = resp.get_json()['report']
        summary = report['data']['summary']

        self.assertEqual(summary['total_invoices'], 0)
        self.assertEqual(summary['total_revenue'], 0)
        self.assertEqual(summary['paid_revenue'], 0)
        self.assertEqual(summary['pending_revenue'], 0)
        self.assertEqual(summary['overdue_revenue'], 0)
        self.assertEqual(summary['average_invoice_value'], 0)

    def test_generate_report_success_with_invoices(self):
        """Generate report with invoices of various statuses and verify all metrics."""
        # Create invoices with specific issue_dates inside the report range
        start = date(2025, 3, 1)

        self._create_invoice_directly(self.user_id, issue_date=date(2025, 3, 10),
                                      status='draft', customer_name='Alpha',
                                      items=[{'description': 'A', 'quantity': 1, 'unit_price': 100.0}])
        self._create_invoice_directly(self.user_id, issue_date=date(2025, 3, 15),
                                      status='sent', customer_name='Alpha',
                                      items=[{'description': 'B', 'quantity': 1, 'unit_price': 200.0}])
        self._create_invoice_directly(self.user_id, issue_date=date(2025, 4, 5),
                                      status='paid', customer_name='Beta',
                                      items=[{'description': 'C', 'quantity': 1, 'unit_price': 300.0}])
        self._create_invoice_directly(self.user_id, issue_date=date(2025, 4, 20),
                                      status='overdue', customer_name='Gamma',
                                      items=[{'description': 'D', 'quantity': 1, 'unit_price': 150.0}])

        resp = self._generate_report(start_date='2025-03-01', end_date='2025-04-30')
        self.assertEqual(resp.status_code, 201)

        report_data = resp.get_json()['report']['data']
        summary = report_data['summary']

        # total_invoices
        self.assertEqual(summary['total_invoices'], 4)
        # total_revenue = 100 + 200 + 300 + 150
        self.assertEqual(summary['total_revenue'], 750.0)
        # paid_revenue = 300
        self.assertEqual(summary['paid_revenue'], 300.0)
        # pending_revenue = 100 (draft) + 200 (sent)
        self.assertEqual(summary['pending_revenue'], 300.0)
        # overdue_revenue = 150
        self.assertEqual(summary['overdue_revenue'], 150.0)
        # average_invoice_value = 750 / 4
        self.assertEqual(summary['average_invoice_value'], 187.5)

        # status_breakdown
        sb = report_data['status_breakdown']
        self.assertEqual(sb['draft'], 1)
        self.assertEqual(sb['sent'], 1)
        self.assertEqual(sb['paid'], 1)
        self.assertEqual(sb['overdue'], 1)

        # monthly_data — should have entries for 2025-03 and 2025-04
        monthly = report_data['monthly_data']
        self.assertEqual(len(monthly), 2)
        months_present = {m['month'] for m in monthly}
        self.assertIn('March 2025', months_present)
        self.assertIn('April 2025', months_present)

        # top_customers sorted by revenue desc
        top = report_data['top_customers']
        # Alpha total = 300, Beta = 300, Gamma = 150
        self.assertEqual(top[0]['revenue'], 300.0)
        self.assertEqual(top[-1]['name'], 'Gamma')

        # date_range matches
        self.assertEqual(report_data['date_range']['start_date'], '2025-03-01')
        self.assertEqual(report_data['date_range']['end_date'], '2025-04-30')

    def test_generate_report_missing_report_type(self):
        """Omitting report_type returns 400."""
        resp = self.client.post('/api/reports/generate', json={
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
        }, headers=self.auth_headers())
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_missing_start_date(self):
        """Omitting start_date returns 400."""
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'end_date': '2025-12-31',
        }, headers=self.auth_headers())
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_missing_end_date(self):
        """Omitting end_date returns 400."""
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2025-01-01',
        }, headers=self.auth_headers())
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_unauthorized(self):
        """POST /api/reports/generate without token returns 401."""
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
        })
        self.assertEqual(resp.status_code, 401)

    def test_generate_report_filters_by_date_range(self):
        """Only invoices whose issue_date is within [start_date, end_date] are included."""
        # Inside range
        self._create_invoice_directly(self.user_id, issue_date=date(2025, 6, 15),
                                      items=[{'description': 'In', 'quantity': 1, 'unit_price': 500.0}])
        # Outside range (before)
        self._create_invoice_directly(self.user_id, issue_date=date(2025, 1, 1),
                                      items=[{'description': 'Before', 'quantity': 1, 'unit_price': 999.0}])
        # Outside range (after)
        self._create_invoice_directly(self.user_id, issue_date=date(2025, 12, 31),
                                      items=[{'description': 'After', 'quantity': 1, 'unit_price': 888.0}])

        resp = self._generate_report(start_date='2025-06-01', end_date='2025-06-30')
        self.assertEqual(resp.status_code, 201)
        summary = resp.get_json()['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 1)
        self.assertEqual(summary['total_revenue'], 500.0)

    def test_generate_report_filters_by_user(self):
        """User B's report should not include user A's invoices."""
        token_b, user_b_id = self._register_user('userB', 'b@example.com')

        # Create invoice for user A
        self._create_invoice_directly(self.user_id, issue_date=date(2025, 6, 15),
                                      items=[{'description': 'A item', 'quantity': 1, 'unit_price': 100.0}])

        # User B generates report for same date range
        resp = self._generate_report(token=token_b, start_date='2025-01-01', end_date='2025-12-31')
        self.assertEqual(resp.status_code, 201)
        summary = resp.get_json()['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 0)
        self.assertEqual(summary['total_revenue'], 0)

    def test_generate_report_all_types(self):
        """All report_type values (monthly, quarterly, yearly, custom) are accepted."""
        for rtype in ('monthly', 'quarterly', 'yearly', 'custom'):
            resp = self._generate_report(report_type=rtype)
            self.assertEqual(resp.status_code, 201, f"Failed for report_type={rtype}")
            self.assertEqual(resp.get_json()['report']['report_type'], rtype)

    # ================================================================== #
    # 3. GET /api/reports/dashboard
    # ================================================================== #

    def test_get_dashboard_empty(self):
        """Dashboard with no invoices returns zero metrics and empty recent_invoices."""
        resp = self.client.get('/api/reports/dashboard', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        overview = data['overview']
        self.assertEqual(overview['total_invoices'], 0)
        self.assertEqual(overview['total_revenue'], 0)
        self.assertEqual(overview['paid_count'], 0)
        self.assertEqual(overview['pending_count'], 0)
        self.assertEqual(overview['overdue_count'], 0)
        self.assertEqual(overview['monthly_revenue'], 0)
        self.assertEqual(data['recent_invoices'], [])

    def test_get_dashboard_with_invoices(self):
        """Dashboard correctly computes overview metrics and limits recent_invoices to 5."""
        today = date.today()
        last_month = (today.replace(day=1) - timedelta(days=1))

        # 3 invoices this month (will count toward monthly_revenue)
        self._create_invoice_directly(self.user_id, issue_date=today, status='paid',
                                      items=[{'description': 'X', 'quantity': 1, 'unit_price': 100.0}])
        self._create_invoice_directly(self.user_id, issue_date=today, status='draft',
                                      items=[{'description': 'Y', 'quantity': 1, 'unit_price': 200.0}])
        self._create_invoice_directly(self.user_id, issue_date=today, status='overdue',
                                      items=[{'description': 'Z', 'quantity': 1, 'unit_price': 50.0}])

        # 1 invoice last month (does NOT count toward monthly_revenue)
        self._create_invoice_directly(self.user_id, issue_date=last_month, status='sent',
                                      items=[{'description': 'W', 'quantity': 1, 'unit_price': 400.0}])

        # 3 more invoices this month to exceed the recent_invoices limit of 5
        for i in range(3):
            self._create_invoice_directly(self.user_id, issue_date=today, status='paid',
                                          items=[{'description': f'Extra{i}', 'quantity': 1, 'unit_price': 10.0}])

        resp = self.client.get('/api/reports/dashboard', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        overview = data['overview']

        # total_invoices = 7
        self.assertEqual(overview['total_invoices'], 7)
        # total_revenue = 100 + 200 + 50 + 400 + 30 = 780
        self.assertEqual(overview['total_revenue'], 780.0)
        # paid_count = 1 + 3 = 4
        self.assertEqual(overview['paid_count'], 4)
        # pending_count = draft(1) + sent(1) = 2
        self.assertEqual(overview['pending_count'], 2)
        # overdue_count = 1
        self.assertEqual(overview['overdue_count'], 1)
        # monthly_revenue = invoices with issue_date >= start of current month
        # = 100 + 200 + 50 + 30 = 380
        self.assertEqual(overview['monthly_revenue'], 380.0)
        # recent_invoices capped at 5
        self.assertLessEqual(len(data['recent_invoices']), 5)

    def test_get_dashboard_unauthorized(self):
        """GET /api/reports/dashboard without token returns 401."""
        resp = self.client.get('/api/reports/dashboard')
        self.assertEqual(resp.status_code, 401)

    def test_get_dashboard_only_own_data(self):
        """User B's dashboard should show zero metrics when only user A has invoices."""
        token_b, user_b_id = self._register_user('userB', 'b@example.com')

        # Create invoice for user A
        self._create_invoice_directly(self.user_id, issue_date=date.today(), status='paid',
                                      items=[{'description': 'X', 'quantity': 1, 'unit_price': 999.0}])

        resp = self.client.get('/api/reports/dashboard', headers=self.auth_headers(token_b))
        self.assertEqual(resp.status_code, 200)
        overview = resp.get_json()['overview']
        self.assertEqual(overview['total_invoices'], 0)
        self.assertEqual(overview['total_revenue'], 0)

    # ================================================================== #
    # 4. DELETE /api/reports/<report_id>
    # ================================================================== #

    def test_delete_report_success(self):
        """Delete a report, verify 200 and that it no longer appears in GET list."""
        gen_resp = self._generate_report()
        report_id = gen_resp.get_json()['report']['id']

        del_resp = self.client.delete(f'/api/reports/{report_id}', headers=self.auth_headers())
        self.assertEqual(del_resp.status_code, 200)
        self.assertIn('message', del_resp.get_json())

        # Verify it is gone
        list_resp = self.client.get('/api/reports/', headers=self.auth_headers())
        report_ids = [r['id'] for r in list_resp.get_json()['reports']]
        self.assertNotIn(report_id, report_ids)

    def test_delete_report_not_found(self):
        """Deleting a non-existent report returns 404."""
        resp = self.client.delete('/api/reports/99999', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 404)

    def test_delete_report_unauthorized(self):
        """DELETE without token returns 401."""
        resp = self.client.delete('/api/reports/1')
        self.assertEqual(resp.status_code, 401)

    def test_delete_report_belongs_to_other_user(self):
        """User B cannot delete user A's report (gets 404)."""
        token_b, _ = self._register_user('userB', 'b@example.com')

        gen_resp = self._generate_report(token=self.token)
        report_id = gen_resp.get_json()['report']['id']

        resp = self.client.delete(f'/api/reports/{report_id}', headers=self.auth_headers(token_b))
        self.assertEqual(resp.status_code, 404)


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

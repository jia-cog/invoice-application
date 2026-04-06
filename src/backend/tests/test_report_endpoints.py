#!/usr/bin/env python3
"""
Report Endpoint Tests

Tests for /api/reports/* endpoints: list, generate, dashboard, delete.
"""

import sys
import os
import unittest
from datetime import date

# Add the parent directory to the path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Invoice, InvoiceItem


class TestReportEndpoints(unittest.TestCase):
    """Test cases for report API endpoints."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['TESTING'] = True

        with self.app.app_context():
            db.drop_all()
            db.create_all()

        self.client = self.app.test_client()

        # Register a user and store the token
        reg_resp = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        })
        self.token = reg_resp.get_json()['access_token']
        self.auth_header = {'Authorization': f'Bearer {self.token}'}

    def tearDown(self):
        """Clean up after each test method."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_invoice(self, customer_name='Acme Corp', status='paid',
                        due_date='2026-06-30'):
        """Helper to create an invoice via the API."""
        return self.client.post('/api/invoices/', json={
            'customer_name': customer_name,
            'customer_email': f'{customer_name.lower().replace(" ", "")}@example.com',
            'due_date': due_date,
            'tax_rate': 10.0,
            'status': status,
            'items': [
                {'description': 'Service A', 'quantity': 2, 'unit_price': 100.00},
                {'description': 'Service B', 'quantity': 1, 'unit_price': 50.00}
            ]
        }, headers=self.auth_header)

    def _generate_report(self, report_type='monthly', start_date='2026-01-01',
                         end_date='2026-12-31'):
        """Helper to generate a report via the API."""
        return self.client.post('/api/reports/generate', json={
            'report_type': report_type,
            'start_date': start_date,
            'end_date': end_date
        }, headers=self.auth_header)

    # --- List Reports Tests ---

    def test_list_reports_empty(self):
        """Test listing reports when none exist."""
        resp = self.client.get('/api/reports/', headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['reports'], [])

    def test_list_reports_with_data(self):
        """Test listing reports after generating some."""
        self._create_invoice()
        self._generate_report(report_type='monthly')
        self._generate_report(report_type='quarterly')

        resp = self.client.get('/api/reports/', headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(data['reports']), 2)

    def test_list_reports_no_token(self):
        """Test listing reports fails without auth token."""
        resp = self.client.get('/api/reports/')
        self.assertEqual(resp.status_code, 401)

    # --- Generate Report Tests ---

    def test_generate_report_success(self):
        """Test successful report generation with invoices."""
        self._create_invoice(customer_name='Acme Corp', status='paid')
        self._create_invoice(customer_name='Globex Corp', status='draft')

        resp = self._generate_report()
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(data['message'], 'Report generated successfully')
        report = data['report']
        self.assertEqual(report['report_type'], 'monthly')
        self.assertIn('data', report)

        summary = report['data']['summary']
        self.assertEqual(summary['total_invoices'], 2)
        self.assertGreater(summary['total_revenue'], 0)

    def test_generate_report_empty_range(self):
        """Test report generation with no invoices in date range."""
        self._create_invoice()

        resp = self._generate_report(start_date='2020-01-01', end_date='2020-12-31')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        summary = data['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 0)
        self.assertEqual(summary['total_revenue'], 0)

    def test_generate_report_missing_type(self):
        """Test report generation fails without report_type."""
        resp = self.client.post('/api/reports/generate', json={
            'start_date': '2026-01-01',
            'end_date': '2026-12-31'
        }, headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('required', data['error'])

    def test_generate_report_missing_dates(self):
        """Test report generation fails without dates."""
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly'
        }, headers=self.auth_header)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('required', data['error'])

    def test_generate_report_no_token(self):
        """Test report generation fails without auth token."""
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31'
        })
        self.assertEqual(resp.status_code, 401)

    def test_generate_report_status_breakdown(self):
        """Test that status breakdown is correct in generated report."""
        self._create_invoice(customer_name='C1', status='paid')
        self._create_invoice(customer_name='C2', status='draft')
        self._create_invoice(customer_name='C3', status='overdue')

        resp = self._generate_report()
        data = resp.get_json()
        breakdown = data['report']['data']['status_breakdown']

        self.assertEqual(breakdown['paid'], 1)
        self.assertEqual(breakdown['draft'], 1)
        self.assertEqual(breakdown['overdue'], 1)
        self.assertEqual(breakdown['sent'], 0)

    def test_generate_report_top_customers(self):
        """Test that top customers are included in the report."""
        self._create_invoice(customer_name='Big Spender', status='paid')
        self._create_invoice(customer_name='Big Spender', status='paid')
        self._create_invoice(customer_name='Small Buyer', status='paid')

        resp = self._generate_report()
        data = resp.get_json()
        top_customers = data['report']['data']['top_customers']

        self.assertGreater(len(top_customers), 0)
        self.assertEqual(top_customers[0]['name'], 'Big Spender')
        self.assertEqual(top_customers[0]['count'], 2)

    def test_generate_report_different_types(self):
        """Test generating reports of different types."""
        self._create_invoice()

        for report_type in ['monthly', 'quarterly', 'yearly', 'custom']:
            resp = self._generate_report(report_type=report_type)
            data = resp.get_json()

            self.assertEqual(resp.status_code, 201)
            self.assertEqual(data['report']['report_type'], report_type)

    # --- Dashboard Tests ---

    def test_dashboard_empty(self):
        """Test dashboard with no invoices."""
        resp = self.client.get(
            '/api/reports/dashboard',
            headers=self.auth_header
        )
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertIn('overview', data)
        self.assertIn('recent_invoices', data)
        self.assertEqual(data['overview']['total_invoices'], 0)
        self.assertEqual(data['overview']['total_revenue'], 0)
        self.assertEqual(data['recent_invoices'], [])

    def test_dashboard_with_invoices(self):
        """Test dashboard returns correct metrics with invoices."""
        self._create_invoice(customer_name='C1', status='paid')
        self._create_invoice(customer_name='C2', status='draft')
        self._create_invoice(customer_name='C3', status='overdue')

        resp = self.client.get(
            '/api/reports/dashboard',
            headers=self.auth_header
        )
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        overview = data['overview']
        self.assertEqual(overview['total_invoices'], 3)
        self.assertGreater(overview['total_revenue'], 0)
        self.assertEqual(overview['paid_count'], 1)
        self.assertEqual(overview['pending_count'], 1)
        self.assertEqual(overview['overdue_count'], 1)

    def test_dashboard_recent_invoices_limit(self):
        """Test dashboard returns at most 5 recent invoices."""
        for i in range(7):
            self._create_invoice(customer_name=f'Customer {i}')

        resp = self.client.get(
            '/api/reports/dashboard',
            headers=self.auth_header
        )
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(data['recent_invoices']), 5)

    def test_dashboard_no_token(self):
        """Test dashboard fails without auth token."""
        resp = self.client.get('/api/reports/dashboard')
        self.assertEqual(resp.status_code, 401)

    # --- Delete Report Tests ---

    def test_delete_report_success(self):
        """Test successful report deletion."""
        self._create_invoice()
        gen_resp = self._generate_report()
        report_id = gen_resp.get_json()['report']['id']

        resp = self.client.delete(
            f'/api/reports/{report_id}',
            headers=self.auth_header
        )
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['message'], 'Report deleted successfully')

        # Confirm it's gone from the list
        list_resp = self.client.get('/api/reports/', headers=self.auth_header)
        self.assertEqual(len(list_resp.get_json()['reports']), 0)

    def test_delete_report_not_found(self):
        """Test deleting a nonexistent report returns 404."""
        resp = self.client.delete(
            '/api/reports/9999',
            headers=self.auth_header
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_report_no_token(self):
        """Test deleting a report fails without auth token."""
        resp = self.client.delete('/api/reports/1')
        self.assertEqual(resp.status_code, 401)

    def test_delete_report_other_user(self):
        """Test that a user cannot delete another user's report."""
        self._create_invoice()
        gen_resp = self._generate_report()
        report_id = gen_resp.get_json()['report']['id']

        # Register second user
        reg_resp = self.client.post('/api/auth/register', json={
            'username': 'otheruser',
            'email': 'other@example.com',
            'password': 'password456'
        })
        other_header = {
            'Authorization': f'Bearer {reg_resp.get_json()["access_token"]}'
        }

        resp = self.client.delete(
            f'/api/reports/{report_id}',
            headers=other_header
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == '__main__':
    unittest.main()

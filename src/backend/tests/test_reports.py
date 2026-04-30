#!/usr/bin/env python3
"""
Report endpoint tests.

Tests for GET /api/reports/, POST /api/reports/generate,
GET /api/reports/dashboard, and DELETE /api/reports/<id>.
"""

import sys
import os
import unittest
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base import BaseTestCase


class TestReportEndpoints(BaseTestCase):
    """Test cases for report endpoints."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _register_and_get_token(self, username='alice', email='alice@example.com'):
        resp = self.register_user(username, email, 'password123')
        return resp.get_json()['access_token']

    def _create_invoice(self, token, customer='Acme', status='draft', tax_rate=0):
        """Create an invoice with today's issue_date so it falls in the
        default report date range."""
        today = date.today().isoformat()
        return self.client.post('/api/invoices/', json={
            'customer_name': customer,
            'due_date': '2025-12-31',
            'status': status,
            'tax_rate': tax_rate,
            'items': [
                {'description': 'Widget', 'quantity': 2, 'unit_price': 50.0},
            ],
        }, headers=self.get_auth_header(token))

    def generate_sample_report(self, token):
        """POST /api/reports/generate with a wide date range."""
        return self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
        }, headers=self.get_auth_header(token))

    # ------------------------------------------------------------------
    # GET /api/reports/
    # ------------------------------------------------------------------

    def test_get_reports_empty(self):
        token = self._register_and_get_token()
        resp = self.client.get('/api/reports/',
                               headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['reports'], [])

    def test_get_reports_success(self):
        token = self._register_and_get_token()
        self.generate_sample_report(token)
        resp = self.client.get('/api/reports/',
                               headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(data['reports']), 1)

    def test_get_reports_no_token(self):
        resp = self.client.get('/api/reports/')
        self.assertEqual(resp.status_code, 401)

    # ------------------------------------------------------------------
    # POST /api/reports/generate
    # ------------------------------------------------------------------

    def test_generate_report_success(self):
        token = self._register_and_get_token()
        resp = self.generate_sample_report(token)
        data = resp.get_json()
        self.assertEqual(resp.status_code, 201)
        report = data['report']
        self.assertEqual(report['report_type'], 'monthly')
        self.assertIn('summary', report['data'])

    def test_generate_report_missing_fields(self):
        token = self._register_and_get_token()
        resp = self.client.post('/api/reports/generate', json={
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
        }, headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_missing_start_date(self):
        token = self._register_and_get_token()
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'end_date': '2025-12-31',
        }, headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_missing_end_date(self):
        token = self._register_and_get_token()
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2025-01-01',
        }, headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_no_token(self):
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
        })
        self.assertEqual(resp.status_code, 401)

    def test_generate_report_with_invoices(self):
        token = self._register_and_get_token()
        # Create invoices with different statuses
        self._create_invoice(token, status='paid')
        self._create_invoice(token, status='draft')
        self._create_invoice(token, status='paid')

        # Use a date range that covers today's issue_date
        today = date.today()
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': today.replace(day=1).isoformat(),
            'end_date': '2027-12-31',
        }, headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 201)
        summary = data['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 3)
        # Each invoice: subtotal=100, no tax → total=100; three invoices = 300
        self.assertAlmostEqual(summary['total_revenue'], 300.0)

    # ------------------------------------------------------------------
    # GET /api/reports/dashboard
    # ------------------------------------------------------------------

    def test_dashboard_empty(self):
        token = self._register_and_get_token()
        resp = self.client.get('/api/reports/dashboard',
                               headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['overview']['total_invoices'], 0)

    def test_dashboard_with_data(self):
        token = self._register_and_get_token()
        self._create_invoice(token, status='paid')
        self._create_invoice(token, status='draft')

        resp = self.client.get('/api/reports/dashboard',
                               headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        overview = data['overview']
        self.assertEqual(overview['total_invoices'], 2)
        self.assertTrue(len(data['recent_invoices']) > 0)

    def test_dashboard_no_token(self):
        resp = self.client.get('/api/reports/dashboard')
        self.assertEqual(resp.status_code, 401)

    # ------------------------------------------------------------------
    # DELETE /api/reports/<id>
    # ------------------------------------------------------------------

    def test_delete_report_success(self):
        token = self._register_and_get_token()
        report_id = self.generate_sample_report(token).get_json()['report']['id']
        resp = self.client.delete(f'/api/reports/{report_id}',
                                  headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 200)
        # Confirm it's gone
        resp2 = self.client.get('/api/reports/',
                                headers=self.get_auth_header(token))
        self.assertEqual(len(resp2.get_json()['reports']), 0)

    def test_delete_report_not_found(self):
        token = self._register_and_get_token()
        resp = self.client.delete('/api/reports/9999',
                                  headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 404)

    def test_delete_report_other_user(self):
        token_a = self._register_and_get_token('alice', 'alice@example.com')
        token_b = self._register_and_get_token('bob', 'bob@example.com')
        report_id = self.generate_sample_report(token_a).get_json()['report']['id']
        resp = self.client.delete(f'/api/reports/{report_id}',
                                  headers=self.get_auth_header(token_b))
        self.assertEqual(resp.status_code, 404)


if __name__ == '__main__':
    unittest.main()

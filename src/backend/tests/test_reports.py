"""
Tests for report routes: generate, list, dashboard, and delete.
"""

import unittest
from base import BaseTestCase


class TestGenerateReport(BaseTestCase):
    """POST /api/reports/generate"""

    def _generate(self, token, **overrides):
        payload = {
            'report_type': 'monthly',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
        }
        payload.update(overrides)
        return self.client.post('/api/reports/generate', json=payload,
                                headers=self.auth_header(token))

    def test_generate_report_empty_range(self):
        token = self.get_token()
        resp = self._generate(token)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(data['message'], 'Report generated successfully')
        report_data = data['report']['data']
        self.assertEqual(report_data['summary']['total_invoices'], 0)
        self.assertAlmostEqual(report_data['summary']['total_revenue'], 0.0)

    def test_generate_report_with_invoices(self):
        token = self.get_token()
        self.create_sample_invoice(token)
        self.create_sample_invoice(token, customer_name='Beta LLC',
                                   status='paid')

        resp = self._generate(token)
        data = resp.get_json()['report']['data']

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(data['summary']['total_invoices'], 2)
        self.assertGreater(data['summary']['total_revenue'], 0)
        self.assertIn('status_breakdown', data)
        self.assertIn('top_customers', data)

    def test_generate_report_missing_report_type(self):
        token = self.get_token()
        resp = self._generate(token, report_type=None)
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_missing_start_date(self):
        token = self.get_token()
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'end_date': '2026-12-31',
        }, headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_missing_end_date(self):
        token = self.get_token()
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2026-01-01',
        }, headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 400)

    def test_generate_report_no_auth(self):
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
        })
        self.assertEqual(resp.status_code, 401)

    def test_generate_report_isolation(self):
        """Reports only include the authenticated user's invoices."""
        token_a = self.get_token(username='alice', email='a@a.com')
        token_b = self.get_token(username='bob', email='b@b.com')

        self.create_sample_invoice(token_a)
        self.create_sample_invoice(token_b)

        resp_a = self._generate(token_a)
        resp_b = self._generate(token_b)

        self.assertEqual(
            resp_a.get_json()['report']['data']['summary']['total_invoices'], 1)
        self.assertEqual(
            resp_b.get_json()['report']['data']['summary']['total_invoices'], 1)

    def test_generate_report_status_breakdown(self):
        token = self.get_token()
        self.create_sample_invoice(token, status='paid')
        self.create_sample_invoice(token, status='draft')
        self.create_sample_invoice(token, status='overdue')

        resp = self._generate(token)
        breakdown = resp.get_json()['report']['data']['status_breakdown']

        self.assertEqual(breakdown['paid'], 1)
        self.assertEqual(breakdown['draft'], 1)
        self.assertEqual(breakdown['overdue'], 1)

    def test_generate_report_top_customers(self):
        token = self.get_token()
        for _ in range(3):
            self.create_sample_invoice(token, customer_name='Top Client')
        self.create_sample_invoice(token, customer_name='Small Client')

        resp = self._generate(token)
        top = resp.get_json()['report']['data']['top_customers']

        self.assertEqual(top[0]['name'], 'Top Client')
        self.assertEqual(top[0]['count'], 3)


class TestListReports(BaseTestCase):
    """GET /api/reports/"""

    def test_list_reports_empty(self):
        token = self.get_token()
        resp = self.client.get('/api/reports/',
                               headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()['reports']), 0)

    def test_list_reports_returns_own_only(self):
        token_a = self.get_token(username='alice', email='a@a.com')
        token_b = self.get_token(username='bob', email='b@b.com')

        self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
        }, headers=self.auth_header(token_a))

        resp_b = self.client.get('/api/reports/',
                                 headers=self.auth_header(token_b))
        self.assertEqual(len(resp_b.get_json()['reports']), 0)

    def test_list_reports_no_auth(self):
        resp = self.client.get('/api/reports/')
        self.assertEqual(resp.status_code, 401)


class TestDashboard(BaseTestCase):
    """GET /api/reports/dashboard"""

    def test_dashboard_empty(self):
        token = self.get_token()
        resp = self.client.get('/api/reports/dashboard',
                               headers=self.auth_header(token))
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['overview']['total_invoices'], 0)
        self.assertAlmostEqual(data['overview']['total_revenue'], 0.0)
        self.assertEqual(len(data['recent_invoices']), 0)

    def test_dashboard_with_invoices(self):
        token = self.get_token()
        self.create_sample_invoice(token, status='paid')
        self.create_sample_invoice(token, status='draft')

        resp = self.client.get('/api/reports/dashboard',
                               headers=self.auth_header(token))
        data = resp.get_json()

        self.assertEqual(data['overview']['total_invoices'], 2)
        self.assertEqual(data['overview']['paid_count'], 1)
        self.assertEqual(data['overview']['pending_count'], 1)

    def test_dashboard_recent_invoices_limit(self):
        token = self.get_token()
        for _ in range(7):
            self.create_sample_invoice(token)

        resp = self.client.get('/api/reports/dashboard',
                               headers=self.auth_header(token))
        self.assertLessEqual(len(resp.get_json()['recent_invoices']), 5)

    def test_dashboard_isolation(self):
        token_a = self.get_token(username='alice', email='a@a.com')
        token_b = self.get_token(username='bob', email='b@b.com')

        self.create_sample_invoice(token_a)

        resp = self.client.get('/api/reports/dashboard',
                               headers=self.auth_header(token_b))
        self.assertEqual(resp.get_json()['overview']['total_invoices'], 0)

    def test_dashboard_no_auth(self):
        resp = self.client.get('/api/reports/dashboard')
        self.assertEqual(resp.status_code, 401)


class TestDeleteReport(BaseTestCase):
    """DELETE /api/reports/<id>"""

    def _create_report(self, token):
        resp = self.client.post('/api/reports/generate', json={
            'report_type': 'monthly',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
        }, headers=self.auth_header(token))
        return resp.get_json()['report']['id']

    def test_delete_report_success(self):
        token = self.get_token()
        report_id = self._create_report(token)

        resp = self.client.delete(f'/api/reports/{report_id}',
                                  headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('deleted', resp.get_json()['message'].lower())

    def test_delete_report_not_found(self):
        token = self.get_token()
        resp = self.client.delete('/api/reports/9999',
                                  headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 404)

    def test_delete_report_owned_by_another_user(self):
        token_a = self.get_token(username='alice', email='a@a.com')
        token_b = self.get_token(username='bob', email='b@b.com')

        report_id = self._create_report(token_a)

        resp = self.client.delete(f'/api/reports/{report_id}',
                                  headers=self.auth_header(token_b))
        self.assertEqual(resp.status_code, 404)

    def test_delete_report_no_auth(self):
        resp = self.client.delete('/api/reports/1')
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()

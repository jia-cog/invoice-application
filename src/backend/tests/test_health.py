"""
Tests for the health check endpoint and application error handlers.
"""

import unittest
from base import BaseTestCase


class TestHealthCheck(BaseTestCase):
    """GET /api/health"""

    def test_health_check(self):
        resp = self.client.get('/api/health')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['status'], 'healthy')

    def test_health_check_no_auth_required(self):
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)


class TestErrorHandlers(BaseTestCase):
    """Application-level error handlers."""

    def test_404_unknown_endpoint(self):
        resp = self.client.get('/api/nonexistent')
        self.assertEqual(resp.status_code, 404)
        self.assertIn('error', resp.get_json())


if __name__ == '__main__':
    unittest.main()

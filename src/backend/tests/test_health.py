#!/usr/bin/env python3
"""
Health check endpoint test.

Tests GET /api/health.
"""

import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base import BaseTestCase


class TestHealthEndpoint(BaseTestCase):
    """Test the health check endpoint."""

    def test_health_check(self):
        resp = self.client.get('/api/health')
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['status'], 'healthy')


if __name__ == '__main__':
    unittest.main()

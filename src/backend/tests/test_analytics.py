#!/usr/bin/env python3
"""
Tests for endpoint usage analytics and invoice quality metrics.
"""

import sys
import os
import unittest
from datetime import datetime, date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from config import Config
from models import db, User, Invoice, InvoiceItem, RequestLog


class AnalyticsTestCase(unittest.TestCase):
    """Base test case with app and database setup."""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True

        db.init_app(self.app)
        JWTManager(self.app)

        from routes.reports import reports_bp
        self.app.register_blueprint(reports_bp, url_prefix='/api/reports')

        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()

        self.token = create_access_token(identity=str(self.user.id))
        self.auth_headers = {'Authorization': f'Bearer {self.token}'}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


class TestRequestLogModel(AnalyticsTestCase):
    """Tests for the RequestLog model."""

    def test_create_request_log(self):
        log = RequestLog(
            endpoint='/api/invoices/',
            method='GET',
            user_id=self.user.id,
            status_code=200
        )
        db.session.add(log)
        db.session.commit()

        saved = RequestLog.query.first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.endpoint, '/api/invoices/')
        self.assertEqual(saved.method, 'GET')
        self.assertEqual(saved.user_id, self.user.id)
        self.assertEqual(saved.status_code, 200)
        self.assertIsNotNone(saved.timestamp)

    def test_request_log_to_dict(self):
        log = RequestLog(
            endpoint='/api/health',
            method='GET',
            status_code=200
        )
        db.session.add(log)
        db.session.commit()

        d = log.to_dict()
        self.assertEqual(d['endpoint'], '/api/health')
        self.assertEqual(d['method'], 'GET')
        self.assertIsNone(d['user_id'])
        self.assertEqual(d['status_code'], 200)
        self.assertIn('timestamp', d)

    def test_request_log_nullable_user_id(self):
        log = RequestLog(
            endpoint='/api/auth/login',
            method='POST',
            status_code=200
        )
        db.session.add(log)
        db.session.commit()

        saved = RequestLog.query.first()
        self.assertIsNone(saved.user_id)

    def test_request_log_default_timestamp(self):
        before = datetime.utcnow()
        log = RequestLog(
            endpoint='/api/test',
            method='GET',
            status_code=200
        )
        db.session.add(log)
        db.session.commit()
        after = datetime.utcnow()

        self.assertGreaterEqual(log.timestamp, before)
        self.assertLessEqual(log.timestamp, after)


class TestUsageAnalyticsEndpoint(AnalyticsTestCase):
    """Tests for GET /api/reports/usage-analytics."""

    def _seed_logs(self):
        now = datetime.utcnow()
        logs = [
            RequestLog(endpoint='/api/invoices/', method='GET', user_id=self.user.id, status_code=200, timestamp=now),
            RequestLog(endpoint='/api/invoices/', method='GET', user_id=self.user.id, status_code=200, timestamp=now),
            RequestLog(endpoint='/api/invoices/', method='POST', user_id=self.user.id, status_code=201, timestamp=now),
            RequestLog(endpoint='/api/reports/dashboard', method='GET', user_id=self.user.id, status_code=200, timestamp=now),
            RequestLog(endpoint='/api/auth/login', method='POST', status_code=200, timestamp=now - timedelta(days=1)),
        ]
        db.session.add_all(logs)
        db.session.commit()

    def test_usage_analytics_requires_auth(self):
        response = self.client.get('/api/reports/usage-analytics')
        self.assertEqual(response.status_code, 401)

    def test_usage_analytics_empty(self):
        response = self.client.get(
            '/api/reports/usage-analytics',
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['total_requests'], 0)
        self.assertEqual(data['endpoint_stats'], [])
        self.assertEqual(data['daily_trends'], [])

    def test_usage_analytics_with_data(self):
        self._seed_logs()
        response = self.client.get(
            '/api/reports/usage-analytics',
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['total_requests'], 5)
        self.assertGreater(len(data['endpoint_stats']), 0)
        self.assertGreater(len(data['daily_trends']), 0)
        self.assertGreater(len(data['status_breakdown']), 0)

    def test_usage_analytics_endpoint_aggregation(self):
        self._seed_logs()
        response = self.client.get(
            '/api/reports/usage-analytics',
            headers=self.auth_headers
        )
        data = response.get_json()
        get_invoices = next(
            (s for s in data['endpoint_stats']
             if s['endpoint'] == '/api/invoices/' and s['method'] == 'GET'),
            None
        )
        self.assertIsNotNone(get_invoices)
        self.assertEqual(get_invoices['count'], 2)

    def test_usage_analytics_custom_days(self):
        old_log = RequestLog(
            endpoint='/api/old',
            method='GET',
            status_code=200,
            timestamp=datetime.utcnow() - timedelta(days=90)
        )
        db.session.add(old_log)
        db.session.commit()

        response = self.client.get(
            '/api/reports/usage-analytics?days=30',
            headers=self.auth_headers
        )
        data = response.get_json()
        self.assertEqual(data['total_requests'], 0)
        self.assertEqual(data['period_days'], 30)

    def test_usage_analytics_status_breakdown(self):
        self._seed_logs()
        response = self.client.get(
            '/api/reports/usage-analytics',
            headers=self.auth_headers
        )
        data = response.get_json()
        status_codes = {s['status_code'] for s in data['status_breakdown']}
        self.assertIn(200, status_codes)
        self.assertIn(201, status_codes)


class TestInvoiceQualityEndpoint(AnalyticsTestCase):
    """Tests for GET /api/reports/invoice-quality."""

    def _create_invoice(self, **kwargs):
        defaults = {
            'invoice_number': f'INV-{Invoice.query.count() + 1:04d}',
            'user_id': self.user.id,
            'customer_name': 'Test Customer',
            'customer_email': 'customer@test.com',
            'customer_address': '123 Test St',
            'issue_date': date.today(),
            'due_date': date.today() + timedelta(days=30),
            'status': 'draft',
            'subtotal': 100.0,
            'tax_rate': 10.0,
            'tax_amount': 10.0,
            'total_amount': 110.0,
            'notes': 'Test invoice',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        defaults.update(kwargs)
        inv = Invoice(**defaults)
        db.session.add(inv)
        db.session.commit()
        return inv

    def test_quality_metrics_requires_auth(self):
        response = self.client.get('/api/reports/invoice-quality')
        self.assertEqual(response.status_code, 401)

    def test_quality_metrics_empty(self):
        response = self.client.get(
            '/api/reports/invoice-quality',
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['total_invoices'], 0)
        self.assertEqual(data['overdue_rate'], 0)
        self.assertEqual(data['draft_stuck_rate'], 0)

    def test_quality_metrics_overdue_rate(self):
        self._create_invoice(status='paid')
        self._create_invoice(status='overdue')
        self._create_invoice(
            status='sent',
            due_date=date.today() - timedelta(days=10)
        )

        response = self.client.get(
            '/api/reports/invoice-quality',
            headers=self.auth_headers
        )
        data = response.get_json()
        self.assertEqual(data['total_invoices'], 3)
        self.assertGreater(data['overdue_rate'], 0)

    def test_quality_metrics_draft_stuck_rate(self):
        self._create_invoice(status='draft')
        self._create_invoice(status='draft')
        self._create_invoice(status='paid')
        self._create_invoice(status='sent')

        response = self.client.get(
            '/api/reports/invoice-quality',
            headers=self.auth_headers
        )
        data = response.get_json()
        self.assertEqual(data['draft_stuck_rate'], 50.0)

    def test_quality_metrics_missing_fields(self):
        self._create_invoice(customer_email=None, customer_address=None, notes=None)
        self._create_invoice()

        response = self.client.get(
            '/api/reports/invoice-quality',
            headers=self.auth_headers
        )
        data = response.get_json()
        self.assertEqual(data['missing_email_rate'], 50.0)
        self.assertEqual(data['missing_address_rate'], 50.0)
        self.assertEqual(data['missing_notes_rate'], 50.0)

    def test_quality_metrics_draft_to_paid_rate(self):
        self._create_invoice(status='paid')
        self._create_invoice(status='paid')
        self._create_invoice(status='draft')
        self._create_invoice(status='sent')

        response = self.client.get(
            '/api/reports/invoice-quality',
            headers=self.auth_headers
        )
        data = response.get_json()
        self.assertEqual(data['draft_to_paid_rate'], 50.0)

    def test_quality_metrics_daily_trends(self):
        self._create_invoice(created_at=datetime.utcnow())
        self._create_invoice(created_at=datetime.utcnow() - timedelta(days=1))

        response = self.client.get(
            '/api/reports/invoice-quality',
            headers=self.auth_headers
        )
        data = response.get_json()
        self.assertGreater(len(data['daily_trends']), 0)

    def test_quality_metrics_custom_days(self):
        self._create_invoice(created_at=datetime.utcnow() - timedelta(days=90))

        response = self.client.get(
            '/api/reports/invoice-quality?days=30',
            headers=self.auth_headers
        )
        data = response.get_json()
        self.assertEqual(data['total_invoices'], 0)
        self.assertEqual(data['period_days'], 30)

    def test_quality_metrics_only_user_invoices(self):
        other_user = User(username='other', email='other@example.com')
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.commit()

        self._create_invoice(user_id=other_user.id)
        self._create_invoice()

        response = self.client.get(
            '/api/reports/invoice-quality',
            headers=self.auth_headers
        )
        data = response.get_json()
        self.assertEqual(data['total_invoices'], 1)


if __name__ == '__main__':
    unittest.main()

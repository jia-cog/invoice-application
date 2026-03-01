#!/usr/bin/env python3
"""
Report Route Tests

Comprehensive tests for report generation, dashboard, and deletion endpoints.
"""

import sys
import os
import unittest
import json
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import Config
from models import db, User, Invoice, InvoiceItem, Report
from app import create_app


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'


class TestReportRoutes(unittest.TestCase):
    """Test cases for report routes."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id
        
        response = self.client.post('/api/auth/login',
            json={'username': 'testuser', 'password': 'password123'})
        data = json.loads(response.data)
        self.token = data['access_token']
        self.headers = {'Authorization': f'Bearer {self.token}'}
    
    def tearDown(self):
        """Clean up after each test method."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def _create_test_invoice(self, customer_name, total_amount, status='paid', issue_date=None):
        """Helper method to create a test invoice."""
        if issue_date is None:
            issue_date = date.today()
        
        with self.app.app_context():
            import uuid
            user = User.query.get(self.user_id)
            invoice = Invoice(
                invoice_number=f'INV-{customer_name}-{date.today().strftime("%Y%m%d")}-{str(uuid.uuid4())[:8]}',
                user_id=user.id,
                customer_name=customer_name,
                issue_date=issue_date,
                due_date=issue_date + timedelta(days=30),
                status=status,
                subtotal=total_amount,
                tax_rate=0.0,
                tax_amount=0.0,
                total_amount=total_amount
            )
            db.session.add(invoice)
            db.session.flush()
            
            item = InvoiceItem(
                invoice_id=invoice.id,
                description='Test Item',
                quantity=1.0,
                unit_price=total_amount,
                total=total_amount
            )
            db.session.add(item)
            db.session.commit()
            return invoice.id
    
    def test_generate_report_success(self):
        """Test successful report generation."""
        self._create_test_invoice('Customer 1', 1000.0, 'paid')
        self._create_test_invoice('Customer 2', 500.0, 'sent')
        
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        
        self.assertIn('message', data)
        self.assertIn('report', data)
        self.assertEqual(data['report']['report_type'], 'monthly')
        self.assertIn('data', data['report'])
        self.assertIn('summary', data['report']['data'])
    
    def test_generate_report_missing_report_type(self):
        """Test report generation with missing report_type."""
        report_data = {
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('report_type', data['error'].lower())
    
    def test_generate_report_missing_start_date(self):
        """Test report generation with missing start_date."""
        report_data = {
            'report_type': 'monthly',
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('start_date', data['error'].lower())
    
    def test_generate_report_missing_end_date(self):
        """Test report generation with missing end_date."""
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat()
        }
        
        response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('end_date', data['error'].lower())
    
    def test_generate_report_without_token(self):
        """Test report generation without authentication token."""
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post('/api/reports/generate', json=report_data)
        
        self.assertEqual(response.status_code, 401)
    
    def test_generate_report_with_invoices(self):
        """Test report generation with multiple invoices."""
        self._create_test_invoice('Customer 1', 1000.0, 'paid')
        self._create_test_invoice('Customer 2', 500.0, 'paid')
        self._create_test_invoice('Customer 3', 750.0, 'sent')
        self._create_test_invoice('Customer 4', 250.0, 'overdue')
        
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        
        summary = data['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 4)
        self.assertEqual(summary['total_revenue'], 2500.0)
        self.assertEqual(summary['paid_revenue'], 1500.0)
        self.assertEqual(summary['pending_revenue'], 750.0)
        self.assertEqual(summary['overdue_revenue'], 250.0)
    
    def test_generate_report_status_breakdown(self):
        """Test report status breakdown."""
        self._create_test_invoice('Customer 1', 100.0, 'draft')
        self._create_test_invoice('Customer 2', 200.0, 'sent')
        self._create_test_invoice('Customer 3', 300.0, 'paid')
        self._create_test_invoice('Customer 4', 400.0, 'paid')
        self._create_test_invoice('Customer 5', 500.0, 'overdue')
        
        report_data = {
            'report_type': 'custom',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        
        data = json.loads(response.data)
        status_breakdown = data['report']['data']['status_breakdown']
        
        self.assertEqual(status_breakdown['draft'], 1)
        self.assertEqual(status_breakdown['sent'], 1)
        self.assertEqual(status_breakdown['paid'], 2)
        self.assertEqual(status_breakdown['overdue'], 1)
    
    def test_generate_report_top_customers(self):
        """Test report top customers calculation."""
        self._create_test_invoice('Customer A', 1000.0, 'paid')
        self._create_test_invoice('Customer A', 500.0, 'paid')
        self._create_test_invoice('Customer B', 800.0, 'paid')
        self._create_test_invoice('Customer C', 300.0, 'paid')
        
        report_data = {
            'report_type': 'quarterly',
            'start_date': (date.today() - timedelta(days=90)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        
        data = json.loads(response.data)
        top_customers = data['report']['data']['top_customers']
        
        self.assertGreater(len(top_customers), 0)
        self.assertEqual(top_customers[0]['name'], 'Customer A')
        self.assertEqual(top_customers[0]['revenue'], 1500.0)
        self.assertEqual(top_customers[0]['count'], 2)
    
    def test_generate_report_empty_date_range(self):
        """Test report generation with no invoices in date range."""
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=365)).isoformat(),
            'end_date': (date.today() - timedelta(days=335)).isoformat()
        }
        
        response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        
        summary = data['report']['data']['summary']
        self.assertEqual(summary['total_invoices'], 0)
        self.assertEqual(summary['total_revenue'], 0.0)
    
    def test_generate_report_types(self):
        """Test different report types."""
        report_types = ['monthly', 'quarterly', 'yearly', 'custom']
        
        for report_type in report_types:
            report_data = {
                'report_type': report_type,
                'start_date': (date.today() - timedelta(days=30)).isoformat(),
                'end_date': date.today().isoformat()
            }
            
            response = self.client.post('/api/reports/generate',
                json=report_data,
                headers=self.headers)
            
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.data)
            self.assertEqual(data['report']['report_type'], report_type)
    
    def test_get_reports_empty(self):
        """Test getting reports when none exist."""
        response = self.client.get('/api/reports/', headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 0)
    
    def test_get_reports_success(self):
        """Test getting all reports for a user."""
        for i in range(2):
            report_data = {
                'report_type': 'monthly',
                'start_date': (date.today() - timedelta(days=30)).isoformat(),
                'end_date': date.today().isoformat()
            }
            self.client.post('/api/reports/generate',
                json=report_data,
                headers=self.headers)
        
        response = self.client.get('/api/reports/', headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 2)
    
    def test_get_reports_without_token(self):
        """Test getting reports without authentication token."""
        response = self.client.get('/api/reports/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_dashboard_data_success(self):
        """Test getting dashboard data."""
        self._create_test_invoice('Customer 1', 1000.0, 'paid')
        self._create_test_invoice('Customer 2', 500.0, 'sent')
        self._create_test_invoice('Customer 3', 250.0, 'overdue')
        
        response = self.client.get('/api/reports/dashboard',
            headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('overview', data)
        self.assertIn('recent_invoices', data)
        
        overview = data['overview']
        self.assertEqual(overview['total_invoices'], 3)
        self.assertEqual(overview['total_revenue'], 1750.0)
        self.assertEqual(overview['paid_count'], 1)
        self.assertEqual(overview['pending_count'], 1)
        self.assertEqual(overview['overdue_count'], 1)
    
    def test_get_dashboard_data_empty(self):
        """Test getting dashboard data with no invoices."""
        response = self.client.get('/api/reports/dashboard',
            headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        overview = data['overview']
        self.assertEqual(overview['total_invoices'], 0)
        self.assertEqual(overview['total_revenue'], 0.0)
        self.assertEqual(overview['paid_count'], 0)
        self.assertEqual(overview['pending_count'], 0)
        self.assertEqual(overview['overdue_count'], 0)
    
    def test_get_dashboard_recent_invoices(self):
        """Test dashboard recent invoices limit."""
        for i in range(10):
            self._create_test_invoice(f'Customer {i+1}', 100.0, 'paid')
        
        response = self.client.get('/api/reports/dashboard',
            headers=self.headers)
        
        data = json.loads(response.data)
        recent_invoices = data['recent_invoices']
        
        self.assertEqual(len(recent_invoices), 5)
    
    def test_get_dashboard_monthly_revenue(self):
        """Test dashboard monthly revenue calculation."""
        today = date.today()
        current_month_date = today
        last_month_date = today - timedelta(days=35)
        
        self._create_test_invoice('Customer 1', 1000.0, 'paid', current_month_date)
        self._create_test_invoice('Customer 2', 500.0, 'paid', current_month_date)
        self._create_test_invoice('Customer 3', 300.0, 'paid', last_month_date)
        
        response = self.client.get('/api/reports/dashboard',
            headers=self.headers)
        
        data = json.loads(response.data)
        overview = data['overview']
        
        self.assertEqual(overview['total_revenue'], 1800.0)
        self.assertEqual(overview['monthly_revenue'], 1500.0)
    
    def test_get_dashboard_without_token(self):
        """Test getting dashboard without authentication token."""
        response = self.client.get('/api/reports/dashboard')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_report_success(self):
        """Test successful report deletion."""
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        create_response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        create_data = json.loads(create_response.data)
        report_id = create_data['report']['id']
        
        response = self.client.delete(f'/api/reports/{report_id}',
            headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        
        get_response = self.client.get('/api/reports/', headers=self.headers)
        get_data = json.loads(get_response.data)
        self.assertEqual(len(get_data['reports']), 0)
    
    def test_delete_report_not_found(self):
        """Test deleting a non-existent report."""
        response = self.client.delete('/api/reports/99999',
            headers=self.headers)
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_delete_report_without_token(self):
        """Test deleting report without authentication token."""
        response = self.client.delete('/api/reports/1')
        
        self.assertEqual(response.status_code, 401)
    
    def test_user_isolation_reports(self):
        """Test that users can only access their own reports."""
        with self.app.app_context():
            user2 = User(username='testuser2', email='test2@example.com')
            user2.set_password('password123')
            db.session.add(user2)
            db.session.commit()
        
        response = self.client.post('/api/auth/login',
            json={'username': 'testuser2', 'password': 'password123'})
        data = json.loads(response.data)
        token2 = data['access_token']
        headers2 = {'Authorization': f'Bearer {token2}'}
        
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        create_response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        create_data = json.loads(create_response.data)
        report_id = create_data['report']['id']
        
        response = self.client.delete(f'/api/reports/{report_id}',
            headers=headers2)
        
        self.assertEqual(response.status_code, 404)
    
    def test_report_average_invoice_value(self):
        """Test report average invoice value calculation."""
        self._create_test_invoice('Customer 1', 100.0, 'paid')
        self._create_test_invoice('Customer 2', 200.0, 'paid')
        self._create_test_invoice('Customer 3', 300.0, 'paid')
        
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post('/api/reports/generate',
            json=report_data,
            headers=self.headers)
        
        data = json.loads(response.data)
        summary = data['report']['data']['summary']
        
        expected_average = 600.0 / 3
        self.assertAlmostEqual(summary['average_invoice_value'], expected_average, places=2)


def run_report_tests():
    """Run all report tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestReportRoutes)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_report_tests()
    if success:
        print("\n✅ All report tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some report tests failed!")
        sys.exit(1)

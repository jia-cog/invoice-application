#!/usr/bin/env python3
"""
Reports Endpoint Tests

Tests for the reports API endpoints including report generation,
retrieval, dashboard data, and deletion functionality.
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
from flask_jwt_extended import create_access_token


class TestReportsEndpoint(unittest.TestCase):
    """Test cases for reports API endpoints."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create all tables
        db.create_all()
        
        # Create a test user
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            company_name='Test Company'
        )
        self.test_user.set_password('testpassword123')
        db.session.add(self.test_user)
        db.session.commit()
        
        # Create access token for the test user
        self.access_token = create_access_token(identity=str(self.test_user.id))
        self.auth_headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _create_test_invoice(self, customer_name='Test Customer', status='paid', 
                             issue_date=None, total_amount=100.0):
        """Helper method to create a test invoice."""
        if issue_date is None:
            issue_date = date.today()
        
        invoice = Invoice(
            invoice_number=f'INV-{datetime.now().strftime("%Y%m%d")}-{os.urandom(4).hex()}',
            user_id=self.test_user.id,
            customer_name=customer_name,
            customer_email=f'{customer_name.lower().replace(" ", "")}@example.com',
            customer_address='123 Test St',
            issue_date=issue_date,
            due_date=issue_date + timedelta(days=30),
            status=status,
            subtotal=total_amount,
            tax_rate=10.0,
            tax_amount=total_amount * 0.1,
            total_amount=total_amount * 1.1
        )
        db.session.add(invoice)
        db.session.commit()
        return invoice

    # ==================== GET /api/reports/ Tests ====================
    
    def test_get_reports_empty(self):
        """Test getting reports when no reports exist."""
        response = self.client.get('/api/reports/', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 0)
    
    def test_get_reports_with_data(self):
        """Test getting reports when reports exist."""
        # Create a test report
        report = Report(
            user_id=self.test_user.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        report.set_data({'summary': {'total_invoices': 5}})
        db.session.add(report)
        db.session.commit()
        
        response = self.client.get('/api/reports/', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['report_type'], 'monthly')
    
    def test_get_reports_unauthorized(self):
        """Test getting reports without authentication."""
        response = self.client.get('/api/reports/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_reports_user_isolation(self):
        """Test that users can only see their own reports."""
        # Create another user
        other_user = User(
            username='otheruser',
            email='other@example.com',
            company_name='Other Company'
        )
        other_user.set_password('otherpassword123')
        db.session.add(other_user)
        db.session.commit()
        
        # Create a report for the other user
        other_report = Report(
            user_id=other_user.id,
            report_type='quarterly',
            start_date=date.today() - timedelta(days=90),
            end_date=date.today()
        )
        other_report.set_data({'summary': {'total_invoices': 10}})
        db.session.add(other_report)
        
        # Create a report for the test user
        test_report = Report(
            user_id=self.test_user.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        test_report.set_data({'summary': {'total_invoices': 5}})
        db.session.add(test_report)
        db.session.commit()
        
        response = self.client.get('/api/reports/', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['report_type'], 'monthly')

    # ==================== POST /api/reports/generate Tests ====================
    
    def test_generate_report_success(self):
        """Test successful report generation."""
        # Create some test invoices
        self._create_test_invoice(customer_name='Customer A', status='paid', total_amount=100.0)
        self._create_test_invoice(customer_name='Customer B', status='sent', total_amount=200.0)
        
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self.auth_headers,
            data=json.dumps(report_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Report generated successfully')
        self.assertIn('report', data)
        self.assertEqual(data['report']['report_type'], 'monthly')
    
    def test_generate_report_missing_report_type(self):
        """Test report generation with missing report_type."""
        report_data = {
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self.auth_headers,
            data=json.dumps(report_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_generate_report_missing_start_date(self):
        """Test report generation with missing start_date."""
        report_data = {
            'report_type': 'monthly',
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self.auth_headers,
            data=json.dumps(report_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_generate_report_missing_end_date(self):
        """Test report generation with missing end_date."""
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self.auth_headers,
            data=json.dumps(report_data)
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_generate_report_unauthorized(self):
        """Test report generation without authentication."""
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(report_data)
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_generate_report_with_no_invoices(self):
        """Test report generation when no invoices exist in date range."""
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self.auth_headers,
            data=json.dumps(report_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['report']['data']['summary']['total_invoices'], 0)
        self.assertEqual(data['report']['data']['summary']['total_revenue'], 0)
    
    def test_generate_report_calculates_metrics_correctly(self):
        """Test that report generation calculates metrics correctly."""
        # Create invoices with different statuses
        self._create_test_invoice(customer_name='Customer A', status='paid', total_amount=100.0)
        self._create_test_invoice(customer_name='Customer A', status='paid', total_amount=150.0)
        self._create_test_invoice(customer_name='Customer B', status='sent', total_amount=200.0)
        self._create_test_invoice(customer_name='Customer C', status='overdue', total_amount=50.0)
        self._create_test_invoice(customer_name='Customer D', status='draft', total_amount=75.0)
        
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self.auth_headers,
            data=json.dumps(report_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        report_data = data['report']['data']
        
        # Check summary
        self.assertEqual(report_data['summary']['total_invoices'], 5)
        
        # Check status breakdown
        self.assertEqual(report_data['status_breakdown']['paid'], 2)
        self.assertEqual(report_data['status_breakdown']['sent'], 1)
        self.assertEqual(report_data['status_breakdown']['overdue'], 1)
        self.assertEqual(report_data['status_breakdown']['draft'], 1)
    
    def test_generate_report_top_customers(self):
        """Test that top customers are calculated correctly."""
        # Create multiple invoices for different customers
        self._create_test_invoice(customer_name='Big Customer', status='paid', total_amount=1000.0)
        self._create_test_invoice(customer_name='Big Customer', status='paid', total_amount=500.0)
        self._create_test_invoice(customer_name='Small Customer', status='paid', total_amount=100.0)
        
        report_data = {
            'report_type': 'monthly',
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self.auth_headers,
            data=json.dumps(report_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        top_customers = data['report']['data']['top_customers']
        
        # Big Customer should be first (highest revenue)
        self.assertEqual(top_customers[0]['name'], 'Big Customer')
        self.assertEqual(top_customers[0]['count'], 2)
    
    def test_generate_report_different_types(self):
        """Test report generation with different report types."""
        report_types = ['monthly', 'quarterly', 'yearly', 'custom']
        
        for report_type in report_types:
            report_data = {
                'report_type': report_type,
                'start_date': (date.today() - timedelta(days=30)).isoformat(),
                'end_date': date.today().isoformat()
            }
            
            response = self.client.post(
                '/api/reports/generate',
                headers=self.auth_headers,
                data=json.dumps(report_data)
            )
            
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.data)
            self.assertEqual(data['report']['report_type'], report_type)

    # ==================== GET /api/reports/dashboard Tests ====================
    
    def test_get_dashboard_empty(self):
        """Test getting dashboard data when no invoices exist."""
        response = self.client.get('/api/reports/dashboard', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('overview', data)
        self.assertIn('recent_invoices', data)
        self.assertEqual(data['overview']['total_invoices'], 0)
        self.assertEqual(data['overview']['total_revenue'], 0)
    
    def test_get_dashboard_with_data(self):
        """Test getting dashboard data with invoices."""
        # Create test invoices
        self._create_test_invoice(customer_name='Customer A', status='paid', total_amount=100.0)
        self._create_test_invoice(customer_name='Customer B', status='sent', total_amount=200.0)
        self._create_test_invoice(customer_name='Customer C', status='overdue', total_amount=50.0)
        
        response = self.client.get('/api/reports/dashboard', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data['overview']['total_invoices'], 3)
        self.assertEqual(data['overview']['paid_count'], 1)
        self.assertEqual(data['overview']['pending_count'], 1)  # 'sent' is pending
        self.assertEqual(data['overview']['overdue_count'], 1)
    
    def test_get_dashboard_unauthorized(self):
        """Test getting dashboard data without authentication."""
        response = self.client.get('/api/reports/dashboard')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_dashboard_recent_invoices_limit(self):
        """Test that dashboard returns only the 5 most recent invoices."""
        # Create 7 invoices
        for i in range(7):
            self._create_test_invoice(
                customer_name=f'Customer {i}',
                status='paid',
                total_amount=100.0 * (i + 1)
            )
        
        response = self.client.get('/api/reports/dashboard', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Should only return 5 recent invoices
        self.assertEqual(len(data['recent_invoices']), 5)
    
    def test_get_dashboard_user_isolation(self):
        """Test that dashboard only shows data for the authenticated user."""
        # Create another user with invoices
        other_user = User(
            username='otheruser',
            email='other@example.com',
            company_name='Other Company'
        )
        other_user.set_password('otherpassword123')
        db.session.add(other_user)
        db.session.commit()
        
        # Create invoice for other user
        other_invoice = Invoice(
            invoice_number='INV-OTHER-001',
            user_id=other_user.id,
            customer_name='Other Customer',
            customer_email='other@customer.com',
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='paid',
            total_amount=5000.0
        )
        db.session.add(other_invoice)
        
        # Create invoice for test user
        self._create_test_invoice(customer_name='Test Customer', status='paid', total_amount=100.0)
        
        response = self.client.get('/api/reports/dashboard', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Should only show test user's data
        self.assertEqual(data['overview']['total_invoices'], 1)
        self.assertEqual(len(data['recent_invoices']), 1)

    # ==================== DELETE /api/reports/<report_id> Tests ====================
    
    def test_delete_report_success(self):
        """Test successful report deletion."""
        # Create a test report
        report = Report(
            user_id=self.test_user.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        report.set_data({'summary': {'total_invoices': 5}})
        db.session.add(report)
        db.session.commit()
        report_id = report.id
        
        response = self.client.delete(
            f'/api/reports/{report_id}',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Report deleted successfully')
        
        # Verify report is deleted
        deleted_report = Report.query.get(report_id)
        self.assertIsNone(deleted_report)
    
    def test_delete_report_not_found(self):
        """Test deleting a non-existent report."""
        response = self.client.delete(
            '/api/reports/99999',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Report not found')
    
    def test_delete_report_unauthorized(self):
        """Test deleting a report without authentication."""
        # Create a test report
        report = Report(
            user_id=self.test_user.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        report.set_data({'summary': {'total_invoices': 5}})
        db.session.add(report)
        db.session.commit()
        
        response = self.client.delete(f'/api/reports/{report.id}')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_report_other_user(self):
        """Test that users cannot delete other users' reports."""
        # Create another user
        other_user = User(
            username='otheruser',
            email='other@example.com',
            company_name='Other Company'
        )
        other_user.set_password('otherpassword123')
        db.session.add(other_user)
        db.session.commit()
        
        # Create a report for the other user
        other_report = Report(
            user_id=other_user.id,
            report_type='quarterly',
            start_date=date.today() - timedelta(days=90),
            end_date=date.today()
        )
        other_report.set_data({'summary': {'total_invoices': 10}})
        db.session.add(other_report)
        db.session.commit()
        
        # Try to delete other user's report
        response = self.client.delete(
            f'/api/reports/{other_report.id}',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Report not found')
        
        # Verify report still exists
        existing_report = Report.query.get(other_report.id)
        self.assertIsNotNone(existing_report)


def run_reports_tests():
    """Run all reports tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestReportsEndpoint)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run the tests
    success = run_reports_tests()
    if success:
        print("\n All reports tests passed!")
        sys.exit(0)
    else:
        print("\n Some reports tests failed!")
        sys.exit(1)

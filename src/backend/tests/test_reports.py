#!/usr/bin/env python3
"""
Reports API Tests

Comprehensive tests for the reports API endpoints including:
- GET /api/reports/ - Retrieve all reports for authenticated user
- POST /api/reports/generate - Generate new report with date range and analytics
- GET /api/reports/dashboard - Return dashboard metrics and recent invoices
- DELETE /api/reports/<int:report_id> - Delete a specific report
"""

import sys
import os
import unittest
from datetime import datetime, date, timedelta

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from config import Config
from models import db, User, Invoice, InvoiceItem, Report


class TestReportsAPI(unittest.TestCase):
    """Test cases for Reports API endpoints."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        
        # Initialize extensions
        db.init_app(self.app)
        self.jwt = JWTManager(self.app)
        
        # Register the reports blueprint
        from routes.reports import reports_bp
        self.app.register_blueprint(reports_bp, url_prefix='/api/reports')
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create all tables
        db.create_all()
        
        # Create test user
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            company_name='Test Company'
        )
        self.test_user.set_password('testpassword123')
        db.session.add(self.test_user)
        db.session.commit()
        
        # Create JWT token for authenticated requests
        self.access_token = create_access_token(identity=str(self.test_user.id))
        self.auth_headers = {'Authorization': f'Bearer {self.access_token}'}
        
        # Create test client
        self.client = self.app.test_client()
        
        # Create test invoices with various statuses
        self._create_test_invoices()
    
    def _create_test_invoices(self):
        """Create test invoices with various statuses for report testing."""
        today = date.today()
        
        # Invoice 1: Paid invoice from this month
        invoice1 = Invoice(
            invoice_number='INV-TEST-001',
            user_id=self.test_user.id,
            customer_name='Customer A',
            customer_email='customera@example.com',
            customer_address='123 Main St',
            issue_date=today - timedelta(days=5),
            due_date=today + timedelta(days=25),
            status='paid',
            subtotal=1000.00,
            tax_rate=10.0,
            tax_amount=100.00,
            total_amount=1100.00
        )
        
        # Invoice 2: Sent invoice from this month
        invoice2 = Invoice(
            invoice_number='INV-TEST-002',
            user_id=self.test_user.id,
            customer_name='Customer B',
            customer_email='customerb@example.com',
            customer_address='456 Oak Ave',
            issue_date=today - timedelta(days=10),
            due_date=today + timedelta(days=20),
            status='sent',
            subtotal=500.00,
            tax_rate=10.0,
            tax_amount=50.00,
            total_amount=550.00
        )
        
        # Invoice 3: Draft invoice
        invoice3 = Invoice(
            invoice_number='INV-TEST-003',
            user_id=self.test_user.id,
            customer_name='Customer A',
            customer_email='customera@example.com',
            customer_address='123 Main St',
            issue_date=today - timedelta(days=2),
            due_date=today + timedelta(days=28),
            status='draft',
            subtotal=750.00,
            tax_rate=10.0,
            tax_amount=75.00,
            total_amount=825.00
        )
        
        # Invoice 4: Overdue invoice
        invoice4 = Invoice(
            invoice_number='INV-TEST-004',
            user_id=self.test_user.id,
            customer_name='Customer C',
            customer_email='customerc@example.com',
            customer_address='789 Pine Rd',
            issue_date=today - timedelta(days=45),
            due_date=today - timedelta(days=15),
            status='overdue',
            subtotal=2000.00,
            tax_rate=10.0,
            tax_amount=200.00,
            total_amount=2200.00
        )
        
        db.session.add_all([invoice1, invoice2, invoice3, invoice4])
        db.session.commit()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    # ==================== GET /api/reports/ Tests ====================
    
    def test_get_reports_success_empty(self):
        """Test GET /api/reports/ returns empty list when no reports exist."""
        response = self.client.get('/api/reports/', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 0)
    
    def test_get_reports_success_with_reports(self):
        """Test GET /api/reports/ returns list of reports for authenticated user."""
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
        data = response.get_json()
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['report_type'], 'monthly')
    
    def test_get_reports_missing_auth(self):
        """Test GET /api/reports/ returns 401 without authentication."""
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
        
        # Create report for other user
        other_report = Report(
            user_id=other_user.id,
            report_type='quarterly',
            start_date=date.today() - timedelta(days=90),
            end_date=date.today()
        )
        other_report.set_data({'summary': {'total_invoices': 10}})
        db.session.add(other_report)
        
        # Create report for test user
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
        data = response.get_json()
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['report_type'], 'monthly')
    
    # ==================== POST /api/reports/generate Tests ====================
    
    def test_generate_report_success(self):
        """Test POST /api/reports/generate with valid data creates a report."""
        today = date.today()
        request_data = {
            'report_type': 'monthly',
            'start_date': (today - timedelta(days=60)).isoformat(),
            'end_date': today.isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            json=request_data,
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Report generated successfully')
        self.assertIn('report', data)
        self.assertEqual(data['report']['report_type'], 'monthly')
    
    def test_generate_report_validates_calculations(self):
        """Test that report generation calculates metrics correctly."""
        today = date.today()
        request_data = {
            'report_type': 'custom',
            'start_date': (today - timedelta(days=60)).isoformat(),
            'end_date': today.isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            json=request_data,
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        report_data = data['report']['data']
        
        # Verify summary structure
        self.assertIn('summary', report_data)
        summary = report_data['summary']
        self.assertIn('total_invoices', summary)
        self.assertIn('total_revenue', summary)
        self.assertIn('paid_revenue', summary)
        self.assertIn('pending_revenue', summary)
        self.assertIn('overdue_revenue', summary)
        self.assertIn('average_invoice_value', summary)
        
        # Verify status breakdown
        self.assertIn('status_breakdown', report_data)
        status = report_data['status_breakdown']
        self.assertIn('draft', status)
        self.assertIn('sent', status)
        self.assertIn('paid', status)
        self.assertIn('overdue', status)
        
        # Verify top customers
        self.assertIn('top_customers', report_data)
        
        # Verify date range
        self.assertIn('date_range', report_data)
    
    def test_generate_report_missing_report_type(self):
        """Test POST /api/reports/generate returns 400 when report_type is missing."""
        today = date.today()
        request_data = {
            'start_date': (today - timedelta(days=30)).isoformat(),
            'end_date': today.isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            json=request_data,
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_generate_report_missing_start_date(self):
        """Test POST /api/reports/generate returns 400 when start_date is missing."""
        today = date.today()
        request_data = {
            'report_type': 'monthly',
            'end_date': today.isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            json=request_data,
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_generate_report_missing_end_date(self):
        """Test POST /api/reports/generate returns 400 when end_date is missing."""
        today = date.today()
        request_data = {
            'report_type': 'monthly',
            'start_date': (today - timedelta(days=30)).isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            json=request_data,
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_generate_report_missing_all_required_fields(self):
        """Test POST /api/reports/generate returns 400 when all required fields are missing."""
        response = self.client.post(
            '/api/reports/generate',
            json={},
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_generate_report_missing_auth(self):
        """Test POST /api/reports/generate returns 401 without authentication."""
        today = date.today()
        request_data = {
            'report_type': 'monthly',
            'start_date': (today - timedelta(days=30)).isoformat(),
            'end_date': today.isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            json=request_data
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_generate_report_empty_date_range(self):
        """Test report generation with date range that has no invoices."""
        # Use a date range in the past with no invoices
        request_data = {
            'report_type': 'custom',
            'start_date': '2020-01-01',
            'end_date': '2020-01-31'
        }
        
        response = self.client.post(
            '/api/reports/generate',
            json=request_data,
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        report_data = data['report']['data']
        
        # Verify zero values for empty range
        self.assertEqual(report_data['summary']['total_invoices'], 0)
        self.assertEqual(report_data['summary']['total_revenue'], 0)
        self.assertEqual(report_data['summary']['average_invoice_value'], 0)
    
    def test_generate_report_different_report_types(self):
        """Test report generation with different report types."""
        today = date.today()
        report_types = ['monthly', 'quarterly', 'yearly', 'custom']
        
        for report_type in report_types:
            request_data = {
                'report_type': report_type,
                'start_date': (today - timedelta(days=30)).isoformat(),
                'end_date': today.isoformat()
            }
            
            response = self.client.post(
                '/api/reports/generate',
                json=request_data,
                headers=self.auth_headers
            )
            
            self.assertEqual(response.status_code, 201, f"Failed for report_type: {report_type}")
            data = response.get_json()
            self.assertEqual(data['report']['report_type'], report_type)
    
    # ==================== GET /api/reports/dashboard Tests ====================
    
    def test_get_dashboard_success(self):
        """Test GET /api/reports/dashboard returns dashboard metrics."""
        response = self.client.get('/api/reports/dashboard', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        # Verify overview structure
        self.assertIn('overview', data)
        overview = data['overview']
        self.assertIn('total_invoices', overview)
        self.assertIn('total_revenue', overview)
        self.assertIn('monthly_revenue', overview)
        self.assertIn('paid_count', overview)
        self.assertIn('pending_count', overview)
        self.assertIn('overdue_count', overview)
        
        # Verify recent invoices
        self.assertIn('recent_invoices', data)
        self.assertIsInstance(data['recent_invoices'], list)
    
    def test_get_dashboard_validates_metrics(self):
        """Test that dashboard metrics are calculated correctly."""
        response = self.client.get('/api/reports/dashboard', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        overview = data['overview']
        
        # We created 4 invoices in setUp
        self.assertEqual(overview['total_invoices'], 4)
        
        # Verify status counts (1 paid, 1 sent + 1 draft = 2 pending, 1 overdue)
        self.assertEqual(overview['paid_count'], 1)
        self.assertEqual(overview['pending_count'], 2)
        self.assertEqual(overview['overdue_count'], 1)
        
        # Verify total revenue (1100 + 550 + 825 + 2200 = 4675)
        self.assertEqual(overview['total_revenue'], 4675.00)
    
    def test_get_dashboard_recent_invoices_limit(self):
        """Test that dashboard returns at most 5 recent invoices."""
        # Create additional invoices to exceed 5
        for i in range(5, 10):
            invoice = Invoice(
                invoice_number=f'INV-TEST-00{i}',
                user_id=self.test_user.id,
                customer_name=f'Customer {i}',
                customer_email=f'customer{i}@example.com',
                issue_date=date.today() - timedelta(days=i),
                due_date=date.today() + timedelta(days=30-i),
                status='draft',
                subtotal=100.00,
                tax_rate=10.0,
                tax_amount=10.00,
                total_amount=110.00
            )
            db.session.add(invoice)
        db.session.commit()
        
        response = self.client.get('/api/reports/dashboard', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertLessEqual(len(data['recent_invoices']), 5)
    
    def test_get_dashboard_missing_auth(self):
        """Test GET /api/reports/dashboard returns 401 without authentication."""
        response = self.client.get('/api/reports/dashboard')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_dashboard_user_isolation(self):
        """Test that dashboard only shows data for authenticated user."""
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
            customer_email='othercustomer@example.com',
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='paid',
            subtotal=5000.00,
            tax_rate=10.0,
            tax_amount=500.00,
            total_amount=5500.00
        )
        db.session.add(other_invoice)
        db.session.commit()
        
        response = self.client.get('/api/reports/dashboard', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        # Should still only see test_user's 4 invoices
        self.assertEqual(data['overview']['total_invoices'], 4)
        self.assertEqual(data['overview']['total_revenue'], 4675.00)
    
    def test_get_dashboard_empty_invoices(self):
        """Test dashboard with no invoices returns zero metrics."""
        # Create a new user with no invoices
        new_user = User(
            username='newuser',
            email='new@example.com',
            company_name='New Company'
        )
        new_user.set_password('newpassword123')
        db.session.add(new_user)
        db.session.commit()
        
        new_token = create_access_token(identity=str(new_user.id))
        new_headers = {'Authorization': f'Bearer {new_token}'}
        
        response = self.client.get('/api/reports/dashboard', headers=new_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['overview']['total_invoices'], 0)
        self.assertEqual(data['overview']['total_revenue'], 0)
        self.assertEqual(data['overview']['monthly_revenue'], 0)
        self.assertEqual(len(data['recent_invoices']), 0)
    
    # ==================== DELETE /api/reports/<id> Tests ====================
    
    def test_delete_report_success(self):
        """Test DELETE /api/reports/<id> successfully deletes a report."""
        # Create a report to delete
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
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Report deleted successfully')
        
        # Verify report is deleted
        deleted_report = Report.query.get(report_id)
        self.assertIsNone(deleted_report)
    
    def test_delete_report_not_found(self):
        """Test DELETE /api/reports/<id> returns 404 for non-existent report."""
        response = self.client.delete(
            '/api/reports/99999',
            headers=self.auth_headers
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Report not found')
    
    def test_delete_report_missing_auth(self):
        """Test DELETE /api/reports/<id> returns 401 without authentication."""
        # Create a report
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
    
    def test_delete_report_user_isolation(self):
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
        
        # Create report for other user
        other_report = Report(
            user_id=other_user.id,
            report_type='quarterly',
            start_date=date.today() - timedelta(days=90),
            end_date=date.today()
        )
        other_report.set_data({'summary': {'total_invoices': 10}})
        db.session.add(other_report)
        db.session.commit()
        other_report_id = other_report.id
        
        # Try to delete other user's report with test_user's token
        response = self.client.delete(
            f'/api/reports/{other_report_id}',
            headers=self.auth_headers
        )
        
        # Should return 404 (not found for this user)
        self.assertEqual(response.status_code, 404)
        
        # Verify report still exists
        existing_report = Report.query.get(other_report_id)
        self.assertIsNotNone(existing_report)


def run_reports_tests():
    """Run all reports tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestReportsAPI)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run the tests
    success = run_reports_tests()
    if success:
        print("\nAll Reports API tests passed!")
        sys.exit(0)
    else:
        print("\nSome Reports API tests failed!")
        sys.exit(1)

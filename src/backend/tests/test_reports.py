#!/usr/bin/env python3
"""
Reports API Tests

Comprehensive test coverage for all reports API endpoints including:
- GET /api/reports/ - Retrieve all reports for authenticated user
- POST /api/reports/generate - Generate new report with date range and analytics
- GET /api/reports/dashboard - Return dashboard metrics and recent invoices
- DELETE /api/reports/<int:report_id> - Delete a specific report
"""

import sys
import os
import unittest
import json
from datetime import datetime, date, timedelta

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from config import Config
from models import db, User, Invoice, InvoiceItem, Report


class TestConfig(Config):
    """Test configuration with in-memory SQLite database."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True


class TestReportsAPI(unittest.TestCase):
    """Test cases for Reports API endpoints."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create Flask app with test configuration
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        
        # Initialize extensions
        db.init_app(self.app)
        self.jwt = JWTManager(self.app)
        
        # Register the reports blueprint
        from routes.reports import reports_bp
        self.app.register_blueprint(reports_bp, url_prefix='/api/reports')
        
        # Create app context and test client
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Create database tables
        db.create_all()
        
        # Create test users
        self.user1 = User(
            username='testuser1',
            email='testuser1@example.com',
            company_name='Test Company 1'
        )
        self.user1.set_password('password123')
        
        self.user2 = User(
            username='testuser2',
            email='testuser2@example.com',
            company_name='Test Company 2'
        )
        self.user2.set_password('password456')
        
        db.session.add(self.user1)
        db.session.add(self.user2)
        db.session.commit()
        
        # Generate JWT tokens for both users
        self.token1 = create_access_token(identity=str(self.user1.id))
        self.token2 = create_access_token(identity=str(self.user2.id))
        
        # Create test invoices for user1 with various statuses
        self._create_test_invoices()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _create_test_invoices(self):
        """Create test invoices with various statuses and dates."""
        today = date.today()
        
        # Invoice 1: Paid invoice from current month
        invoice1 = Invoice(
            invoice_number='INV-001',
            user_id=self.user1.id,
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
        
        # Invoice 2: Sent invoice from current month
        invoice2 = Invoice(
            invoice_number='INV-002',
            user_id=self.user1.id,
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
            invoice_number='INV-003',
            user_id=self.user1.id,
            customer_name='Customer A',
            customer_email='customera@example.com',
            customer_address='123 Main St',
            issue_date=today - timedelta(days=3),
            due_date=today + timedelta(days=27),
            status='draft',
            subtotal=750.00,
            tax_rate=10.0,
            tax_amount=75.00,
            total_amount=825.00
        )
        
        # Invoice 4: Overdue invoice
        invoice4 = Invoice(
            invoice_number='INV-004',
            user_id=self.user1.id,
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
        
        # Invoice 5: Another paid invoice for Customer A (for top customers test)
        invoice5 = Invoice(
            invoice_number='INV-005',
            user_id=self.user1.id,
            customer_name='Customer A',
            customer_email='customera@example.com',
            customer_address='123 Main St',
            issue_date=today - timedelta(days=15),
            due_date=today + timedelta(days=15),
            status='paid',
            subtotal=1500.00,
            tax_rate=10.0,
            tax_amount=150.00,
            total_amount=1650.00
        )
        
        # Invoice for user2 (for isolation tests)
        invoice_user2 = Invoice(
            invoice_number='INV-USER2-001',
            user_id=self.user2.id,
            customer_name='User2 Customer',
            customer_email='user2customer@example.com',
            customer_address='999 Other St',
            issue_date=today - timedelta(days=5),
            due_date=today + timedelta(days=25),
            status='paid',
            subtotal=3000.00,
            tax_rate=10.0,
            tax_amount=300.00,
            total_amount=3300.00
        )
        
        db.session.add_all([invoice1, invoice2, invoice3, invoice4, invoice5, invoice_user2])
        db.session.commit()
        
        self.invoices = [invoice1, invoice2, invoice3, invoice4, invoice5]
        self.user2_invoice = invoice_user2
    
    def _get_auth_headers(self, token):
        """Return authorization headers with the given token."""
        return {'Authorization': f'Bearer {token}'}
    
    # ==================== GET /api/reports/ Tests ====================
    
    def test_get_reports_success_empty(self):
        """Test GET /api/reports/ returns empty list when no reports exist."""
        response = self.client.get(
            '/api/reports/',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 0)
    
    def test_get_reports_success_with_reports(self):
        """Test GET /api/reports/ returns existing reports for authenticated user."""
        # First create a report
        report = Report(
            user_id=self.user1.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        report.set_data({'summary': {'total_invoices': 5}})
        db.session.add(report)
        db.session.commit()
        
        response = self.client.get(
            '/api/reports/',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['report_type'], 'monthly')
    
    def test_get_reports_missing_auth(self):
        """Test GET /api/reports/ returns 401 without authentication."""
        response = self.client.get('/api/reports/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_reports_invalid_token(self):
        """Test GET /api/reports/ returns 422 with invalid/malformed token."""
        response = self.client.get(
            '/api/reports/',
            headers={'Authorization': 'Bearer invalid.token.here'}
        )
        
        # Flask-JWT-Extended returns 422 (Unprocessable Entity) for malformed tokens
        self.assertEqual(response.status_code, 422)
    
    def test_get_reports_user_isolation(self):
        """Test that users only see their own reports."""
        # Create reports for both users
        report1 = Report(
            user_id=self.user1.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        report1.set_data({'user': 'user1'})
        
        report2 = Report(
            user_id=self.user2.id,
            report_type='quarterly',
            start_date=date.today() - timedelta(days=90),
            end_date=date.today()
        )
        report2.set_data({'user': 'user2'})
        
        db.session.add_all([report1, report2])
        db.session.commit()
        
        # User1 should only see their report
        response = self.client.get(
            '/api/reports/',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['report_type'], 'monthly')
        
        # User2 should only see their report
        response = self.client.get(
            '/api/reports/',
            headers=self._get_auth_headers(self.token2)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['report_type'], 'quarterly')
    
    # ==================== POST /api/reports/generate Tests ====================
    
    def test_generate_report_success(self):
        """Test POST /api/reports/generate creates report with valid data."""
        today = date.today()
        request_data = {
            'report_type': 'monthly',
            'start_date': (today - timedelta(days=60)).isoformat(),
            'end_date': today.isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Report generated successfully')
        self.assertIn('report', data)
        self.assertEqual(data['report']['report_type'], 'monthly')
    
    def test_generate_report_calculations_accuracy(self):
        """Test that report generation calculates metrics correctly."""
        today = date.today()
        request_data = {
            'report_type': 'custom',
            'start_date': (today - timedelta(days=60)).isoformat(),
            'end_date': today.isoformat()
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
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
        
        # Verify status breakdown structure
        self.assertIn('status_breakdown', report_data)
        status_breakdown = report_data['status_breakdown']
        self.assertIn('draft', status_breakdown)
        self.assertIn('sent', status_breakdown)
        self.assertIn('paid', status_breakdown)
        self.assertIn('overdue', status_breakdown)
        
        # Verify top customers structure
        self.assertIn('top_customers', report_data)
        
        # Verify date range structure
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
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
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
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
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
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_generate_report_missing_all_required_fields(self):
        """Test POST /api/reports/generate returns 400 when all required fields are missing."""
        response = self.client.post(
            '/api/reports/generate',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('report_type', data['error'])
        self.assertIn('start_date', data['error'])
        self.assertIn('end_date', data['error'])
    
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
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_generate_report_empty_date_range(self):
        """Test report generation with date range containing no invoices."""
        # Use a date range in the far past with no invoices
        request_data = {
            'report_type': 'custom',
            'start_date': '2020-01-01',
            'end_date': '2020-01-31'
        }
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self._get_auth_headers(self.token1),
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        report_data = data['report']['data']
        
        # Verify zero values for empty date range
        self.assertEqual(report_data['summary']['total_invoices'], 0)
        self.assertEqual(report_data['summary']['total_revenue'], 0)
        self.assertEqual(report_data['summary']['average_invoice_value'], 0)
    
    def test_generate_report_different_types(self):
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
                headers=self._get_auth_headers(self.token1),
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 201, f"Failed for report_type: {report_type}")
            data = json.loads(response.data)
            self.assertEqual(data['report']['report_type'], report_type)
    
    def test_generate_report_user_isolation(self):
        """Test that generated reports only include user's own invoices."""
        today = date.today()
        request_data = {
            'report_type': 'monthly',
            'start_date': (today - timedelta(days=60)).isoformat(),
            'end_date': today.isoformat()
        }
        
        # Generate report for user2
        response = self.client.post(
            '/api/reports/generate',
            headers=self._get_auth_headers(self.token2),
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        report_data = data['report']['data']
        
        # User2 should only see their own invoice (1 invoice, $3300 total)
        self.assertEqual(report_data['summary']['total_invoices'], 1)
        self.assertEqual(report_data['summary']['total_revenue'], 3300.00)
    
    # ==================== GET /api/reports/dashboard Tests ====================
    
    def test_dashboard_success(self):
        """Test GET /api/reports/dashboard returns dashboard data."""
        response = self.client.get(
            '/api/reports/dashboard',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify overview structure
        self.assertIn('overview', data)
        overview = data['overview']
        self.assertIn('total_invoices', overview)
        self.assertIn('total_revenue', overview)
        self.assertIn('monthly_revenue', overview)
        self.assertIn('paid_count', overview)
        self.assertIn('pending_count', overview)
        self.assertIn('overdue_count', overview)
        
        # Verify recent invoices structure
        self.assertIn('recent_invoices', data)
        self.assertIsInstance(data['recent_invoices'], list)
    
    def test_dashboard_metrics_accuracy(self):
        """Test that dashboard metrics are calculated correctly."""
        response = self.client.get(
            '/api/reports/dashboard',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        overview = data['overview']
        
        # User1 has 5 invoices total
        self.assertEqual(overview['total_invoices'], 5)
        
        # Total revenue: 1100 + 550 + 825 + 2200 + 1650 = 6325
        self.assertEqual(overview['total_revenue'], 6325.00)
        
        # Status counts: 2 paid, 2 pending (draft + sent), 1 overdue
        self.assertEqual(overview['paid_count'], 2)
        self.assertEqual(overview['pending_count'], 2)  # draft + sent
        self.assertEqual(overview['overdue_count'], 1)
    
    def test_dashboard_recent_invoices_limit(self):
        """Test that dashboard returns at most 5 recent invoices."""
        response = self.client.get(
            '/api/reports/dashboard',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Should return at most 5 recent invoices
        self.assertLessEqual(len(data['recent_invoices']), 5)
    
    def test_dashboard_missing_auth(self):
        """Test GET /api/reports/dashboard returns 401 without authentication."""
        response = self.client.get('/api/reports/dashboard')
        
        self.assertEqual(response.status_code, 401)
    
    def test_dashboard_invalid_token(self):
        """Test GET /api/reports/dashboard returns 422 with invalid/malformed token."""
        response = self.client.get(
            '/api/reports/dashboard',
            headers={'Authorization': 'Bearer invalid.token.here'}
        )
        
        # Flask-JWT-Extended returns 422 (Unprocessable Entity) for malformed tokens
        self.assertEqual(response.status_code, 422)
    
    def test_dashboard_user_isolation(self):
        """Test that dashboard only shows user's own data."""
        # Get dashboard for user2
        response = self.client.get(
            '/api/reports/dashboard',
            headers=self._get_auth_headers(self.token2)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        overview = data['overview']
        
        # User2 has only 1 invoice
        self.assertEqual(overview['total_invoices'], 1)
        self.assertEqual(overview['total_revenue'], 3300.00)
        self.assertEqual(overview['paid_count'], 1)
        self.assertEqual(overview['pending_count'], 0)
        self.assertEqual(overview['overdue_count'], 0)
    
    def test_dashboard_empty_user(self):
        """Test dashboard for user with no invoices."""
        # Create a new user with no invoices
        user3 = User(
            username='testuser3',
            email='testuser3@example.com',
            company_name='Test Company 3'
        )
        user3.set_password('password789')
        db.session.add(user3)
        db.session.commit()
        
        token3 = create_access_token(identity=str(user3.id))
        
        response = self.client.get(
            '/api/reports/dashboard',
            headers=self._get_auth_headers(token3)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        overview = data['overview']
        
        self.assertEqual(overview['total_invoices'], 0)
        self.assertEqual(overview['total_revenue'], 0)
        self.assertEqual(overview['monthly_revenue'], 0)
        self.assertEqual(overview['paid_count'], 0)
        self.assertEqual(overview['pending_count'], 0)
        self.assertEqual(overview['overdue_count'], 0)
        self.assertEqual(len(data['recent_invoices']), 0)
    
    # ==================== DELETE /api/reports/<id> Tests ====================
    
    def test_delete_report_success(self):
        """Test DELETE /api/reports/<id> successfully deletes a report."""
        # First create a report
        report = Report(
            user_id=self.user1.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        report.set_data({'summary': {'total_invoices': 5}})
        db.session.add(report)
        db.session.commit()
        report_id = report.id
        
        # Delete the report
        response = self.client.delete(
            f'/api/reports/{report_id}',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Report deleted successfully')
        
        # Verify report is actually deleted
        deleted_report = Report.query.get(report_id)
        self.assertIsNone(deleted_report)
    
    def test_delete_report_not_found(self):
        """Test DELETE /api/reports/<id> returns 404 for non-existent report."""
        response = self.client.delete(
            '/api/reports/99999',
            headers=self._get_auth_headers(self.token1)
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Report not found')
    
    def test_delete_report_missing_auth(self):
        """Test DELETE /api/reports/<id> returns 401 without authentication."""
        # First create a report
        report = Report(
            user_id=self.user1.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        report.set_data({'summary': {'total_invoices': 5}})
        db.session.add(report)
        db.session.commit()
        
        response = self.client.delete(f'/api/reports/{report.id}')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_report_invalid_token(self):
        """Test DELETE /api/reports/<id> returns 422 with invalid/malformed token."""
        # First create a report
        report = Report(
            user_id=self.user1.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        report.set_data({'summary': {'total_invoices': 5}})
        db.session.add(report)
        db.session.commit()
        
        response = self.client.delete(
            f'/api/reports/{report.id}',
            headers={'Authorization': 'Bearer invalid.token.here'}
        )
        
        # Flask-JWT-Extended returns 422 (Unprocessable Entity) for malformed tokens
        self.assertEqual(response.status_code, 422)
    
    def test_delete_report_user_isolation(self):
        """Test that users cannot delete other users' reports."""
        # Create a report for user1
        report = Report(
            user_id=self.user1.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        report.set_data({'summary': {'total_invoices': 5}})
        db.session.add(report)
        db.session.commit()
        report_id = report.id
        
        # Try to delete with user2's token
        response = self.client.delete(
            f'/api/reports/{report_id}',
            headers=self._get_auth_headers(self.token2)
        )
        
        # Should return 404 because user2 doesn't own this report
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Report not found')
        
        # Verify report still exists
        existing_report = Report.query.get(report_id)
        self.assertIsNotNone(existing_report)
    
    def test_delete_multiple_reports(self):
        """Test deleting multiple reports sequentially."""
        # Create multiple reports
        reports = []
        for i in range(3):
            report = Report(
                user_id=self.user1.id,
                report_type='monthly',
                start_date=date.today() - timedelta(days=30 * (i + 1)),
                end_date=date.today() - timedelta(days=30 * i)
            )
            report.set_data({'index': i})
            db.session.add(report)
            reports.append(report)
        db.session.commit()
        
        # Delete each report
        for report in reports:
            response = self.client.delete(
                f'/api/reports/{report.id}',
                headers=self._get_auth_headers(self.token1)
            )
            self.assertEqual(response.status_code, 200)
        
        # Verify all reports are deleted
        remaining_reports = Report.query.filter_by(user_id=self.user1.id).all()
        self.assertEqual(len(remaining_reports), 0)


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

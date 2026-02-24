#!/usr/bin/env python3
"""
Reports Endpoint Tests

Tests for report generation, retrieval, dashboard data, and deletion functionality.
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


class TestConfig(Config):
    """Test configuration with in-memory database."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True


class TestReportsEndpoint(unittest.TestCase):
    """Test cases for reports endpoint functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        
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
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        db.session.commit()
        
        # Create access token for test user
        self.access_token = create_access_token(identity=str(self.test_user.id))
        
        # Create test client
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def get_auth_headers(self):
        """Return authorization headers with JWT token."""
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def create_test_invoice(self, customer_name='Test Customer', status='paid', 
                            total_amount=100.0, issue_date=None):
        """Helper method to create a test invoice."""
        if issue_date is None:
            issue_date = date.today()
        
        invoice = Invoice(
            invoice_number=f'INV-{datetime.now().strftime("%Y%m%d")}-{os.urandom(4).hex()}',
            user_id=self.test_user.id,
            customer_name=customer_name,
            customer_email=f'{customer_name.lower().replace(" ", "")}@example.com',
            issue_date=issue_date,
            due_date=issue_date + timedelta(days=30),
            status=status,
            subtotal=total_amount,
            tax_rate=0,
            tax_amount=0,
            total_amount=total_amount
        )
        db.session.add(invoice)
        db.session.commit()
        return invoice

    # ==================== GET /api/reports/ Tests ====================
    
    def test_get_reports_empty_list(self):
        """Test getting reports when no reports exist."""
        response = self.client.get(
            '/api/reports/',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
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
        
        response = self.client.get(
            '/api/reports/',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['report_type'], 'monthly')
    
    def test_get_reports_unauthorized(self):
        """Test getting reports without authentication."""
        response = self.client.get('/api/reports/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_reports_only_returns_user_reports(self):
        """Test that users can only see their own reports."""
        # Create another user
        other_user = User(
            username='otheruser',
            email='other@example.com',
            company_name='Other Company'
        )
        other_user.set_password('otherpassword')
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
        
        response = self.client.get(
            '/api/reports/',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['report_type'], 'monthly')

    # ==================== POST /api/reports/generate Tests ====================
    
    def test_generate_report_success(self):
        """Test successful report generation."""
        # Create test invoices
        self.create_test_invoice(customer_name='Customer A', status='paid', total_amount=100.0)
        self.create_test_invoice(customer_name='Customer B', status='sent', total_amount=200.0)
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self.get_auth_headers(),
            json={
                'report_type': 'monthly',
                'start_date': (date.today() - timedelta(days=30)).isoformat(),
                'end_date': date.today().isoformat()
            }
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Report generated successfully')
        self.assertIn('report', data)
        self.assertEqual(data['report']['report_type'], 'monthly')
    
    def test_generate_report_missing_report_type(self):
        """Test report generation with missing report_type."""
        response = self.client.post(
            '/api/reports/generate',
            headers=self.get_auth_headers(),
            json={
                'start_date': (date.today() - timedelta(days=30)).isoformat(),
                'end_date': date.today().isoformat()
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_generate_report_missing_start_date(self):
        """Test report generation with missing start_date."""
        response = self.client.post(
            '/api/reports/generate',
            headers=self.get_auth_headers(),
            json={
                'report_type': 'monthly',
                'end_date': date.today().isoformat()
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_generate_report_missing_end_date(self):
        """Test report generation with missing end_date."""
        response = self.client.post(
            '/api/reports/generate',
            headers=self.get_auth_headers(),
            json={
                'report_type': 'monthly',
                'start_date': (date.today() - timedelta(days=30)).isoformat()
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_generate_report_unauthorized(self):
        """Test report generation without authentication."""
        response = self.client.post(
            '/api/reports/generate',
            json={
                'report_type': 'monthly',
                'start_date': (date.today() - timedelta(days=30)).isoformat(),
                'end_date': date.today().isoformat()
            }
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_generate_report_calculates_metrics_correctly(self):
        """Test that report generation calculates metrics correctly."""
        # Create invoices with different statuses
        self.create_test_invoice(customer_name='Customer A', status='paid', total_amount=100.0)
        self.create_test_invoice(customer_name='Customer A', status='paid', total_amount=150.0)
        self.create_test_invoice(customer_name='Customer B', status='sent', total_amount=200.0)
        self.create_test_invoice(customer_name='Customer C', status='overdue', total_amount=50.0)
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self.get_auth_headers(),
            json={
                'report_type': 'monthly',
                'start_date': (date.today() - timedelta(days=30)).isoformat(),
                'end_date': date.today().isoformat()
            }
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        report_data = data['report']['data']
        
        # Verify summary metrics
        self.assertEqual(report_data['summary']['total_invoices'], 4)
        self.assertEqual(report_data['summary']['total_revenue'], 500.0)
        self.assertEqual(report_data['summary']['paid_revenue'], 250.0)
        self.assertEqual(report_data['summary']['pending_revenue'], 200.0)
        self.assertEqual(report_data['summary']['overdue_revenue'], 50.0)
        
        # Verify status breakdown
        self.assertEqual(report_data['status_breakdown']['paid'], 2)
        self.assertEqual(report_data['status_breakdown']['sent'], 1)
        self.assertEqual(report_data['status_breakdown']['overdue'], 1)
    
    def test_generate_report_with_no_invoices(self):
        """Test report generation when no invoices exist in date range."""
        response = self.client.post(
            '/api/reports/generate',
            headers=self.get_auth_headers(),
            json={
                'report_type': 'monthly',
                'start_date': (date.today() - timedelta(days=30)).isoformat(),
                'end_date': date.today().isoformat()
            }
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        report_data = data['report']['data']
        
        self.assertEqual(report_data['summary']['total_invoices'], 0)
        self.assertEqual(report_data['summary']['total_revenue'], 0)
        self.assertEqual(report_data['summary']['average_invoice_value'], 0)
    
    def test_generate_report_top_customers(self):
        """Test that top customers are calculated correctly."""
        # Create multiple invoices for different customers
        self.create_test_invoice(customer_name='Big Customer', status='paid', total_amount=1000.0)
        self.create_test_invoice(customer_name='Big Customer', status='paid', total_amount=500.0)
        self.create_test_invoice(customer_name='Small Customer', status='paid', total_amount=100.0)
        
        response = self.client.post(
            '/api/reports/generate',
            headers=self.get_auth_headers(),
            json={
                'report_type': 'monthly',
                'start_date': (date.today() - timedelta(days=30)).isoformat(),
                'end_date': date.today().isoformat()
            }
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        top_customers = data['report']['data']['top_customers']
        
        # Big Customer should be first (highest revenue)
        self.assertEqual(top_customers[0]['name'], 'Big Customer')
        self.assertEqual(top_customers[0]['revenue'], 1500.0)
        self.assertEqual(top_customers[0]['count'], 2)
    
    def test_generate_report_different_types(self):
        """Test generating reports with different report types."""
        report_types = ['monthly', 'quarterly', 'yearly', 'custom']
        
        for report_type in report_types:
            response = self.client.post(
                '/api/reports/generate',
                headers=self.get_auth_headers(),
                json={
                    'report_type': report_type,
                    'start_date': (date.today() - timedelta(days=30)).isoformat(),
                    'end_date': date.today().isoformat()
                }
            )
            
            self.assertEqual(response.status_code, 201)
            data = response.get_json()
            self.assertEqual(data['report']['report_type'], report_type)

    # ==================== GET /api/reports/dashboard Tests ====================
    
    def test_get_dashboard_data_success(self):
        """Test successful dashboard data retrieval."""
        # Create test invoices
        self.create_test_invoice(customer_name='Customer A', status='paid', total_amount=100.0)
        self.create_test_invoice(customer_name='Customer B', status='sent', total_amount=200.0)
        
        response = self.client.get(
            '/api/reports/dashboard',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('overview', data)
        self.assertIn('recent_invoices', data)
    
    def test_get_dashboard_data_unauthorized(self):
        """Test dashboard data retrieval without authentication."""
        response = self.client.get('/api/reports/dashboard')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_dashboard_overview_metrics(self):
        """Test that dashboard overview contains correct metrics."""
        # Create invoices with different statuses
        self.create_test_invoice(customer_name='Customer A', status='paid', total_amount=100.0)
        self.create_test_invoice(customer_name='Customer B', status='sent', total_amount=200.0)
        self.create_test_invoice(customer_name='Customer C', status='overdue', total_amount=50.0)
        self.create_test_invoice(customer_name='Customer D', status='draft', total_amount=75.0)
        
        response = self.client.get(
            '/api/reports/dashboard',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        overview = data['overview']
        
        self.assertEqual(overview['total_invoices'], 4)
        self.assertEqual(overview['total_revenue'], 425.0)
        self.assertEqual(overview['paid_count'], 1)
        self.assertEqual(overview['pending_count'], 2)  # draft + sent
        self.assertEqual(overview['overdue_count'], 1)
    
    def test_get_dashboard_recent_invoices(self):
        """Test that dashboard returns recent invoices."""
        # Create 7 invoices
        for i in range(7):
            self.create_test_invoice(
                customer_name=f'Customer {i}',
                status='paid',
                total_amount=100.0 * (i + 1)
            )
        
        response = self.client.get(
            '/api/reports/dashboard',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        # Should only return 5 most recent invoices
        self.assertEqual(len(data['recent_invoices']), 5)
    
    def test_get_dashboard_empty_data(self):
        """Test dashboard data when no invoices exist."""
        response = self.client.get(
            '/api/reports/dashboard',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['overview']['total_invoices'], 0)
        self.assertEqual(data['overview']['total_revenue'], 0)
        self.assertEqual(len(data['recent_invoices']), 0)

    # ==================== DELETE /api/reports/<id> Tests ====================
    
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
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['message'], 'Report deleted successfully')
        
        # Verify report is deleted
        deleted_report = Report.query.get(report_id)
        self.assertIsNone(deleted_report)
    
    def test_delete_report_not_found(self):
        """Test deleting a non-existent report."""
        response = self.client.delete(
            '/api/reports/99999',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Report not found')
    
    def test_delete_report_unauthorized(self):
        """Test report deletion without authentication."""
        response = self.client.delete('/api/reports/1')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_report_other_user(self):
        """Test that users cannot delete other users' reports."""
        # Create another user
        other_user = User(
            username='otheruser',
            email='other@example.com',
            company_name='Other Company'
        )
        other_user.set_password('otherpassword')
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
        
        # Try to delete other user's report
        response = self.client.delete(
            f'/api/reports/{other_report_id}',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
        
        # Verify report still exists
        existing_report = Report.query.get(other_report_id)
        self.assertIsNotNone(existing_report)

    # ==================== Report Model Tests ====================
    
    def test_report_set_and_get_data(self):
        """Test Report model set_data and get_data methods."""
        report = Report(
            user_id=self.test_user.id,
            report_type='monthly',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        
        test_data = {
            'summary': {'total_invoices': 10, 'total_revenue': 5000.0},
            'status_breakdown': {'paid': 5, 'sent': 3, 'draft': 2}
        }
        
        report.set_data(test_data)
        db.session.add(report)
        db.session.commit()
        
        # Retrieve and verify data
        retrieved_report = Report.query.get(report.id)
        retrieved_data = retrieved_report.get_data()
        
        self.assertEqual(retrieved_data['summary']['total_invoices'], 10)
        self.assertEqual(retrieved_data['summary']['total_revenue'], 5000.0)
        self.assertEqual(retrieved_data['status_breakdown']['paid'], 5)
    
    def test_report_to_dict(self):
        """Test Report model to_dict method."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        report = Report(
            user_id=self.test_user.id,
            report_type='quarterly',
            start_date=start_date,
            end_date=end_date
        )
        report.set_data({'summary': {'total_invoices': 5}})
        db.session.add(report)
        db.session.commit()
        
        report_dict = report.to_dict()
        
        self.assertIn('id', report_dict)
        self.assertEqual(report_dict['report_type'], 'quarterly')
        self.assertEqual(report_dict['start_date'], start_date.isoformat())
        self.assertEqual(report_dict['end_date'], end_date.isoformat())
        self.assertIn('data', report_dict)
        self.assertIn('created_at', report_dict)


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

"""
Base test class for the Invoice Application backend tests.

Provides a reusable test setup with an in-memory SQLite database,
test client, and helper methods for authentication.
"""

import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Invoice, InvoiceItem, Report
from datetime import date, datetime


class BaseTestCase(unittest.TestCase):
    """Base test class with app factory, test client, and auth helpers."""

    def setUp(self):
        """Create a fresh app and database for each test."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'

        with self.app.app_context():
            db.drop_all()
            db.create_all()

        self.client = self.app.test_client()

    def tearDown(self):
        """Drop all tables after each test."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # ------------------------------------------------------------------ #
    # Helper methods
    # ------------------------------------------------------------------ #

    def register_user(self, username='testuser', email='test@example.com',
                      password='password123', company_name='Test Co'):
        """Register a user and return the response."""
        return self.client.post('/api/auth/register', json={
            'username': username,
            'email': email,
            'password': password,
            'company_name': company_name,
        })

    def login_user(self, username='testuser', password='password123'):
        """Log in a user and return the response."""
        return self.client.post('/api/auth/login', json={
            'username': username,
            'password': password,
        })

    def get_token(self, username='testuser', email='test@example.com',
                  password='password123'):
        """Register + login and return the JWT access token string."""
        self.register_user(username=username, email=email, password=password)
        resp = self.login_user(username=username, password=password)
        return resp.get_json()['access_token']

    def auth_header(self, token):
        """Return an Authorization header dict for the given token."""
        return {'Authorization': f'Bearer {token}'}

    def create_sample_invoice(self, token, **overrides):
        """POST a sample invoice and return the response."""
        payload = {
            'customer_name': 'Acme Corp',
            'customer_email': 'billing@acme.com',
            'customer_address': '123 Main St',
            'due_date': '2026-12-31',
            'tax_rate': 10.0,
            'notes': 'Test invoice',
            'status': 'draft',
            'items': [
                {
                    'description': 'Widget A',
                    'quantity': 2,
                    'unit_price': 50.00,
                },
                {
                    'description': 'Widget B',
                    'quantity': 1,
                    'unit_price': 100.00,
                },
            ],
        }
        payload.update(overrides)
        return self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self.auth_header(token),
        )

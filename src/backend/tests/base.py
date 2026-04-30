#!/usr/bin/env python3
"""
Shared test base class for backend endpoint tests.

Provides a BaseTestCase with app factory setup using an in-memory SQLite
database, plus helper methods for user registration, login, and auth headers.
"""

import sys
import os
import unittest

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db


class BaseTestCase(unittest.TestCase):
    """Base test case with Flask app, in-memory DB, and auth helpers."""

    def setUp(self):
        """Create app with in-memory DB, push context, create tables."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.drop_all()
        db.create_all()

        self.client = self.app.test_client()

    def tearDown(self):
        """Remove session, drop tables, pop context."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def register_user(self, username, email, password, company_name=''):
        """POST /api/auth/register and return the response."""
        return self.client.post('/api/auth/register', json={
            'username': username,
            'email': email,
            'password': password,
            'company_name': company_name,
        })

    def login_user(self, username, password):
        """POST /api/auth/login and return the response."""
        return self.client.post('/api/auth/login', json={
            'username': username,
            'password': password,
        })

    def get_auth_header(self, token):
        """Return Authorization + Content-Type headers for a Bearer token."""
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

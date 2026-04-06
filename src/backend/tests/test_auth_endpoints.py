#!/usr/bin/env python3
"""
Auth Endpoint Tests

Tests for /api/auth/* endpoints: register, login, profile.
"""

import sys
import os
import unittest

# Add the parent directory to the path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User


class TestAuthEndpoints(unittest.TestCase):
    """Test cases for auth API endpoints."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['TESTING'] = True

        with self.app.app_context():
            db.drop_all()
            db.create_all()

        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up after each test method."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _register_user(self, username='testuser', email='test@example.com',
                       password='password123', company_name='Test Co'):
        """Helper to register a user and return the response."""
        return self.client.post('/api/auth/register', json={
            'username': username,
            'email': email,
            'password': password,
            'company_name': company_name
        })

    def _login_user(self, username='testuser', password='password123'):
        """Helper to login a user and return the response."""
        return self.client.post('/api/auth/login', json={
            'username': username,
            'password': password
        })

    def _get_auth_header(self, token):
        """Helper to build an Authorization header."""
        return {'Authorization': f'Bearer {token}'}

    # --- Register Endpoint Tests ---

    def test_register_success(self):
        """Test successful user registration."""
        resp = self._register_user()
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(data['message'], 'User created successfully')
        self.assertIn('access_token', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@example.com')
        self.assertEqual(data['user']['company_name'], 'Test Co')

    def test_register_missing_username(self):
        """Test registration fails when username is missing."""
        resp = self.client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('username is required', data['error'])

    def test_register_missing_email(self):
        """Test registration fails when email is missing."""
        resp = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'password123'
        })
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('email is required', data['error'])

    def test_register_missing_password(self):
        """Test registration fails when password is missing."""
        resp = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com'
        })
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('password is required', data['error'])

    def test_register_duplicate_username(self):
        """Test registration fails for duplicate username."""
        self._register_user()
        resp = self._register_user(email='other@example.com')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(data['error'], 'Username already exists')

    def test_register_duplicate_email(self):
        """Test registration fails for duplicate email."""
        self._register_user()
        resp = self._register_user(username='otheruser')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(data['error'], 'Email already exists')

    def test_register_without_company_name(self):
        """Test registration succeeds without optional company_name."""
        resp = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        })
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(data['user']['company_name'], '')

    # --- Login Endpoint Tests ---

    def test_login_success(self):
        """Test successful login."""
        self._register_user()
        resp = self._login_user()
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['message'], 'Login successful')
        self.assertIn('access_token', data)
        self.assertEqual(data['user']['username'], 'testuser')

    def test_login_wrong_password(self):
        """Test login fails with wrong password."""
        self._register_user()
        resp = self._login_user(password='wrongpassword')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(data['error'], 'Invalid credentials')

    def test_login_nonexistent_user(self):
        """Test login fails for nonexistent user."""
        resp = self._login_user(username='nobody')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(data['error'], 'Invalid credentials')

    def test_login_missing_username(self):
        """Test login fails when username is missing."""
        resp = self.client.post('/api/auth/login', json={
            'password': 'password123'
        })
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('required', data['error'])

    def test_login_missing_password(self):
        """Test login fails when password is missing."""
        resp = self.client.post('/api/auth/login', json={
            'username': 'testuser'
        })
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertIn('required', data['error'])

    # --- Profile Endpoint Tests ---

    def test_get_profile_success(self):
        """Test successful profile retrieval."""
        reg_resp = self._register_user()
        token = reg_resp.get_json()['access_token']

        resp = self.client.get(
            '/api/auth/profile',
            headers=self._get_auth_header(token)
        )
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@example.com')

    def test_get_profile_no_token(self):
        """Test profile retrieval fails without token."""
        resp = self.client.get('/api/auth/profile')
        self.assertEqual(resp.status_code, 401)

    def test_get_profile_invalid_token(self):
        """Test profile retrieval fails with invalid token."""
        resp = self.client.get(
            '/api/auth/profile',
            headers=self._get_auth_header('invalid.token.here')
        )
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()

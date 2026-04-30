#!/usr/bin/env python3
"""
Auth endpoint tests.

Tests for POST /api/auth/register, POST /api/auth/login,
and GET /api/auth/profile.
"""

import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base import BaseTestCase


class TestAuthEndpoints(BaseTestCase):
    """Test cases for authentication endpoints."""

    # ------------------------------------------------------------------
    # POST /api/auth/register
    # ------------------------------------------------------------------

    def test_register_success(self):
        resp = self.register_user('alice', 'alice@example.com', 'password123')
        data = resp.get_json()
        self.assertEqual(resp.status_code, 201)
        self.assertIn('access_token', data)
        self.assertEqual(data['user']['username'], 'alice')
        self.assertEqual(data['user']['email'], 'alice@example.com')

    def test_register_missing_username(self):
        resp = self.client.post('/api/auth/register', json={
            'email': 'a@b.com',
            'password': 'pass',
        })
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_email(self):
        resp = self.client.post('/api/auth/register', json={
            'username': 'alice',
            'password': 'pass',
        })
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_password(self):
        resp = self.client.post('/api/auth/register', json={
            'username': 'alice',
            'email': 'a@b.com',
        })
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_username(self):
        self.register_user('alice', 'alice@example.com', 'pass1')
        resp = self.register_user('alice', 'other@example.com', 'pass2')
        data = resp.get_json()
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Username already exists', data['error'])

    def test_register_duplicate_email(self):
        self.register_user('alice', 'alice@example.com', 'pass1')
        resp = self.register_user('bob', 'alice@example.com', 'pass2')
        data = resp.get_json()
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Email already exists', data['error'])

    # ------------------------------------------------------------------
    # POST /api/auth/login
    # ------------------------------------------------------------------

    def test_login_success(self):
        self.register_user('alice', 'alice@example.com', 'password123')
        resp = self.login_user('alice', 'password123')
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access_token', data)
        self.assertIn('user', data)

    def test_login_missing_fields(self):
        resp = self.client.post('/api/auth/login', json={})
        self.assertEqual(resp.status_code, 400)

    def test_login_wrong_password(self):
        self.register_user('alice', 'alice@example.com', 'password123')
        resp = self.login_user('alice', 'wrongpass')
        self.assertEqual(resp.status_code, 401)

    def test_login_nonexistent_user(self):
        resp = self.login_user('ghost', 'password123')
        self.assertEqual(resp.status_code, 401)

    # ------------------------------------------------------------------
    # GET /api/auth/profile
    # ------------------------------------------------------------------

    def test_get_profile_success(self):
        reg = self.register_user('alice', 'alice@example.com', 'password123')
        token = reg.get_json()['access_token']
        resp = self.client.get('/api/auth/profile',
                               headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['user']['username'], 'alice')
        self.assertEqual(data['user']['email'], 'alice@example.com')

    def test_get_profile_no_token(self):
        resp = self.client.get('/api/auth/profile')
        self.assertEqual(resp.status_code, 401)

    def test_get_profile_invalid_token(self):
        resp = self.client.get('/api/auth/profile',
                               headers=self.get_auth_header('invalidtoken'))
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()

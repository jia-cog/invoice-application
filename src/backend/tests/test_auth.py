"""
Tests for authentication routes: register, login, and profile.
"""

import unittest
from base import BaseTestCase


class TestRegister(BaseTestCase):
    """POST /api/auth/register"""

    def test_register_success(self):
        resp = self.register_user()
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        self.assertIn('access_token', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@example.com')
        self.assertEqual(data['message'], 'User created successfully')

    def test_register_with_company_name(self):
        resp = self.register_user(company_name='ACME Inc')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(data['user']['company_name'], 'ACME Inc')

    def test_register_missing_username(self):
        resp = self.client.post('/api/auth/register', json={
            'email': 'a@b.com',
            'password': 'pw',
        })
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_email(self):
        resp = self.client.post('/api/auth/register', json={
            'username': 'user1',
            'password': 'pw',
        })
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_password(self):
        resp = self.client.post('/api/auth/register', json={
            'username': 'user1',
            'email': 'a@b.com',
        })
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_username(self):
        self.register_user()
        resp = self.register_user(email='other@example.com')

        self.assertEqual(resp.status_code, 400)
        self.assertIn('Username already exists', resp.get_json()['error'])

    def test_register_duplicate_email(self):
        self.register_user()
        resp = self.register_user(username='another')

        self.assertEqual(resp.status_code, 400)
        self.assertIn('Email already exists', resp.get_json()['error'])

    def test_register_empty_body(self):
        resp = self.client.post('/api/auth/register', json={})
        self.assertEqual(resp.status_code, 400)


class TestLogin(BaseTestCase):
    """POST /api/auth/login"""

    def test_login_success(self):
        self.register_user()
        resp = self.login_user()
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertIn('access_token', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['message'], 'Login successful')

    def test_login_wrong_password(self):
        self.register_user()
        resp = self.login_user(password='wrong')

        self.assertEqual(resp.status_code, 401)
        self.assertIn('Invalid credentials', resp.get_json()['error'])

    def test_login_nonexistent_user(self):
        resp = self.login_user(username='ghost')

        self.assertEqual(resp.status_code, 401)
        self.assertIn('Invalid credentials', resp.get_json()['error'])

    def test_login_missing_username(self):
        resp = self.client.post('/api/auth/login', json={
            'password': 'pw',
        })
        self.assertEqual(resp.status_code, 400)

    def test_login_missing_password(self):
        resp = self.client.post('/api/auth/login', json={
            'username': 'testuser',
        })
        self.assertEqual(resp.status_code, 400)


class TestProfile(BaseTestCase):
    """GET /api/auth/profile"""

    def test_profile_success(self):
        token = self.get_token()
        resp = self.client.get('/api/auth/profile',
                               headers=self.auth_header(token))
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@example.com')

    def test_profile_no_token(self):
        resp = self.client.get('/api/auth/profile')
        self.assertEqual(resp.status_code, 401)

    def test_profile_invalid_token(self):
        resp = self.client.get('/api/auth/profile',
                               headers=self.auth_header('bad.token.value'))
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""
Authentication Route Tests

Comprehensive tests for authentication endpoints: register, login, and profile.
"""

import sys
import os
import unittest
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager
from config import Config
from models import db, User
from app import create_app


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'


class TestAuthRoutes(unittest.TestCase):
    """Test cases for authentication routes."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.drop_all()
            db.create_all()
    
    def tearDown(self):
        """Clean up after each test method."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_register_success(self):
        """Test successful user registration."""
        response = self.client.post('/api/auth/register', 
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123',
                'company_name': 'Test Company'
            })
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        
        self.assertIn('message', data)
        self.assertIn('access_token', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@example.com')
        self.assertEqual(data['user']['company_name'], 'Test Company')
        self.assertNotIn('password_hash', data['user'])
    
    def test_register_missing_username(self):
        """Test registration with missing username."""
        response = self.client.post('/api/auth/register',
            json={
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('username', data['error'].lower())
    
    def test_register_missing_email(self):
        """Test registration with missing email."""
        response = self.client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'password': 'password123'
            })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('email', data['error'].lower())
    
    def test_register_missing_password(self):
        """Test registration with missing password."""
        response = self.client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com'
            })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('password', data['error'].lower())
    
    def test_register_duplicate_username(self):
        """Test registration with duplicate username."""
        self.client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'test1@example.com',
                'password': 'password123'
            })
        
        response = self.client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'test2@example.com',
                'password': 'password456'
            })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('username', data['error'].lower())
    
    def test_register_duplicate_email(self):
        """Test registration with duplicate email."""
        self.client.post('/api/auth/register',
            json={
                'username': 'testuser1',
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        response = self.client.post('/api/auth/register',
            json={
                'username': 'testuser2',
                'email': 'test@example.com',
                'password': 'password456'
            })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('email', data['error'].lower())
    
    def test_register_without_company_name(self):
        """Test registration without optional company_name."""
        response = self.client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['company_name'], '')
    
    def test_login_success(self):
        """Test successful login."""
        self.client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        response = self.client.post('/api/auth/login',
            json={
                'username': 'testuser',
                'password': 'password123'
            })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('message', data)
        self.assertIn('access_token', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')
    
    def test_login_invalid_username(self):
        """Test login with invalid username."""
        response = self.client.post('/api/auth/login',
            json={
                'username': 'nonexistent',
                'password': 'password123'
            })
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('invalid', data['error'].lower())
    
    def test_login_invalid_password(self):
        """Test login with invalid password."""
        self.client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        response = self.client.post('/api/auth/login',
            json={
                'username': 'testuser',
                'password': 'wrongpassword'
            })
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('invalid', data['error'].lower())
    
    def test_login_missing_username(self):
        """Test login with missing username."""
        response = self.client.post('/api/auth/login',
            json={
                'password': 'password123'
            })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_login_missing_password(self):
        """Test login with missing password."""
        response = self.client.post('/api/auth/login',
            json={
                'username': 'testuser'
            })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_get_profile_success(self):
        """Test getting user profile with valid token."""
        register_response = self.client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123',
                'company_name': 'Test Company'
            })
        
        data = json.loads(register_response.data)
        token = data['access_token']
        
        response = self.client.get('/api/auth/profile',
            headers={'Authorization': f'Bearer {token}'})
        
        self.assertEqual(response.status_code, 200)
        profile_data = json.loads(response.data)
        
        self.assertIn('user', profile_data)
        self.assertEqual(profile_data['user']['username'], 'testuser')
        self.assertEqual(profile_data['user']['email'], 'test@example.com')
    
    def test_get_profile_missing_token(self):
        """Test getting profile without token."""
        response = self.client.get('/api/auth/profile')
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_get_profile_invalid_token(self):
        """Test getting profile with invalid token."""
        response = self.client.get('/api/auth/profile',
            headers={'Authorization': 'Bearer invalid.token.here'})
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_token_persistence_across_requests(self):
        """Test that token works across multiple requests."""
        register_response = self.client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        data = json.loads(register_response.data)
        token = data['access_token']
        
        for _ in range(3):
            response = self.client.get('/api/auth/profile',
                headers={'Authorization': f'Bearer {token}'})
            self.assertEqual(response.status_code, 200)
    
    def test_login_returns_same_user_data(self):
        """Test that login returns the same user data as registration."""
        register_response = self.client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123',
                'company_name': 'Test Company'
            })
        
        register_data = json.loads(register_response.data)
        
        login_response = self.client.post('/api/auth/login',
            json={
                'username': 'testuser',
                'password': 'password123'
            })
        
        login_data = json.loads(login_response.data)
        
        self.assertEqual(register_data['user']['username'], login_data['user']['username'])
        self.assertEqual(register_data['user']['email'], login_data['user']['email'])
        self.assertEqual(register_data['user']['company_name'], login_data['user']['company_name'])


def run_auth_tests():
    """Run all auth tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAuthRoutes)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_auth_tests()
    if success:
        print("\n✅ All auth tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some auth tests failed!")
        sys.exit(1)

#!/usr/bin/env python3
"""
JWT Authentication Tests

Tests for JWT token creation, validation, and authentication functionality,
including is_admin claim-based authorization.
"""

import sys
import os
import unittest

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token, decode_token, get_jwt_identity
from config import Config
from models import db, User


class TestJWTAuthentication(unittest.TestCase):
    """Test cases for JWT authentication functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.jwt = JWTManager(self.app)
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        @self.jwt.additional_claims_loader
        def add_claims_to_access_token(identity):
            user = User.query.get(int(identity))
            if user:
                return {'is_admin': user.is_admin}
            return {'is_admin': False}
    
    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_create_access_token_with_string_identity(self):
        """Test that access tokens can be created with string identity."""
        test_user_id = "123"
        token = create_access_token(identity=test_user_id)
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
    
    def test_create_access_token_with_integer_converted_to_string(self):
        """Test that integer user IDs are properly converted to strings."""
        test_user_id = 123
        token = create_access_token(identity=str(test_user_id))
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
    
    def test_decode_token_success(self):
        """Test successful token decoding."""
        test_user_id = "456"
        token = create_access_token(identity=test_user_id)
        
        decoded = decode_token(token)
        
        self.assertIsNotNone(decoded)
        self.assertIsInstance(decoded, dict)
        self.assertIn('sub', decoded)  # 'sub' is the subject claim
        self.assertEqual(decoded['sub'], test_user_id)
    
    def test_token_identity_consistency(self):
        """Test that the identity in the token matches what was provided."""
        test_user_id = "789"
        token = create_access_token(identity=test_user_id)
        decoded = decode_token(token)
        
        # The subject should match our original user ID
        self.assertEqual(decoded['sub'], test_user_id)
    
    def test_multiple_tokens_different_identities(self):
        """Test creating multiple tokens with different identities."""
        user_ids = ["100", "200", "300"]
        tokens = []
        
        for user_id in user_ids:
            token = create_access_token(identity=user_id)
            tokens.append(token)
            
            # Verify each token is unique
            self.assertNotIn(token, tokens[:-1])
            
            # Verify each token decodes correctly
            decoded = decode_token(token)
            self.assertEqual(decoded['sub'], user_id)
    
    def test_token_contains_required_claims(self):
        """Test that tokens contain all required JWT claims."""
        test_user_id = "999"
        token = create_access_token(identity=test_user_id)
        decoded = decode_token(token)
        
        # Check for standard JWT claims
        required_claims = ['sub', 'iat', 'exp', 'jti', 'type']
        for claim in required_claims:
            self.assertIn(claim, decoded, f"Missing required claim: {claim}")
    
    def test_invalid_token_handling(self):
        """Test handling of invalid tokens."""
        invalid_token = "invalid.token.here"
        
        with self.assertRaises(Exception):
            decode_token(invalid_token)

    def test_token_contains_is_admin_claim_for_regular_user(self):
        """Test that tokens for regular users contain is_admin=False."""
        user = User(username='regular', email='regular@test.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)

        self.assertIn('is_admin', decoded)
        self.assertFalse(decoded['is_admin'])

    def test_token_contains_is_admin_claim_for_admin_user(self):
        """Test that tokens for admin users contain is_admin=True."""
        user = User(username='admin', email='admin@test.com', is_admin=True)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)

        self.assertIn('is_admin', decoded)
        self.assertTrue(decoded['is_admin'])

    def test_is_admin_defaults_to_false(self):
        """Test that new users default to is_admin=False."""
        user = User(username='newuser', email='new@test.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        self.assertFalse(user.is_admin)

    def test_user_to_dict_includes_is_admin(self):
        """Test that User.to_dict() includes the is_admin field."""
        user = User(username='dictuser', email='dict@test.com', is_admin=True)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        user_dict = user.to_dict()
        self.assertIn('is_admin', user_dict)
        self.assertTrue(user_dict['is_admin'])


class TestAdminRequired(unittest.TestCase):
    """Test cases for admin_required decorator."""

    def setUp(self):
        """Set up test app with routes."""
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.jwt = JWTManager(self.app)
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        @self.jwt.additional_claims_loader
        def add_claims_to_access_token(identity):
            user = User.query.get(int(identity))
            if user:
                return {'is_admin': user.is_admin}
            return {'is_admin': False}

        # Import and register auth blueprint
        from routes.auth import auth_bp
        self.app.register_blueprint(auth_bp, url_prefix='/api/auth')

        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_admin_endpoint_accessible_by_admin(self):
        """Test that admin users can access admin-only endpoints."""
        admin = User(username='admin', email='admin@test.com', is_admin=True)
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()

        token = create_access_token(identity=str(admin.id))
        response = self.client.get(
            '/api/auth/users',
            headers={'Authorization': f'Bearer {token}'}
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_endpoint_rejected_for_non_admin(self):
        """Test that non-admin users get 403 on admin-only endpoints."""
        user = User(username='regular', email='regular@test.com', is_admin=False)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        response = self.client.get(
            '/api/auth/users',
            headers={'Authorization': f'Bearer {token}'}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('Admin access required', response.get_json()['error'])

    def test_admin_endpoint_rejected_without_token(self):
        """Test that unauthenticated requests get 401."""
        response = self.client.get('/api/auth/users')
        self.assertEqual(response.status_code, 401)


def run_jwt_tests():
    """Run all JWT tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestJWTAuthentication))
    suite.addTests(loader.loadTestsFromTestCase(TestAdminRequired))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run the tests
    success = run_jwt_tests()
    if success:
        print("\nAll JWT tests passed!")
        sys.exit(0)
    else:
        print("\nSome JWT tests failed!")
        sys.exit(1)

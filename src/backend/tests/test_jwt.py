#!/usr/bin/env python3
"""
JWT Authentication Tests

Tests for JWT token creation, validation, and authentication functionality.
"""

import sys
import os
import unittest

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token, decode_token, get_jwt_identity
from config import Config


class TestJWTAuthentication(unittest.TestCase):
    """Test cases for JWT authentication functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.jwt = JWTManager(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after each test method."""
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


class TestAdminClaim(unittest.TestCase):
    """Test cases for the custom is_admin JWT claim."""

    def setUp(self):
        """Set up a Flask app backed by an in-memory SQLite DB."""
        # Use an isolated in-memory database so we don't touch real data.
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

        from app import create_app
        from models import db, User

        self.User = User
        self.db = db
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        # create_app() already calls db.create_all() within an app context.

    def tearDown(self):
        """Clean up after each test method."""
        self.db.session.remove()
        self.db.drop_all()
        self.app_context.pop()
        os.environ.pop('DATABASE_URL', None)

    def test_token_contains_is_admin_claim_for_admin_user(self):
        """Tokens for admin users should embed is_admin=True."""
        user = self.User(username='testadmin', email='admin@test.com', is_admin=True)
        user.set_password('password')
        self.db.session.add(user)
        self.db.session.commit()

        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)

        self.assertIn('is_admin', decoded)
        self.assertTrue(decoded['is_admin'])

    def test_token_contains_is_admin_claim_for_regular_user(self):
        """Tokens for non-admin users should embed is_admin=False."""
        user = self.User(username='testuser', email='user@test.com', is_admin=False)
        user.set_password('password')
        self.db.session.add(user)
        self.db.session.commit()

        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)

        self.assertIn('is_admin', decoded)
        self.assertFalse(decoded['is_admin'])


def run_jwt_tests():
    """Run all JWT tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestJWTAuthentication))
    suite.addTests(loader.loadTestsFromTestCase(TestAdminClaim))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run the tests
    success = run_jwt_tests()
    if success:
        print("\n✅ All JWT tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some JWT tests failed!")
        sys.exit(1)

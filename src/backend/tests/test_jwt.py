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

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token, decode_token, get_jwt_identity
from config import Config
from utils.auth import admin_required


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
    
    def test_token_with_is_admin_true_claim(self):
        """Test that tokens carry an is_admin=True claim when provided."""
        token = create_access_token(
            identity="42",
            additional_claims={"is_admin": True}
        )
        decoded = decode_token(token)
        
        self.assertIn('is_admin', decoded)
        self.assertTrue(decoded['is_admin'])
    
    def test_token_without_is_admin_claim_defaults_to_false(self):
        """Test that tokens without is_admin claim are absent or False."""
        token_with_false = create_access_token(
            identity="43",
            additional_claims={"is_admin": False}
        )
        decoded_with_false = decode_token(token_with_false)
        self.assertIn('is_admin', decoded_with_false)
        self.assertFalse(decoded_with_false['is_admin'])
        
        token_no_claim = create_access_token(identity="44")
        decoded_no_claim = decode_token(token_no_claim)
        self.assertFalse(decoded_no_claim.get('is_admin', False))


class TestAdminRequiredDecorator(unittest.TestCase):
    """Test cases for the admin_required decorator."""
    
    def setUp(self):
        """Set up a Flask test app with a route protected by admin_required."""
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.jwt = JWTManager(self.app)
        
        @self.app.route('/admin-only', methods=['GET'])
        @admin_required
        def admin_only():
            return jsonify({'message': 'admin ok'}), 200
        
        self.client = self.app.test_client()
    
    def test_admin_required_allows_admin(self):
        """Admin tokens should be allowed through."""
        with self.app.app_context():
            token = create_access_token(
                identity="1",
                additional_claims={"is_admin": True}
            )
        
        response = self.client.get(
            '/admin-only',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'message': 'admin ok'})
    
    def test_admin_required_rejects_non_admin(self):
        """Non-admin tokens should receive a 403."""
        with self.app.app_context():
            token = create_access_token(
                identity="2",
                additional_claims={"is_admin": False}
            )
        
        response = self.client.get(
            '/admin-only',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.get_json(),
            {'error': 'Admin access required'}
        )
    
    def test_admin_required_rejects_missing_token(self):
        """Requests without a token should not pass admin_required."""
        response = self.client.get('/admin-only')
        
        self.assertEqual(response.status_code, 401)


def run_jwt_tests():
    """Run all JWT tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([
        loader.loadTestsFromTestCase(TestJWTAuthentication),
        loader.loadTestsFromTestCase(TestAdminRequiredDecorator),
    ])
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

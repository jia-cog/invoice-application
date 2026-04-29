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
from models import db, User


class TestJWTAuthentication(unittest.TestCase):
    """Test cases for JWT authentication functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        self.jwt = JWTManager(self.app)

        @self.jwt.additional_claims_loader
        def add_claims_to_access_token(identity):
            user = User.query.get(int(identity))
            return {
                "is_admin": user.is_admin if user else False,
                "is_authorized": user.is_authorized if user else False,
            }

        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
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

    def test_token_contains_is_admin_claim(self):
        """Test that tokens contain the is_admin claim."""
        user = User(username="claimuser", email="claim@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)

        self.assertIn("is_admin", decoded)

    def test_admin_claim_is_false_by_default(self):
        """Test that new users get is_admin=False by default."""
        user = User(username="regularuser", email="regular@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)

        self.assertFalse(decoded["is_admin"])

    def test_admin_claim_is_true_for_admin_user(self):
        """Test that admin users get is_admin=True in their token."""
        user = User(username="adminuser", email="admin@test.com", is_admin=True)
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)

        self.assertTrue(decoded["is_admin"])

    def test_token_contains_is_authorized_claim(self):
        """Test that tokens contain the is_authorized claim."""
        user = User(username="authclaimuser", email="authclaim@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)

        self.assertIn("is_authorized", decoded)

    def test_authorized_claim_is_true_by_default(self):
        """Test that new users get is_authorized=True by default."""
        user = User(username="defaultauthuser", email="defaultauth@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)

        self.assertTrue(decoded["is_authorized"])

    def test_authorized_claim_is_false_when_revoked(self):
        """Test that unauthorized users get is_authorized=False in their token."""
        user = User(username="revokeduser", email="revoked@test.com", is_authorized=False)
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)

        self.assertFalse(decoded["is_authorized"])


def run_jwt_tests():
    """Run all JWT tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestJWTAuthentication)
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

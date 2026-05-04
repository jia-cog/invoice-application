#!/usr/bin/env python3
"""Tests for the is_admin JWT claim and admin_required decorator."""

import os
import sys
import tempfile
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAdminAuth(unittest.TestCase):
    """Verify additional_claims_loader and admin_required decorator behavior."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        os.environ["DATABASE_URL"] = f"sqlite:///{self._tmp.name}"

        # Reload modules so config picks up the override DATABASE_URL.
        for mod in [m for m in list(sys.modules) if m in {
            "config", "models", "app", "routes.auth", "routes.invoices",
            "routes.reports", "utils.decorators",
        }]:
            del sys.modules[mod]

        from app import create_app
        from models import db, User

        self.db = db
        self.User = User
        self.app = create_app()
        self.client = self.app.test_client()

        with self.app.app_context():
            admin = User(username="admin", email="admin@example.com", is_admin=True)
            admin.set_password("adminpw")
            regular = User(username="alice", email="alice@example.com")
            regular.set_password("alicepw")
            db.session.add_all([admin, regular])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
        os.unlink(self._tmp.name)
        os.environ.pop("DATABASE_URL", None)

    def _login(self, username, password):
        response = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def test_login_response_includes_is_admin(self):
        admin_payload = self._login("admin", "adminpw")
        self.assertTrue(admin_payload["user"]["is_admin"])

        regular_payload = self._login("alice", "alicepw")
        self.assertFalse(regular_payload["user"]["is_admin"])

    def test_admin_endpoint_allows_admin(self):
        token = self._login("admin", "adminpw")["access_token"]
        response = self.client.get(
            "/api/auth/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        users = response.get_json()["users"]
        self.assertEqual({u["username"] for u in users}, {"admin", "alice"})

    def test_admin_endpoint_rejects_regular_user(self):
        token = self._login("alice", "alicepw")["access_token"]
        response = self.client.get(
            "/api/auth/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json(), {"error": "Admin access required"})

    def test_admin_endpoint_rejects_missing_token(self):
        response = self.client.get("/api/auth/admin/users")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

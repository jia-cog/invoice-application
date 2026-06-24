#!/usr/bin/env python3
"""
Bootstrap a sample user and print a JWT for local development.

- Username: testuser@email.com
- Email:    testuser@email.com
- Password: topsecretpassword

Pass ``--admin`` to also create and promote an admin user:

- Username: admin@email.com
- Email:    admin@email.com
- Password: adminpassword

Reads API base URL from the environment variable API_BASE_URL.
Defaults to http://localhost:5001/api (matches src/backend/app.py default).

Endpoints:
- POST {BASE_URL}/auth/register
- POST {BASE_URL}/auth/login
- GET  {BASE_URL}/auth/profile (used to verify token)
- POST {BASE_URL}/auth/promote (admin promotion, requires promote_key)

Usage:
  python src/backend/bootstrap/bootstrap_sample_data.py
  python src/backend/bootstrap/bootstrap_sample_data.py --admin

Optionally set:
  export API_BASE_URL=http://localhost:5001/api

This script uses only the Python standard library (urllib), so no extra deps needed.
"""

import json
import os
import sys
from typing import Union, Optional
from urllib import request, error

DEFAULT_BASE_URL = "http://localhost:5001/api"
USERNAME = "testuser@email.com"
EMAIL = "testuser@email.com"
PASSWORD = "topsecretpassword"
COMPANY_NAME = "Test Company"

ADMIN_USERNAME = "admin@email.com"
ADMIN_EMAIL = "admin@email.com"
ADMIN_PASSWORD = "adminpassword"
ADMIN_COMPANY_NAME = "Admin Company"

def _http_request(method: str, url: str, payload: Optional[dict] = None, headers: Optional[dict] = None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.getcode(), json.loads(body) if body else {}
            except json.JSONDecodeError:
                return resp.getcode(), {"raw": body}
    except error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body) if body else {"error": f"HTTPError {e.code}"}
        except json.JSONDecodeError:
            return e.code, {"error": body or f"HTTPError {e.code}"}
    except error.URLError as e:
        return None, {"error": f"URLError: {e.reason}"}


def register_user(base_url: str) -> tuple[Optional[int], dict]:
    url = f"{base_url}/auth/register"
    payload = {
        "username": USERNAME,
        "email": EMAIL,
        "password": PASSWORD,
        "company_name": COMPANY_NAME,
    }
    return _http_request("POST", url, payload)


def login_user(base_url: str) -> tuple[Optional[int], dict]:
    url = f"{base_url}/auth/login"
    payload = {
        "username": USERNAME,
        "password": PASSWORD,   
    }
    return _http_request("POST", url, payload)


def get_profile(base_url: str, token: str) -> tuple[Optional[int], dict]:
    url = f"{base_url}/auth/profile"
    headers = {"Authorization": f"Bearer {token}"}
    return _http_request("GET", url, headers=headers)


def register_admin(base_url: str) -> tuple[Optional[int], dict]:
    url = f"{base_url}/auth/register"
    payload = {
        "username": ADMIN_USERNAME,
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "company_name": ADMIN_COMPANY_NAME,
    }
    return _http_request("POST", url, payload)


def login_admin(base_url: str) -> tuple[Optional[int], dict]:
    url = f"{base_url}/auth/login"
    payload = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    }
    return _http_request("POST", url, payload)


def promote_to_admin(base_url: str, token: str, promote_key: str) -> tuple[Optional[int], dict]:
    url = f"{base_url}/auth/promote"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"promote_key": promote_key}
    return _http_request("POST", url, payload=payload, headers=headers)


def main() -> int:
    base_url = os.environ.get("API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    create_admin = "--admin" in sys.argv

    print(f"Using API base URL: {base_url}")
    print("Registering sample user ...")
    status, data = register_user(base_url)

    if status is None:
        print(f"Error: Could not reach API: {data.get('error')}")
        return 2

    if status == 201:
        print("✓ User created successfully")
    elif status == 400 and isinstance(data, dict):
        msg = data.get("error", "")
        if any(s in msg.lower() for s in ["exists", "already", "taken"]):
            print("ℹ︎ User already exists — proceeding to login")
        else:
            print(f"Registration returned 400: {data}")
            print("Proceeding to login anyway ...")
    elif status >= 500:
        print(f"Registration failed with server error {status}: {data}")
        return 3
    elif status != 201:
        print(f"Unexpected registration status {status}: {data}")
        # Continue to login attempt anyway

    print("Logging in sample user ...")
    status, data = login_user(base_url)

    if status is None:
        print(f"Error: Could not reach API during login: {data.get('error')}")
        return 2

    if status == 200 and isinstance(data, dict):
        token = data.get("access_token")
        if not token:
            print(f"Login succeeded but no access_token in response: {data}")
            return 4
        user = data.get("user", {})
        print("✓ Login successful")
        print("")
        print("JWT (access_token):")
        print(token)
        print("")
        print("You can export this for convenience:")
        print(f"export TEST_USER_TOKEN='{token}'")

        # Optional: verify token by hitting profile
        p_status, p_data = get_profile(base_url, token)
        if p_status == 200:
            print("✓ Token verified via /auth/profile")
        else:
            print(f"Warning: /auth/profile check returned {p_status}: {p_data}")

        if not create_admin:
            return 0

    if not create_admin and status == 401:
        print("✗ Login failed: invalid credentials.\n"
              "If a user with the same username already exists but with a different password, "
              "either delete that user from the DB or change PASSWORD in this script.")
        return 5

    if not create_admin:
        print(f"Unexpected login status {status}: {data}")
        return 6

    # --- Admin user flow (--admin flag) ---
    print("")
    print("=" * 40)
    print("Creating admin user ...")

    status, data = register_admin(base_url)
    if status == 201:
        print("✓ Admin user created successfully")
    elif status == 400 and isinstance(data, dict):
        msg = data.get("error", "")
        if any(s in msg.lower() for s in ["exists", "already", "taken"]):
            print("ℹ︎ Admin user already exists — proceeding to login")
        else:
            print(f"Admin registration returned 400: {data}")
    elif status is None:
        print(f"Error: Could not reach API: {data.get('error')}")
        return 2
    else:
        print(f"Admin registration status {status}: {data}")

    print("Logging in admin user ...")
    status, data = login_admin(base_url)

    if status is None:
        print(f"Error: Could not reach API during admin login: {data.get('error')}")
        return 2

    if status != 200 or not isinstance(data, dict):
        print(f"Admin login failed with status {status}: {data}")
        return 7

    admin_token = data.get("access_token")
    if not admin_token:
        print(f"Admin login succeeded but no access_token: {data}")
        return 4

    print("✓ Admin login successful")

    promote_key = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    print("Promoting admin user ...")
    status, data = promote_to_admin(base_url, admin_token, promote_key)

    if status == 200:
        admin_token = data.get("access_token", admin_token)
        print("✓ Admin user promoted successfully")
        print("")
        print("Admin JWT (access_token):")
        print(admin_token)
        print("")
        print("You can export this for convenience:")
        print(f"export ADMIN_USER_TOKEN='{admin_token}'")
        return 0

    print(f"Promotion failed with status {status}: {data}")
    return 8


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(130)

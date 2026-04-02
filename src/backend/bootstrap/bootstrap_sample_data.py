#!/usr/bin/env python3
"""
Bootstrap a sample user and print a JWT for local development.

- Username: testuser@email.com
- Email:    testuser@email.com
- Password: topsecretpassword

Reads API base URL from the environment variable API_BASE_URL.
Defaults to http://localhost:5001/api (matches src/backend/app.py default).

Endpoints (from openapi.yaml):
- POST {BASE_URL}/auth/register
- POST {BASE_URL}/auth/login
- GET  {BASE_URL}/auth/profile (used to verify token)

Usage:
  python src/backend/bootstrap/bootstrap_login.py

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


def main() -> int:
    # Prevent accidental execution in production environments
    env = os.environ.get("ENV", os.environ.get("FLASK_ENV", "")).lower()
    if env == "production":
        print(
            "ERROR: This bootstrap script must not be run in production.\n"
            "It creates test user accounts with well-known credentials.\n"
            "Detected ENV/FLASK_ENV=production. Aborting."
        )
        return 1

    base_url = os.environ.get("API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

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
        return 0

    if status == 401:
        print("✗ Login failed: invalid credentials.\n"
              "If a user with the same username already exists but with a different password, "
              "either delete that user from the DB or change PASSWORD in this script.")
        return 5

    print(f"Unexpected login status {status}: {data}")
    return 6


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(130)

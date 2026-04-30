# Backend Tests

This directory contains all backend tests for the Invoice Application.

## Structure

```
tests/
├── __init__.py          # Makes tests a Python package
├── README.md            # This file
├── run_tests.py         # Test runner script
├── base.py              # Shared BaseTestCase with in-memory DB setup
├── test_jwt.py          # JWT authentication tests
├── test_auth.py         # Auth endpoint tests (register, login, profile)
├── test_invoices.py     # Invoice CRUD endpoint tests
├── test_reports.py      # Report & dashboard endpoint tests
└── test_health.py       # Health check endpoint test
```

## Running Tests

### Run All Tests
```bash
# From the backend directory
python3 tests/run_tests.py
```

### Run Specific Test File
```bash
# From the backend directory
python3 tests/test_jwt.py
python3 tests/test_auth.py
python3 tests/test_invoices.py
python3 tests/test_reports.py
python3 tests/test_health.py
```

### Run Tests with Python's unittest module
```bash
# From the backend directory
python3 -m unittest discover tests -v
```

## Test Files

### `base.py` — Shared Test Base Class
Provides `BaseTestCase(unittest.TestCase)` used by all endpoint test files. Sets up a Flask app with an **in-memory SQLite database** (`sqlite:///:memory:`) so tests are fast and isolated. Includes helper methods:
- `register_user(username, email, password, company_name='')` — POST `/api/auth/register`
- `login_user(username, password)` — POST `/api/auth/login`
- `get_auth_header(token)` — returns `Authorization: Bearer <token>` headers

### `test_jwt.py` — JWT Authentication Tests
- Token creation with string identities
- Token creation with integer IDs (converted to strings)
- Token decoding and validation
- Token identity consistency
- Required JWT claims verification
- Invalid token handling

### `test_auth.py` — Auth Endpoint Tests
- **POST /api/auth/register** — success, missing fields, duplicate username/email
- **POST /api/auth/login** — success, missing fields, wrong password, nonexistent user
- **GET /api/auth/profile** — success, no token, invalid token

### `test_invoices.py` — Invoice Endpoint Tests
- **POST /api/invoices/** — success, missing fields, invalid item, no auth, tax calculation
- **GET /api/invoices/** — empty list, populated list, no auth, user isolation
- **GET /api/invoices/<id>** — success, not found, ownership check
- **PUT /api/invoices/<id>** — update fields, update items, not found, ownership, status change
- **DELETE /api/invoices/<id>** — success, not found, ownership check

### `test_reports.py` — Report Endpoint Tests
- **GET /api/reports/** — empty, populated, no auth
- **POST /api/reports/generate** — success, missing fields, no auth, with invoices
- **GET /api/reports/dashboard** — empty, with data, no auth
- **DELETE /api/reports/<id>** — success, not found, ownership check

### `test_health.py` — Health Check Test
- **GET /api/health** — verifies `status: 'healthy'`

## Adding New Tests

1. Create a new test file following the naming convention `test_*.py`
2. Import `BaseTestCase` from `base` and subclass it
3. Write test methods starting with `test_`
4. The base class handles app creation, DB setup/teardown, and provides auth helpers

## Notes

- All tests should be independent and not rely on external state
- Use descriptive test method names that explain what is being tested
- Include docstrings for test classes and methods
- Mock external dependencies when necessary
- Follow the AAA pattern: Arrange, Act, Assert

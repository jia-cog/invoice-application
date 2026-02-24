# Backend Tests

This directory contains all backend tests for the Invoice Application.

## Structure

```
tests/
├── __init__.py          # Makes tests a Python package
├── README.md           # This file
├── run_tests.py        # Test runner script
├── test_jwt.py         # JWT authentication tests
└── test_invoices.py    # Invoice API route tests
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
```

### Run Tests with Python's unittest module
```bash
# From the backend directory
python3 -m unittest discover tests -v
```

## Test Categories

### JWT Authentication Tests (`test_jwt.py`)
- Token creation with string identities
- Token creation with integer IDs (converted to strings)
- Token decoding and validation
- Token identity consistency
- Required JWT claims verification
- Invalid token handling

### Invoice API Route Tests (`test_invoices.py`)
Comprehensive tests for all 5 invoice API endpoints:

**GET /api/invoices/ (List Invoices)**
- Successfully retrieve invoices for authenticated user
- Return empty list when no invoices exist
- Verify user isolation (users only see their own invoices)
- Reject unauthenticated requests
- Reject invalid JWT tokens

**GET /api/invoices/<id> (Get Single Invoice)**
- Successfully retrieve invoice by ID
- Return 404 for non-existent invoice
- Return 404 for invoice belonging to another user
- Verify invoice includes items in response
- Reject unauthenticated requests

**POST /api/invoices/ (Create Invoice)**
- Successfully create invoice with valid data
- Generate unique invoice number (INV-YYYYMMDD-UUID format)
- Calculate totals correctly (subtotal, tax, total)
- Return 400 for missing required fields (customer_name, due_date, items)
- Return 400 for invalid item data (missing description, quantity, unit_price)
- Default status to 'draft' when not specified
- Reject unauthenticated requests

**PUT /api/invoices/<id> (Update Invoice)**
- Successfully update invoice fields
- Return 404 for non-existent invoice
- Return 404 for invoice belonging to another user
- Update items and recalculate totals
- Support partial updates
- Reject unauthenticated requests

**DELETE /api/invoices/<id> (Delete Invoice)**
- Successfully delete invoice
- Return 404 for non-existent invoice
- Return 404 for invoice belonging to another user
- Cascade delete associated invoice items
- Reject unauthenticated requests

**User Isolation Tests**
- Comprehensive verification that users cannot access, modify, or delete other users' invoices

## Adding New Tests

1. Create a new test file following the naming convention `test_*.py`
2. Import the `unittest` module and create a test class inheriting from `unittest.TestCase`
3. Add the parent directory to the Python path to import backend modules:
   ```python
   import sys
   import os
   sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```
4. Write test methods starting with `test_`
5. Use `setUp()` and `tearDown()` methods for test fixtures if needed

## Example Test Structure

```python
import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from your_module import YourClass

class TestYourFeature(unittest.TestCase):
    def setUp(self):
        # Set up test fixtures
        pass
    
    def tearDown(self):
        # Clean up after tests
        pass
    
    def test_your_feature(self):
        # Your test code here
        self.assertEqual(expected, actual)

if __name__ == "__main__":
    unittest.main()
```

## Notes

- All tests should be independent and not rely on external state
- Use descriptive test method names that explain what is being tested
- Include docstrings for test classes and methods
- Mock external dependencies when necessary
- Follow the AAA pattern: Arrange, Act, Assert

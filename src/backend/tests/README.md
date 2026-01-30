# Backend Tests

This directory contains all backend tests for the Invoice Application.

## Structure

```
tests/
├── __init__.py          # Makes tests a Python package
├── README.md           # This file
├── run_tests.py        # Test runner script
├── test_jwt.py         # JWT authentication tests
└── test_invoices.py    # Invoice API routes tests
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

### Invoice API Routes Tests (`test_invoices.py`)
Tests for all 5 invoice API endpoints with comprehensive coverage:

**GET /api/invoices/ (List Invoices)**
- Successfully retrieve invoices for authenticated user
- Return empty list when no invoices exist
- Verify user isolation (users only see their own invoices)
- Reject requests without authentication

**GET /api/invoices/<id> (Get Single Invoice)**
- Successfully retrieve invoice by ID
- Return 404 for non-existent invoice
- Return 404 for invoice belonging to another user
- Reject requests without authentication

**POST /api/invoices/ (Create Invoice)**
- Successfully create invoice with valid data
- Return 400 for missing required fields (customer_name, due_date, items)
- Return 400 for invalid item data (missing description, quantity, unit_price)
- Verify unique invoice number generation
- Verify invoice/item totals calculation
- Test default and custom status values
- Reject requests without authentication

**PUT /api/invoices/<id> (Update Invoice)**
- Successfully update invoice fields
- Return 404 for non-existent invoice
- Return 404 for invoice belonging to another user
- Verify item updates and totals recalculation
- Test partial field updates
- Reject requests without authentication

**DELETE /api/invoices/<id> (Delete Invoice)**
- Successfully delete invoice
- Return 404 for non-existent invoice
- Return 404 for invoice belonging to another user
- Verify cascade deletion of invoice items
- Reject requests without authentication

**User Isolation & Authentication**
- Comprehensive user isolation testing
- Invalid token handling

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

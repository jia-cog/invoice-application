# Backend Tests

This directory contains all backend tests for the Invoice Application.

## Structure

```
tests/
├── __init__.py          # Makes tests a Python package
├── README.md           # This file
├── run_tests.py        # Test runner script
├── test_jwt.py         # JWT authentication tests
└── test_invoices.py    # Invoice API endpoint tests
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
# Run JWT tests
python3 tests/test_jwt.py

# Run invoice tests
python3 tests/test_invoices.py
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

### Invoice API Tests (`test_invoices.py`)
- **GET /api/invoices/**: List all user invoices
  - Authenticated access with valid JWT
  - Empty list when no invoices exist
  - User isolation (users only see their own invoices)
  - Unauthenticated access returns 401
  
- **GET /api/invoices/<id>**: Get single invoice
  - Success with valid invoice ID
  - 404 for non-existent invoice
  - 404 for another user's invoice
  
- **POST /api/invoices/**: Create new invoice
  - Success with valid data
  - Validation for required fields (customer_name, due_date, items)
  - Validation for item data (description, quantity, unit_price)
  - Invoice number generation and format verification
  - Financial calculations (subtotal, tax, total)
  
- **PUT /api/invoices/<id>**: Update invoice
  - Success updating invoice fields
  - Success updating items with total recalculation
  - 404 for non-existent or another user's invoice
  
- **DELETE /api/invoices/<id>**: Delete invoice
  - Success deleting invoice
  - 404 for non-existent or another user's invoice

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

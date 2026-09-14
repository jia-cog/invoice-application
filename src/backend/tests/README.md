# Backend Tests

This directory contains all backend tests for the Invoice Application.

## Structure

```
tests/
├── __init__.py          # Makes tests a Python package
├── README.md           # This file
├── run_tests.py        # Test runner script
└── test_jwt.py         # JWT authentication tests
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

## Running Tests on Kubernetes

The test harness can also run as a Kubernetes `Job` using the image defined in
`src/backend/Dockerfile.test` and the manifests in `k8s/`.

### 1. Build the test image
```bash
# From the repository root (requirements.txt lives there)
docker build -f src/backend/Dockerfile.test -t invoice-backend-tests:latest .

# For a real cluster, tag and push to your registry, then update the image in
# k8s/test-job.yaml (and set imagePullPolicy: Always):
#   docker tag invoice-backend-tests:latest <registry>/invoice-backend-tests:<tag>
#   docker push <registry>/invoice-backend-tests:<tag>
# For kind:      kind load docker-image invoice-backend-tests:latest
# For minikube:  minikube image load invoice-backend-tests:latest
```

### 2. Apply the config and Job
```bash
kubectl apply -f k8s/test-config.yaml   # ConfigMap (DATABASE_URL) + Secret (JWT_SECRET_KEY, SECRET_KEY)
kubectl apply -f k8s/test-job.yaml
```

### 3. View results
```bash
kubectl wait --for=condition=complete --timeout=120s job/invoice-backend-tests
kubectl logs job/invoice-backend-tests
```

A failing test run exits non-zero, so the Job is marked `Failed`
(`restartPolicy: Never`, `backoffLimit: 1`). Check with
`kubectl get job invoice-backend-tests`.

### Re-running
Jobs are immutable, so delete before re-applying (the Job also auto-cleans
after one hour via `ttlSecondsAfterFinished`):
```bash
kubectl delete job invoice-backend-tests
kubectl apply -f k8s/test-job.yaml
```

## Test Categories

### JWT Authentication Tests (`test_jwt.py`)
- Token creation with string identities
- Token creation with integer IDs (converted to strings)
- Token decoding and validation
- Token identity consistency
- Required JWT claims verification
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

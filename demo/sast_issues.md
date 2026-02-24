# ISSUE 1
The removal of fallback defaults for JWT_SECRET_KEY and SECRET_KEY in src/backend/config.py (lines 8 and 11) breaks the existing tests in src/backend/tests/test_jwt.py because the tests use Config directly without setting environment variables.

To fix this, update src/backend/tests/test_jwt.py to set the required config values in the setUp method. In the setUp method (around line 23-29), after creating the Flask app and before calling from_object(Config), override the secret keys:

    self.app.config['JWT_SECRET_KEY'] = 'test-jwt-secret-key'
    self.app.config['SECRET_KEY'] = 'test-secret-key'

Or alternatively, set the environment variables in setUp and unset them in tearDown:

    os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key'
    os.environ['SECRET_KEY'] = 'test-secret-key'

The first approach (overriding app.config after from_object) is cleaner since it doesn't pollute the environment.

# ISSUE 2
JWT invalid_token_loader leaks debug information

In app.py, the invalid_token_callback returns {'error': 'Invalid token', 'debug': str(error)} in the JSON response. This is pre-existing and not changed by this PR, but it exposes internal error details to API consumers, which could aid attackers in crafting valid tokens or understanding the JWT implementation. This debug leak is worth noting as an inconsistency with the security goals and should be obfuscated.

# Issue 3
In config.py, CORS_ORIGINS includes '*' alongside specific origins ['http://localhost:3000', 'http://localhost:5001', '*']. The wildcard effectively makes the specific origins redundant and allows any origin to make cross-origin requests. This undermines the security hardening goal as it is too permissive. If the application is ever deployed without changing this, it would be a security concern. This should be fixed by removing the wildcard. 


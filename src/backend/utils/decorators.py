"""Reusable view decorators for the backend API."""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def admin_required():
    """Require a valid JWT whose ``is_admin`` claim is truthy.

    Returns a 403 JSON response when the caller is authenticated but not an
    admin. Authentication errors (missing/expired/invalid tokens) bubble up to
    the JWTManager error handlers registered on the app.
    """

    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if not claims.get('is_admin', False):
                return jsonify({'error': 'Admin access required'}), 403
            return fn(*args, **kwargs)

        return decorator

    return wrapper

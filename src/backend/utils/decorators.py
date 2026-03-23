from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt


def admin_required(fn):
    """Decorator that ensures the requesting user has admin privileges.

    Combines JWT authentication with an admin claim check.  If the
    ``is_admin`` claim in the JWT is not ``True``, the request is
    rejected with a 403 response.
    """
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if not claims.get("is_admin"):
            return jsonify({"error": "Admin privileges required"}), 403
        return fn(*args, **kwargs)
    return wrapper

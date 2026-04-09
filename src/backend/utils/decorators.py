from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
import base64
from models import User


def auth_required(fn):
    """Decorator that accepts either JWT Bearer token or Basic Auth."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Basic '):
            # Handle Basic Auth
            try:
                decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = decoded.split(':', 1)
            except Exception:
                return jsonify({'error': 'Invalid Basic Auth header'}), 401

            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
                return jsonify({'error': 'Invalid credentials'}), 401

            g.current_user_id = user.id
        else:
            # Fall back to JWT
            try:
                verify_jwt_in_request()
                g.current_user_id = int(get_jwt_identity())
            except Exception:
                return jsonify({'error': 'Authorization required'}), 401

        return fn(*args, **kwargs)
    return wrapper

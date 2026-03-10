import os
from datetime import timedelta


def _require_env(var_name: str) -> str:
    """Return the value of an environment variable or raise if it is not set."""
    value = os.environ.get(var_name)
    if not value:
        raise ValueError(
            f"Required environment variable '{var_name}' is not set. "
            f"Please set {var_name} before starting the application."
        )
    return value


class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///invoice_app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT configuration
    JWT_SECRET_KEY = _require_env('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Flask configuration
    SECRET_KEY = _require_env('SECRET_KEY')

    # CORS configuration
    CORS_ORIGINS = ['http://localhost:3000','http://localhost:5001', '*']  # React development server

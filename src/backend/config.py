import os
import secrets
from datetime import timedelta


class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///invoice_app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT configuration - must be set via environment variable; no fallback
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Flask configuration - must be set via environment variable; no fallback
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # CORS configuration
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5001', '*']


class TestConfig(Config):
    """Configuration for testing. Uses ephemeral random secrets."""

    TESTING = True
    JWT_SECRET_KEY = secrets.token_hex(32)
    SECRET_KEY = secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

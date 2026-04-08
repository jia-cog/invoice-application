import os
from datetime import timedelta


class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///invoice_app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT configuration — no hardcoded fallback; must be set via environment variable
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Flask configuration — no hardcoded fallback; must be set via environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # CORS configuration
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5001', '*']  # React development server

    @staticmethod
    def validate():
        """Validate that all required environment variables are set."""
        missing = []
        if not os.environ.get('JWT_SECRET_KEY'):
            missing.append('JWT_SECRET_KEY')
        if not os.environ.get('SECRET_KEY'):
            missing.append('SECRET_KEY')
        if missing:
            raise ValueError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Set them before starting the application. "
                "You can generate a secure value with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

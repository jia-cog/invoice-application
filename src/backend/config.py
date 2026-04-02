import os
from datetime import timedelta

class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///invoice_app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT configuration — no hardcoded fallbacks; must be set via environment variables
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Flask configuration — no hardcoded fallbacks; must be set via environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # CORS configuration
    CORS_ORIGINS = ['http://localhost:3000','http://localhost:5001', '*']  # React development server


def validate_config():
    """Validate that all required environment variables are set.
    
    Raises ValueError if any required secret keys are missing.
    """
    missing = []
    if not Config.JWT_SECRET_KEY:
        missing.append('JWT_SECRET_KEY')
    if not Config.SECRET_KEY:
        missing.append('SECRET_KEY')
    if missing:
        raise ValueError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "These must be set before starting the application. "
            "Generate secure values with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database configuration
    # Default to PostgreSQL; fall back to SQLite for backwards compatibility
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://invoice_user:invoice_pass@localhost:5432/invoice_app'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection pool settings (applicable to PostgreSQL)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 20,
    }
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'your-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # CORS configuration
    CORS_ORIGINS = ['http://localhost:3000','http://localhost:5001', '*']  # React development server

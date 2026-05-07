#!/usr/bin/env python3
"""
Database initialization script for the Invoice Application.
Run this script to create the database tables.
"""

from app import create_app
from models import db

def init_database():
    """Initialize the database with all tables."""
    app = create_app()
    
    with app.app_context():
        # Drop all tables (use with caution in production)
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        print("Database initialized successfully!")
        print("Tables created:")
        print("- users")
        print("- invoices")
        print("- invoice_items")
        print("- request_logs")
        print("- reports")

if __name__ == '__main__':
    init_database()

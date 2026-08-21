#!/usr/bin/env python3
"""
Database initialization script for the Invoice Application.

Applies all Alembic migrations to bring the configured database up to date.
Equivalent to `flask db upgrade`.
"""

from flask_migrate import upgrade

from app import create_app


def init_database():
    """Apply all pending migrations."""
    app = create_app()

    with app.app_context():
        upgrade()
        print("Database is up to date!")


if __name__ == '__main__':
    init_database()

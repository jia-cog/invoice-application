#!/usr/bin/env python3
"""
Migration script to add is_admin column to the user table.
Run this script to upgrade an existing database without losing data.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from models import db


def migrate():
    app = create_app()

    with app.app_context():
        with db.engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(
                db.text("PRAGMA table_info(user)")
            )
            columns = [row[1] for row in result]

            if 'is_admin' not in columns:
                conn.execute(
                    db.text(
                        "ALTER TABLE user ADD COLUMN is_admin BOOLEAN "
                        "NOT NULL DEFAULT 0"
                    )
                )
                conn.commit()
                print("Added is_admin column to user table.")
            else:
                print("is_admin column already exists. No changes needed.")


if __name__ == '__main__':
    migrate()

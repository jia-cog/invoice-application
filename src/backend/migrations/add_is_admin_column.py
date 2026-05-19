"""Migration script to add is_admin column to the User table."""
import sqlite3
import os
import sys


def migrate():
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "instance",
        "invoices.db",
    )
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Skipping migration — "
              "the column will be created automatically by db.create_all().")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if the column already exists
    cursor.execute("PRAGMA table_info(user)")
    columns = [row[1] for row in cursor.fetchall()]

    if "is_admin" in columns:
        print("Column 'is_admin' already exists. Nothing to do.")
    else:
        cursor.execute(
            "ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"
        )
        conn.commit()
        print("Successfully added 'is_admin' column to the User table.")

    conn.close()


if __name__ == "__main__":
    migrate()

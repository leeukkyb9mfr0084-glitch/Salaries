import sqlite3
import os

DB_FILE = "reporter/data/kranos_data.db"


def create_database(db_name: str):
    """
    Connects to an SQLite database and creates the necessary tables if they don't exist.
    Args:
        db_name (str): The name of the database file (e.g., 'kranos_data.db' or ':memory:').
    """
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Create members table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            email TEXT,
    join_date TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1
        );
        """
        )

        # Create pt_memberships table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS pt_memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            purchase_date TEXT,
            amount_paid REAL,
            sessions_total INTEGER,
            sessions_remaining INTEGER,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );
        """
        )

        # Create group_class_memberships table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS group_class_memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            plan_id INTEGER,
            start_date TEXT,
            end_date TEXT,
            amount_paid REAL,
            purchase_date TEXT,
            membership_type TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
            FOREIGN KEY (plan_id) REFERENCES group_plans(id) ON DELETE RESTRICT
        );
        """
        )

        # Create group_plans table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS group_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration_days INTEGER NOT NULL,
            default_amount REAL NOT NULL,
            display_name TEXT UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT 1
        );
        """
        )
        conn.commit()
    except sqlite3.Error as e:
        if conn: # If connection was established before error, close it
            conn.close()
        return None # Return None if an error occurred
    return conn


def initialize_database():
    """
    Initializes the database: creates the directory, database, tables, and seeds initial data.
    """
    # Get the directory path from DB_FILE
    data_dir = os.path.dirname(DB_FILE)

    # If the directory doesn't exist, create it
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
        except OSError as e:
            return  # Stop if directory creation fails

    # Call create_database(DB_FILE)
    # This function already prints success or error messages.
    # It also handles its own connection opening and closing for file-based DBs.
    create_database(DB_FILE)

    # Seeding was removed, so no need to establish a separate connection here.

if __name__ == "__main__":
    initialize_database()

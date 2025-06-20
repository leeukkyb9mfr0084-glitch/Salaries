import os
import sqlite3

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
            FOREIGN KEY (plan_id) REFERENCES group_plans(id) ON DELETE RESTRICT,
            UNIQUE (member_id, plan_id, start_date)
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
        if conn:  # If connection was established before error, close it
            conn.close()
        return None  # Return None if an error occurred
    return conn


if __name__ == "__main__":
    initialize_database()


def initialize_database():
    conn = sqlite3.connect("kranos_data.db")
    cursor = conn.cursor()

    # Create Members table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        join_date TEXT,
        is_active BOOLEAN DEFAULT TRUE
    )
    """
    )

    # Create Group Plans table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS group_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        display_name TEXT,
        default_amount REAL,
        duration_days INTEGER,
        is_active BOOLEAN DEFAULT TRUE
    )
    """
    )

    # Create Group Class Memberships table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS group_class_memberships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        start_date TEXT,
        end_date TEXT,
        purchase_date TEXT,
        membership_type TEXT,  -- e.g., 'new', 'renewal'
        amount_paid REAL,
        is_active BOOLEAN DEFAULT TRUE, -- Added based on model
        FOREIGN KEY (member_id) REFERENCES members (id),
        FOREIGN KEY (plan_id) REFERENCES group_plans (id)
    )
    """
    )

    # Create PT Memberships table
    # Assuming 'membership_id' in PTMembershipView is the primary key for this table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS pt_memberships (
        membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        purchase_date TEXT,
        sessions_total INTEGER,
        sessions_remaining INTEGER,
        amount_paid REAL,
        FOREIGN KEY (member_id) REFERENCES members (id)
    )
    """
    )

    conn.commit()
    conn.close()

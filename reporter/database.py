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
            phone TEXT UNIQUE,
            email TEXT,
    join_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
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
            notes TEXT,
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
            membership_type TEXT, -- 'New' or 'Renewal'
            FOREIGN KEY (member_id) REFERENCES members(id),
            FOREIGN KEY (plan_id) REFERENCES group_plans(id),
            UNIQUE(member_id, plan_id, start_date)
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
        # print(f"Error creating database or tables: {e}") # Removed
        if conn: # If connection was established before error, close it
            conn.close()
        return None # Return None if an error occurred
    # If successful, return the connection object
    # The caller will be responsible for closing the connection.
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
            # print(f"Created directory: {data_dir}") # Removed
        except OSError as e:
            # print(f"Error creating directory {data_dir}: {e}") # Removed
            return  # Stop if directory creation fails

    # Call create_database(DB_FILE)
    # This function already prints success or error messages.
    # It also handles its own connection opening and closing for file-based DBs.
    create_database(DB_FILE)

    # Establish a new connection to DB_FILE for seeding
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        # If the connection is successful, call seed_initial_plans(conn)
        # seed_initial_plans(conn) # Call removed
        # print(f"Database initialized at {DB_FILE}.") # Removed
    except sqlite3.Error as e:
        pass
        # print(f"Error during database initialization: {e}") # Removed
    finally:
        # Ensure the connection is closed in a finally block
        if conn:
            conn.close()


if __name__ == "__main__":
    initialize_database()
    # print("Database setup complete.") # Removed

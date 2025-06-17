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
    is_active INTEGER NOT NULL DEFAULT 1 -- << ADD THIS COLUMN
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
            sessions_purchased INTEGER,
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
        print(f"Database '{db_name}' created and tables ensured.")
    except sqlite3.Error as e:
        print(f"Error creating database or tables: {e}")
        if conn: # If connection was established before error, close it
            conn.close()
        return None # Return None if an error occurred
    # If successful, return the connection object
    # The caller will be responsible for closing the connection.
    return conn


def seed_initial_plans(conn: sqlite3.Connection):
    """
    Inserts initial plans into the group_plans table.
    Args:
        conn (sqlite3.Connection): The database connection object.
    """
    # plans_to_seed list and the loop for inserting them have been removed.
    try:
        # The seeding logic has been removed as per requirements.
        # Initial plans are now expected to be handled by migration scripts or other setup processes.
        print("Initial plan seeding in seed_initial_plans is disabled. Plans should be migrated via ETL process.")
    except sqlite3.Error as e:
        # This error block might be less relevant now but kept for structural integrity
        # or if other non-seeding operations were to be added here later.
        print(f"Error in (now mostly empty) seed_initial_plans function: {e}")


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
            print(f"Created directory: {data_dir}")
        except OSError as e:
            print(f"Error creating directory {data_dir}: {e}")
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
        seed_initial_plans(conn)
        print(f"Database initialized and seeded at {DB_FILE}.")
    except sqlite3.Error as e:
        print(f"Error during database initialization or seeding: {e}")
    finally:
        # Ensure the connection is closed in a finally block
        if conn:
            conn.close()


if __name__ == "__main__":
    initialize_database()
    print("Database setup complete.")

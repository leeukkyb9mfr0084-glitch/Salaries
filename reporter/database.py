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
            is_active BOOLEAN,
            FOREIGN KEY (member_id) REFERENCES members(id),
            FOREIGN KEY (plan_id) REFERENCES group_plans(id)
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
    finally:
        if conn and db_name != ":memory:":  # Only close if it's a file-based DB
            conn.close()
        elif db_name == ":memory:":
            return conn  # Return the connection for in-memory DBs
    return None  # Explicitly return None for file-based DBs after closing


def seed_initial_plans(conn: sqlite3.Connection):
    """
    Inserts initial plans into the group_plans table.
    Args:
        conn (sqlite3.Connection): The database connection object.
    """
    plans_to_seed = [
        ("Monthly - Unrestricted", 30, 100.0, "Monthly Unrestricted"),
        ("3 Months - Unrestricted", 90, 270.0, "3 Months Unrestricted"),
        ("Annual - Unrestricted", 365, 1000.0, "Annual Unrestricted"),
    ]
    try:
        cursor = conn.cursor()
        for (
            name,
            duration_days,
            default_amount,
            display_name,
        ) in plans_to_seed:
            cursor.execute(
                "INSERT OR IGNORE INTO group_plans (name, duration_days, default_amount, display_name) VALUES (?, ?, ?, ?)",
                (name, duration_days, default_amount, display_name),
            )
        conn.commit()
        print(f"Seeded {len(plans_to_seed)} initial plans.")
    except sqlite3.Error as e:
        print(f"Error seeding initial plans: {e}")


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

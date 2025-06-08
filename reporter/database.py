import sqlite3
import os

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
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            phone TEXT UNIQUE,
            join_date TEXT
        );
        """)

        # Create plans table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_name TEXT NOT NULL UNIQUE,
            duration_days INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );
        """)

        # Create group_memberships table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_memberships (
            membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            payment_date TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            amount_paid REAL NOT NULL,
            payment_method TEXT,
            FOREIGN KEY (member_id) REFERENCES members (member_id),
            FOREIGN KEY (plan_id) REFERENCES plans (plan_id)
        );
        """)

        # Create pt_bookings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pt_bookings (
            pt_booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            sessions INTEGER NOT NULL,
            amount_paid REAL NOT NULL,
            FOREIGN KEY (member_id) REFERENCES members (member_id)
        );
        """)
        conn.commit()
        print(f"Database '{db_name}' created and tables ensured.")
    except sqlite3.Error as e:
        print(f"Error creating database or tables: {e}")
    finally:
        if conn and db_name != ':memory:': # Only close if it's a file-based DB
            conn.close()
        elif db_name == ':memory:':
            return conn # Return the connection for in-memory DBs
    return None # Explicitly return None for file-based DBs after closing

def seed_initial_plans(conn: sqlite3.Connection):
    """
    Inserts initial plans into the plans table.
    Args:
        conn (sqlite3.Connection): The database connection object.
    """
    plans_to_seed = [
        ("Monthly - Unrestricted", 30, True),
        ("3 Months - Unrestricted", 90, True),
        ("Annual - Unrestricted", 365, True)
    ]
    try:
        cursor = conn.cursor()
        for plan_name, duration_days, is_active in plans_to_seed:
            cursor.execute("INSERT OR IGNORE INTO plans (plan_name, duration_days, is_active) VALUES (?, ?, ?)", (plan_name, duration_days, is_active))
        conn.commit()
        print(f"Seeded {len(plans_to_seed)} initial plans.")
    except sqlite3.Error as e:
        print(f"Error seeding initial plans: {e}")

if __name__ == '__main__':
    DB_FILE = 'reporter/data/kranos_data.db'

    # Create the data directory if it doesn't exist
    data_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created directory: {data_dir}")

    # For file-based DB, create_database handles connection and closure.
    create_database(DB_FILE)

    # Re-open connection for seeding, specific to the main block's operation
    main_conn = None
    try:
        main_conn = sqlite3.connect(DB_FILE)
        seed_initial_plans(main_conn)
    except sqlite3.Error as e:
        print(f"Error connecting to DB or seeding plans in main block: {e}")
    finally:
        if main_conn:
            main_conn.close()

    print("Database setup complete.")

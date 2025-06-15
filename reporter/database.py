import sqlite3
import os

DB_FILE = 'reporter/data/kranos_data.db'

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
    join_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 -- << ADD THIS COLUMN
        );
        """)

        # Create plans table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            price INTEGER,
            type TEXT,
            UNIQUE(name, duration, type)
        );
        """)

        # Create transactions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            plan_id INTEGER,
            start_date TEXT NOT NULL,
            end_date TEXT, -- Added missing column
            transaction_date TEXT,
            amount REAL,
            payment_method TEXT,
            sessions INTEGER,
            description TEXT,
            FOREIGN KEY (member_id) REFERENCES members (member_id),
            FOREIGN KEY (plan_id) REFERENCES plans (plan_id)
        );
        """)

        # Create monthly_book_status table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_book_status (
            month_key TEXT PRIMARY KEY, -- e.g., "2025-06"
            status TEXT NOT NULL CHECK(status IN ('open', 'closed')),
            closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        ("Monthly - Unrestricted", 30, 100, "Standard"), # Example price and type
        ("3 Months - Unrestricted", 90, 270, "Standard"), # Example price and type
        ("Annual - Unrestricted", 365, 1000, "Standard") # Example price and type
    ]
    try:
        cursor = conn.cursor()
        for plan_name, duration_days, price, type_text in plans_to_seed: # Added price and type
            cursor.execute("INSERT OR IGNORE INTO plans (name, duration, price, type) VALUES (?, ?, ?, ?)", (plan_name, duration_days, price, type_text)) # Updated column names and added new ones
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
            return # Stop if directory creation fails

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

if __name__ == '__main__':
    initialize_database()
    print("Database setup complete.")

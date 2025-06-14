import sqlite3
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "kranos_gym.db")

def init_db():
    """Initializes the database and creates tables with the corrected schema."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Drop tables if they exist to ensure a fresh schema
        # (This is useful for re-initialization)
        cursor.execute("DROP TABLE IF EXISTS members")
        cursor.execute("DROP TABLE IF EXISTS plans")
        cursor.execute("DROP TABLE IF EXISTS transactions")
        cursor.execute("DROP TABLE IF EXISTS book_closing")

        # Create members table
        cursor.execute("""
            CREATE TABLE members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                join_date TEXT,
                phone TEXT,
                status TEXT CHECK(status IN ('active', 'inactive'))
            )
        """)
        # Removed: email TEXT UNIQUE NOT NULL - Not in new spec
        # Removed: membership_plan_id INTEGER - Not in new spec (handled by transactions)
        # Removed: is_active BOOLEAN DEFAULT TRUE - Replaced by status TEXT

        # Create plans table
        cursor.execute("""
            CREATE TABLE plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                price INTEGER NOT NULL,
                duration_days INTEGER NOT NULL,
                type TEXT CHECK(type IN ('GC', 'PT'))
            )
        """)
        # Removed: description TEXT - Not in new spec
        # Changed: price REAL to price INTEGER

        # Create transactions table
        cursor.execute("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER,
                plan_id INTEGER,
                transaction_date TEXT NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('renewal', 'payment', 'expense', 'new_subscription')),
                description TEXT,
                start_date TEXT,
                end_date TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id),
                FOREIGN KEY (plan_id) REFERENCES plans(id)
            )
        """)
        # Removed: payment_method TEXT - Not in new spec
        # Added: type TEXT (more specific check constraint)
        # Added: description TEXT
        # Added: start_date TEXT
        # Added: end_date TEXT
        # Ensured transaction_date and amount are NOT NULL as they are essential.
        # plan_id can be NULL as per instruction "can be NULL"

        # Create book_closing table
        cursor.execute("""
            CREATE TABLE book_closing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month INTEGER NOT NULL CHECK(month >= 1 AND month <= 12),
                year INTEGER NOT NULL,
                closing_date TEXT NOT NULL UNIQUE
            )
        """)
        # Removed: total_revenue REAL NOT NULL - Not in new spec
        # Removed: total_expenses REAL DEFAULT 0 - Not in new spec
        # Removed: net_profit REAL NOT NULL - Not in new spec
        # Removed: closed_by TEXT - Not in new spec
        # Added: month, year with checks. closing_date made UNIQUE and NOT NULL.

        conn.commit()
        print("Database schema updated and initialized successfully.")
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "init_db":
        # Optionally, delete old DB file before initializing
        # if os.path.exists(DB_PATH):
        #     os.remove(DB_PATH)
        #     print(f"Old database file '{DB_PATH}' removed.")
        init_db()
    else:
        print("Usage: python -m kranos_reporter.db.database init_db")

# Corrected migrate_data.py script content
# Placeholder for the actual corrected script

import sqlite3
import os

# Define the path to the new database, ensuring it's in the 'reporter/data' directory
NEW_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'kranos_data_migrated.db')
OLD_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'kranos_data_old.db') # Assuming old DB is also in data

def connect_db(db_path):
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Access columns by name
    return conn

def create_new_schema(conn):
    """Creates the new schema in the migrated database."""
    cursor = conn.cursor()
    # Drop tables if they exist to ensure a fresh start (optional, for testing)
    cursor.execute("DROP TABLE IF EXISTS pt_bookings;")
    cursor.execute("DROP TABLE IF EXISTS group_memberships;")
    cursor.execute("DROP TABLE IF EXISTS plans;")
    cursor.execute("DROP TABLE IF EXISTS members;")

    # Create members table (as per new schema)
    cursor.execute("""
    CREATE TABLE members (
        member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        phone TEXT UNIQUE,
        join_date TEXT -- Will be populated from first activity
    );
    """)

    # Create plans table (as per new schema)
    cursor.execute("""
    CREATE TABLE plans (
        plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_name TEXT NOT NULL UNIQUE,
        duration_days INTEGER NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE -- New column
    );
    """)

    # Create group_memberships table (as per new schema)
    cursor.execute("""
    CREATE TABLE group_memberships (
        membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        payment_date TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL, -- Calculated based on plan duration
        amount_paid REAL NOT NULL,
        payment_method TEXT,
        FOREIGN KEY (member_id) REFERENCES members (member_id),
        FOREIGN KEY (plan_id) REFERENCES plans (plan_id)
    );
    """)

    # Create pt_bookings table (as per new schema)
    cursor.execute("""
    CREATE TABLE pt_bookings (
        pt_booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        start_date TEXT NOT NULL, -- Renamed from booking_date
        sessions INTEGER NOT NULL,
        amount_paid REAL NOT NULL,
        FOREIGN KEY (member_id) REFERENCES members (member_id)
    );
    """)
    conn.commit()
    print("New database schema created successfully.")

def migrate_members(old_conn, new_conn):
    """Migrates members from the old database to the new one."""
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    old_cursor.execute("SELECT client_id, client_name, phone, join_date FROM clients")
    members_migrated = 0
    for row in old_cursor.fetchall():
        try:
            # Insert into new members table, join_date can be directly migrated if available and correct
            # If join_date was not reliably set, it might be better to set it based on first activity
            new_cursor.execute("""
                INSERT INTO members (member_id, client_name, phone, join_date)
                VALUES (?, ?, ?, ?)
            """, (row['client_id'], row['client_name'], row['phone'], row['join_date']))
            members_migrated += 1
        except sqlite3.IntegrityError as e:
            print(f"Skipping member due to integrity error (e.g., duplicate phone): {row['client_name']} - {e}")
        except Exception as e:
            print(f"An error occurred while migrating member {row['client_name']}: {e}")
    new_conn.commit()
    print(f"Migrated {members_migrated} members.")

def migrate_plans(old_conn, new_conn):
    """Migrates plans from the old database to the new one, adding is_active."""
    # In the old schema, plans did not have an 'is_active' field.
    # We will assume all migrated plans are initially active.
    # Or, define specific logic if some old plans should be inactive.
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    old_cursor.execute("SELECT plan_id, plan_name, duration FROM plans") # Assuming old table was 'plans' with 'duration'
    plans_migrated = 0
    for row in old_cursor.fetchall():
        try:
            new_cursor.execute("""
                INSERT INTO plans (plan_id, plan_name, duration_days, is_active)
                VALUES (?, ?, ?, ?)
            """, (row['plan_id'], row['plan_name'], row['duration'], True)) # Default is_active to True
            plans_migrated += 1
        except sqlite3.IntegrityError as e:
            print(f"Skipping plan due to integrity error: {row['plan_name']} - {e}")
        except Exception as e:
            print(f"An error occurred while migrating plan {row['plan_name']}: {e}")

    # Seed default plans if they are not coming from the old DB or if specific IDs are needed
    # This is an example, adjust as necessary.
    default_plans = [
        ("Monthly - Unrestricted", 30, True),
        ("3 Months - Unrestricted", 90, True),
        ("Annual - Unrestricted", 365, True)
    ]
    for name, duration, active in default_plans:
        try:
            new_cursor.execute("INSERT OR IGNORE INTO plans (plan_name, duration_days, is_active) VALUES (?, ?, ?)",
                               (name, duration, active))
        except Exception as e:
            print(f"Error seeding plan {name}: {e}")

    new_conn.commit()
    print(f"Migrated {plans_migrated} plans and ensured default plans exist.")


def migrate_group_memberships(old_conn, new_conn):
    """Migrates group memberships, calculating end_date."""
    from datetime import datetime, timedelta # Ensure datetime is available

    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # Fetch all plans from the new DB to get duration_days for end_date calculation
    plan_durations = {row['plan_id']: row['duration_days'] for row in new_cursor.execute("SELECT plan_id, duration_days FROM plans").fetchall()}

    old_cursor.execute("""
        SELECT client_id, plan_id, payment_date, start_date, amount_paid, payment_method
        FROM client_plans
    """) # Assuming old table was 'client_plans'
    memberships_migrated = 0
    for row in old_cursor.fetchall():
        try:
            plan_duration_days = plan_durations.get(row['plan_id'])
            if not plan_duration_days:
                print(f"Warning: Plan ID {row['plan_id']} not found in new plans table. Skipping membership for client {row['client_id']}.")
                continue

            start_date_obj = datetime.strptime(row['start_date'], '%Y-%m-%d')
            end_date_obj = start_date_obj + timedelta(days=plan_duration_days)
            end_date_str = end_date_obj.strftime('%Y-%m-%d')

            new_cursor.execute("""
                INSERT INTO group_memberships (member_id, plan_id, payment_date, start_date, end_date, amount_paid, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (row['client_id'], row['plan_id'], row['payment_date'], row['start_date'], end_date_str, row['amount_paid'], row['payment_method']))
            memberships_migrated += 1
        except Exception as e:
            print(f"An error occurred while migrating group membership for client {row['client_id']}: {e}")
    new_conn.commit()
    print(f"Migrated {memberships_migrated} group memberships.")

def migrate_pt_bookings(old_conn, new_conn):
    """Migrates PT bookings from the old database to the new one."""
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # Assuming old table was 'pt_bookings' and had 'client_id', 'booking_date', 'sessions', 'amount_paid'
    old_cursor.execute("SELECT client_id, booking_date, sessions, amount_paid FROM pt_sessions")
    bookings_migrated = 0
    for row in old_cursor.fetchall():
        try:
            # Renaming 'booking_date' to 'start_date' for the new schema
            new_cursor.execute("""
                INSERT INTO pt_bookings (member_id, start_date, sessions, amount_paid)
                VALUES (?, ?, ?, ?)
            """, (row['client_id'], row['booking_date'], row['sessions'], row['amount_paid']))
            bookings_migrated += 1
        except Exception as e:
            print(f"An error occurred while migrating PT booking for client {row['client_id']}: {e}")
    new_conn.commit()
    print(f"Migrated {bookings_migrated} PT bookings.")


def main():
    """Main function to orchestrate the database migration."""
    # Ensure the 'data' directory exists
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created directory: {data_dir}")

    # --- Safety Check: Backup old database before proceeding ---
    # This is a placeholder for a real backup mechanism.
    # For example, copy OLD_DB_PATH to OLD_DB_PATH + ".backup"
    if os.path.exists(OLD_DB_PATH):
        backup_path = OLD_DB_PATH + f".backup_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            import shutil
            shutil.copy2(OLD_DB_PATH, backup_path)
            print(f"Backup of old database created at {backup_path}")
        except Exception as e:
            print(f"Error creating backup: {e}. Migration will not proceed.")
            return
    else:
        print(f"Old database at {OLD_DB_PATH} not found. Cannot proceed with migration.")
        # Depending on the use case, you might want to allow proceeding if old DB is not found,
        # e.g., to set up a fresh new DB. For this script, we assume migration is needed.
        # Create a dummy old database for testing if it doesn't exist
        print(f"Creating a dummy old database for testing purposes: {OLD_DB_PATH}")
        old_conn_setup = connect_db(OLD_DB_PATH)
        setup_dummy_old_db(old_conn_setup)
        old_conn_setup.close()
        # return # Exit if old DB not found and not creating a dummy one.


    # Connect to the (potentially dummy) old and new databases
    old_conn = None
    new_conn = None
    try:
        old_conn = connect_db(OLD_DB_PATH)
        print(f"Connected to old database: {OLD_DB_PATH}")

        # Remove existing new database file to start fresh (optional)
        if os.path.exists(NEW_DB_PATH):
            os.remove(NEW_DB_PATH)
            print(f"Removed existing new database: {NEW_DB_PATH}")

        new_conn = connect_db(NEW_DB_PATH)
        print(f"Connected to new database: {NEW_DB_PATH}")

        # Create the schema in the new database
        create_new_schema(new_conn)

        # Perform data migration
        print("\nStarting data migration...")
        migrate_members(old_conn, new_conn)
        migrate_plans(old_conn, new_conn) # Migrates and seeds default plans
        migrate_group_memberships(old_conn, new_conn)
        migrate_pt_bookings(old_conn, new_conn)

        print("\nData migration completed successfully!")

    except sqlite3.Error as e:
        print(f"An SQLite error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if old_conn:
            old_conn.close()
        if new_conn:
            new_conn.close()

def setup_dummy_old_db(conn):
    """Creates and populates a dummy old database for testing the migration script."""
    cursor = conn.cursor()
    print("Setting up dummy old database...")

    # Old clients table
    cursor.execute("DROP TABLE IF EXISTS clients;")
    cursor.execute("""
    CREATE TABLE clients (
        client_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        phone TEXT UNIQUE,
        join_date TEXT
    );""")
    clients_data = [
        (1, 'John Doe', '1234567890', '2023-01-15'),
        (2, 'Jane Smith', '0987654321', '2023-02-20'),
        (3, 'Alice Brown', '1122334455', '2023-03-10')
    ]
    cursor.executemany("INSERT INTO clients VALUES (?, ?, ?, ?)", clients_data)

    # Old plans table
    cursor.execute("DROP TABLE IF EXISTS plans;")
    cursor.execute("""
    CREATE TABLE plans (
        plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_name TEXT NOT NULL UNIQUE,
        duration INTEGER NOT NULL -- Assuming duration was just integer days
    );""")
    plans_data = [
        (1, 'Old Monthly', 30),
        (2, 'Old Quarterly', 90)
    ]
    cursor.executemany("INSERT INTO plans VALUES (?, ?, ?)", plans_data)

    # Old client_plans (group memberships) table
    cursor.execute("DROP TABLE IF EXISTS client_plans;")
    cursor.execute("""
    CREATE TABLE client_plans (
        client_plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        plan_id INTEGER,
        payment_date TEXT,
        start_date TEXT,
        amount_paid REAL,
        payment_method TEXT,
        FOREIGN KEY (client_id) REFERENCES clients (client_id),
        FOREIGN KEY (plan_id) REFERENCES plans (plan_id)
    );""")
    client_plans_data = [
        # client_id, plan_id, payment_date, start_date, amount_paid, payment_method
        (1, 1, '2023-01-15', '2023-01-15', 50.00, 'Credit Card'),
        (2, 2, '2023-02-20', '2023-02-20', 135.00, 'Cash')
    ]
    # Explicitly list columns to avoid issues with autoincrementing primary key
    cursor.executemany("""
        INSERT INTO client_plans (client_id, plan_id, payment_date, start_date, amount_paid, payment_method)
        VALUES (?, ?, ?, ?, ?, ?)
    """, client_plans_data)

    # Old pt_sessions (PT bookings) table
    cursor.execute("DROP TABLE IF EXISTS pt_sessions;")
    cursor.execute("""
    CREATE TABLE pt_sessions (
        pt_session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        booking_date TEXT, -- Old column name
        sessions INTEGER,
        amount_paid REAL,
        FOREIGN KEY (client_id) REFERENCES clients (client_id)
    );""")
    pt_sessions_data = [
        # client_id, booking_date, sessions, amount_paid
        (1, '2023-01-20', 10, 300.00),
        (3, '2023-03-15', 5, 150.00) # Corrected client_id from 2 to 3 to match members data
    ]
    # Explicitly list columns
    cursor.executemany("""
        INSERT INTO pt_sessions (client_id, booking_date, sessions, amount_paid)
        VALUES (?, ?, ?, ?)
    """, pt_sessions_data)

    conn.commit()
    print("Dummy old database setup complete.")


if __name__ == '__main__':
    from datetime import datetime # Ensure datetime is available for backup naming
    main()

import sqlite3
from datetime import datetime, timedelta, date
import os

# Assuming this script is in kranos_reporter/db/
# and database.py (for DB_PATH) is in the same directory.
try:
    from .database import DB_PATH
except ImportError:
    # Fallback for direct execution if the relative import fails
    # This assumes kranos_reporter is in PYTHONPATH or current dir is kranos_reporter
    try:
        from database import DB_PATH
    except ImportError:
        # Absolute fallback if running from within kranos_reporter/db directly
        DB_DIR = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(DB_DIR, "kranos_gym.db")


def execute_query(conn, query, params=None):
    """Helper to execute a query."""
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error: {e} for query: {query} with params: {params}")
        conn.rollback()  # Rollback on error
        return None


def add_plan(conn, name, price, duration_days, type):
    print(f"Adding plan: {name}")
    return execute_query(
        conn,
        "INSERT INTO plans (name, price, duration_days, type) VALUES (?, ?, ?, ?)",
        (name, price, duration_days, type),
    )


def add_member(conn, name, join_date, phone, status):
    print(f"Adding member: {name}")
    return execute_query(
        conn,
        "INSERT INTO members (name, join_date, phone, status) VALUES (?, ?, ?, ?)",
        (name, join_date, phone, status),
    )


def add_transaction(
    conn,
    member_id,
    plan_id,
    transaction_date,
    amount,
    type,
    description,
    start_date,
    end_date,
):
    print(
        f"Adding transaction for member_id {member_id}: type {type}, end_date {end_date}"
    )
    return execute_query(
        conn,
        """INSERT INTO transactions
           (member_id, plan_id, transaction_date, amount, type, description, start_date, end_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            member_id,
            plan_id,
            transaction_date,
            amount,
            type,
            description,
            start_date,
            end_date,
        ),
    )


def seed():
    """Seeds the database with sample data."""
    if not os.path.exists(DB_PATH):
        print(
            f"Database file not found at {DB_PATH}. Please initialize it first using kranos_reporter.db.database init_db."
        )
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        print(f"Connected to database: {DB_PATH}")

        # Clean slate for relevant tables before seeding (optional, but good for repeatable tests)
        execute_query(conn, "DELETE FROM transactions")
        execute_query(conn, "DELETE FROM members")
        execute_query(conn, "DELETE FROM plans")
        print("Cleared existing data from transactions, members, and plans tables.")

        # 1. Sample Plans
        plan1_id = add_plan(conn, "Monthly GC", 5000, 30, "GC")
        plan2_id = add_plan(conn, "3 Month PT", 15000, 90, "PT")
        plan3_id = add_plan(conn, "Annual Gold", 50000, 365, "GC")
        plan4_id = add_plan(
            conn, "Single Session PT", 2000, 1, "PT"
        )  # For non-renewal type

        if not all([plan1_id, plan2_id, plan3_id, plan4_id]):
            print("Failed to add all plans. Aborting seed.")
            return

        # 2. Sample Members
        member1_id = add_member(
            conn,
            "Alice Active",
            date.today() - timedelta(days=100),
            "555-0101",
            "active",
        )
        member2_id = add_member(
            conn, "Bob Busy", date.today() - timedelta(days=200), "555-0102", "active"
        )
        member3_id = add_member(
            conn,
            "Charlie Current",
            date.today() - timedelta(days=50),
            "555-0103",
            "active",
        )
        member4_id = add_member(
            conn,
            "David Done",
            date.today() - timedelta(days=300),
            "555-0104",
            "inactive",
        )  # Inactive member
        member5_id = add_member(
            conn, "Eve Eager", date.today() - timedelta(days=10), "555-0105", "active"
        )  # For non-renewal transaction

        if not all([member1_id, member2_id, member3_id, member4_id, member5_id]):
            print("Failed to add all members. Aborting seed.")
            return

        # 3. Sample Renewal Transactions
        today = date.today()

        # Scenario 1: Plan ends in 10 days (Alice)
        # Get actual duration for plan1_id
        cursor = conn.cursor()
        cursor.execute(
            "SELECT duration_days, price FROM plans WHERE id = ?", (plan1_id,)
        )
        plan1_data = cursor.fetchone()
        plan1_duration_days, plan1_price = (
            plan1_data if plan1_data else (30, 5000)
        )  # Default if plan lookup fails

        start_s1 = today - timedelta(days=plan1_duration_days) + timedelta(days=10)
        end_s1 = start_s1 + timedelta(
            days=plan1_duration_days
        )  # This is today + 10 days
        add_transaction(
            conn,
            member1_id,
            plan1_id,
            start_s1.isoformat(),
            plan1_price,
            "renewal",
            "Monthly GC Renewal",
            start_s1.isoformat(),
            end_s1.isoformat(),
        )

        # Scenario 2: Plan ends in 25 days (Bob)
        cursor.execute(
            "SELECT duration_days, price FROM plans WHERE id = ?", (plan2_id,)
        )
        plan2_data = cursor.fetchone()
        plan2_duration_days, plan2_price = plan2_data if plan2_data else (90, 15000)

        start_s2 = today - timedelta(days=plan2_duration_days) + timedelta(days=25)
        end_s2 = start_s2 + timedelta(
            days=plan2_duration_days
        )  # This is today + 25 days
        add_transaction(
            conn,
            member2_id,
            plan2_id,
            start_s2.isoformat(),
            plan2_price,
            "renewal",
            "3 Month PT Renewal",
            start_s2.isoformat(),
            end_s2.isoformat(),
        )

        # Scenario 3: Plan ends in 45 days (Charlie) - Should not appear in a 30-day report
        cursor.execute(
            "SELECT duration_days, price FROM plans WHERE id = ?", (plan1_id,)
        )  # Using monthly plan for Charlie
        plan1_data_charlie = cursor.fetchone()
        plan1_duration_days_charlie, plan1_price_charlie = (
            plan1_data_charlie if plan1_data_charlie else (30, 5000)
        )

        start_s3 = (
            today - timedelta(days=plan1_duration_days_charlie) + timedelta(days=45)
        )
        end_s3 = start_s3 + timedelta(
            days=plan1_duration_days_charlie
        )  # This is today + 45 days
        add_transaction(
            conn,
            member3_id,
            plan1_id,
            start_s3.isoformat(),
            plan1_price_charlie,
            "renewal",
            "Monthly GC Renewal",
            start_s3.isoformat(),
            end_s3.isoformat(),
        )

        # Scenario 4: Plan just expired (e.g., 2 days ago - Alice, another transaction)
        start_s4 = today - timedelta(
            days=plan1_duration_days + 2
        )  # Start date was (duration + 2) days ago
        end_s4 = start_s4 + timedelta(
            days=plan1_duration_days
        )  # This is today - 2 days
        add_transaction(
            conn,
            member1_id,
            plan1_id,
            start_s4.isoformat(),
            plan1_price,
            "renewal",
            "Past Monthly GC Renewal",
            start_s4.isoformat(),
            end_s4.isoformat(),
        )

        # Scenario 5: Inactive member whose plan would have ended in 15 days (David)
        cursor.execute(
            "SELECT duration_days, price FROM plans WHERE id = ?", (plan3_id,)
        )  # Annual plan for David
        plan3_data = cursor.fetchone()
        plan3_duration_days, plan3_price = plan3_data if plan3_data else (365, 50000)

        start_s5 = today - timedelta(days=plan3_duration_days) + timedelta(days=15)
        end_s5 = start_s5 + timedelta(
            days=plan3_duration_days
        )  # This is today + 15 days
        add_transaction(
            conn,
            member4_id,
            plan3_id,
            start_s5.isoformat(),
            plan3_price,
            "renewal",
            "Annual Gold Renewal - Inactive",
            start_s5.isoformat(),
            end_s5.isoformat(),
        )

        # Scenario 6: A transaction of type 'payment' (not 'renewal') whose end_date might be soon (Eve)
        cursor.execute(
            "SELECT duration_days, price FROM plans WHERE id = ?", (plan4_id,)
        )  # Single Session PT
        plan4_data = cursor.fetchone()
        plan4_duration_days, plan4_price = plan4_data if plan4_data else (1, 2000)

        start_s6 = today + timedelta(days=5)  # A payment for a session in 5 days
        end_s6 = start_s6 + timedelta(days=plan4_duration_days)  # Ends in 6 days
        add_transaction(
            conn,
            member5_id,
            plan4_id,
            start_s6.isoformat(),
            plan4_price,
            "payment",
            "Payment for PT session",
            start_s6.isoformat(),
            end_s6.isoformat(),
        )

        print("Sample data seeded successfully.")

    except sqlite3.Error as e:
        print(f"Error during seeding process: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    print("Starting data seeding process...")
    seed()
    print("Data seeding process finished.")

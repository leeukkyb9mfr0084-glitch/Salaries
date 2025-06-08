import sqlite3
from datetime import datetime, timedelta

DB_FILE = 'reporter/data/kranos_data.db'

def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        # conn.row_factory = sqlite3.Row # Optional: to access columns by name
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database {DB_FILE}: {e}")
        raise  # Re-raise the exception if connection fails

def add_member_to_db(name: str, phone: str) -> bool:
    """
    Adds a new member to the database.
    Args:
        name (str): The name of the member.
        phone (str): The phone number of the member (must be unique).
    Returns:
        bool: True if the member was added successfully, False otherwise.
    Raises:
        sqlite3.IntegrityError: If the phone number already exists (implicitly via UNIQUE constraint).
                                 Or we can catch it and return False.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        join_date = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(
            "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
            (name, phone, join_date)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # This typically means the phone number already exists due to UNIQUE constraint
        print(f"Error adding member: Phone number '{phone}' likely already exists.")
        return False
    except sqlite3.Error as e:
        print(f"Database error while adding member: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_all_members() -> list:
    """
    Retrieves all members from the database, ordered by client_name.
    Returns:
        list: A list of tuples, where each tuple represents a member
              (member_id, client_name, phone, join_date).
              Returns an empty list if no members are found or an error occurs.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT member_id, client_name, phone, join_date FROM members ORDER BY client_name ASC")
        members = cursor.fetchall()
        return members
    except sqlite3.Error as e:
        print(f"Database error while fetching members: {e}")
        return []  # Return empty list on error
    finally:
        if conn:
            conn.close()

def get_all_plans() -> list:
    """
    Retrieves all plans from the database.
    Returns:
        list: A list of tuples, where each tuple represents a plan
              (plan_id, plan_name, duration_days).
              Returns an empty list if no plans are found or an error occurs.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT plan_id, plan_name, duration_days FROM plans ORDER BY plan_name ASC")
        plans = cursor.fetchall()
        return plans
    except sqlite3.Error as e:
        print(f"Database error while fetching plans: {e}")
        return []
    finally:
        if conn:
            conn.close()

def add_group_membership_to_db(member_id: int, plan_id: int, payment_date: str,
                               start_date: str, amount_paid: float, payment_method: str) -> bool:
    """
    Adds a new group membership record to the database.
    Calculates end_date based on plan_id's duration.
    Args:
        member_id (int): ID of the member.
        plan_id (int): ID of the plan.
        payment_date (str): Payment date in 'YYYY-MM-DD' format.
        start_date (str): Membership start date in 'YYYY-MM-DD' format.
        amount_paid (float): Amount paid for the membership.
        payment_method (str): Method of payment.
    Returns:
        bool: True if successful, False otherwise.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get plan duration
        cursor.execute("SELECT duration_days FROM plans WHERE plan_id = ?", (plan_id,))
        plan_duration_row = cursor.fetchone()
        if not plan_duration_row:
            print(f"Error: Plan with ID {plan_id} not found.")
            return False
        duration_days = plan_duration_row[0]

        # Calculate end_date
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = start_date_obj + timedelta(days=duration_days)
        end_date_str = end_date_obj.strftime('%Y-%m-%d')

        cursor.execute(
            """
            INSERT INTO group_memberships
            (member_id, plan_id, payment_date, start_date, end_date, amount_paid, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (member_id, plan_id, payment_date, start_date, end_date_str, amount_paid, payment_method)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error while adding group membership: {e}")
        return False
    except ValueError as ve: # For date conversion errors
        print(f"Date format error: {ve}")
        return False
    finally:
        if conn:
            conn.close()

def get_memberships_for_member(member_id: int) -> list:
    """
    Retrieves all group membership records for a given member, joined with plan names.
    Args:
        member_id (int): The ID of the member.
    Returns:
        list: A list of tuples, where each tuple contains:
              (plan_name, payment_date, start_date, end_date, amount_paid, payment_method, membership_id)
              Ordered by start_date descending. Returns empty list on error or if no memberships.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                p.plan_name,
                gm.payment_date,
                gm.start_date,
                gm.end_date,
                gm.amount_paid,
                gm.payment_method,
                gm.membership_id
            FROM group_memberships gm
            JOIN plans p ON gm.plan_id = p.plan_id
            WHERE gm.member_id = ?
            ORDER BY gm.start_date DESC
        """, (member_id,))
        memberships = cursor.fetchall()
        return memberships
    except sqlite3.Error as e:
        print(f"Database error while fetching memberships for member {member_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_pending_renewals(target_date_str: str) -> list:
    """
    Retrieves group memberships ending in the month and year of the target_date_str.
    Args:
        target_date_str (str): The target date in 'YYYY-MM-DD' format.
    Returns:
        list: A list of tuples, where each tuple contains:
              (client_name, phone, plan_name, end_date)
              Ordered by end_date, then client_name. Returns empty list on error or if none found.
    """
    conn = None
    try:
        # Validate target_date_str format (optional, as strftime will handle some errors)
        datetime.strptime(target_date_str, '%Y-%m-%d') # Will raise ValueError if format is wrong

        conn = get_db_connection()
        cursor = conn.cursor()

        # Extract year and month from target_date_str for comparison
        # SQLite's strftime('%Y-%m', date_column) will give 'YYYY-MM'
        target_year_month = datetime.strptime(target_date_str, '%Y-%m-%d').strftime('%Y-%m')

        cursor.execute("""
            SELECT
                m.client_name,
                m.phone,
                p.plan_name,
                gm.end_date
            FROM group_memberships gm
            JOIN members m ON gm.member_id = m.member_id
            JOIN plans p ON gm.plan_id = p.plan_id
            WHERE strftime('%Y-%m', gm.end_date) = ?
            ORDER BY gm.end_date ASC, m.client_name ASC
        """, (target_year_month,))

        renewals = cursor.fetchall()
        return renewals
    except ValueError:
        print(f"Error: Invalid target_date_str format '{target_date_str}'. Please use YYYY-MM-DD.")
        return []
    except sqlite3.Error as e:
        print(f"Database error while fetching pending renewals: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_finance_report(year: int, month: int) -> float | None:
    """
    Calculates the total amount_paid from group_memberships for a given year and month.
    Args:
        year (int): The target year.
        month (int): The target month (1-12).
    Returns:
        float | None: The total sum of amount_paid, or None if no transactions or an error occurs.
    """
    conn = None
    try:
        if not (1 <= month <= 12):
            print("Error: Month must be between 1 and 12.")
            return None

        # Format month to ensure two digits (e.g., '01', '02', ..., '12')
        month_str = f"{month:02d}"
        date_prefix = f"{year}-{month_str}-" # e.g., "2023-07-"

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT SUM(amount_paid)
            FROM group_memberships
            WHERE payment_date LIKE ?
        """, (date_prefix + '%',)) # LIKE 'YYYY-MM-%'

        result = cursor.fetchone()

        if result and result[0] is not None:
            return float(result[0])
        else:
            return 0.0 # Return 0.0 if no transactions found for that month

    except sqlite3.Error as e:
        print(f"Database error while generating finance report for {year}-{month}: {e}")
        return None
    except Exception as e: # Catch any other unexpected errors
        print(f"An unexpected error occurred in get_finance_report: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_member_by_phone(phone: str) -> tuple | None:
    """Retrieves a member's ID by their phone number."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT member_id, client_name FROM members WHERE phone = ?", (phone,))
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Database error while fetching member by phone '{phone}': {e}")
        return None
    finally:
        if conn:
            conn.close()

def add_member_with_join_date(name: str, phone: str, join_date: str) -> int | None:
    """Adds a new member with a specific join date and returns their ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
            (name, phone, join_date)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # This means the phone number already exists, which is fine.
        return None # We'll fetch the ID separately in the migration script.
    except sqlite3.Error as e:
        print(f"Database error while adding member '{name}': {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_or_create_plan_id(plan_name: str, duration_days: int) -> int | None:
    """Retrieves the ID of a plan, creating it if it doesn't exist."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Check if the plan already exists
        cursor.execute("SELECT plan_id FROM plans WHERE plan_name = ?", (plan_name,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            # If not, create it
            cursor.execute(
                "INSERT INTO plans (plan_name, duration_days) VALUES (?, ?)",
                (plan_name, duration_days)
            )
            conn.commit()
            print(f"Created new plan: {plan_name}")
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error with plan '{plan_name}': {e}")
        return None
    finally:
        if conn:
            conn.close()

def add_pt_booking(member_id: int, start_date: str, sessions: int, amount_paid: float) -> bool:
    """Adds a personal training booking to the database."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pt_bookings (member_id, start_date, sessions, amount_paid)
            VALUES (?, ?, ?, ?)
            """,
            (member_id, start_date, sessions, amount_paid)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error while adding PT booking for member {member_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Example Usage (and for basic testing)
    print("Attempting to initialize DB (if not already done by database.py main)")
    # We need tables to be there, so ensure database.py's main block has run or run its functions
    from reporter.database import create_database, seed_initial_plans

    # Ensure data directory exists (if running this directly before database.py's main)
    import os
    data_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created directory: {data_dir}")

    create_database(DB_FILE) # Create tables if they don't exist

    # Seeding plans is not directly related to member management but good for full setup
    temp_conn_for_seed = get_db_connection()
    try:
        seed_initial_plans(temp_conn_for_seed)
    finally:
        if temp_conn_for_seed:
            temp_conn_for_seed.close()

    print("\n--- Testing add_member_to_db ---")
    success1 = add_member_to_db("John Doe", "1234567890")
    print(f"Added 'John Doe': {success1}")
    success2 = add_member_to_db("Jane Smith", "0987654321")
    print(f"Added 'Jane Smith': {success2}")
    success_dup = add_member_to_db("John Again", "1234567890") # Duplicate phone
    print(f"Added 'John Again' (duplicate phone): {success_dup}")

    print("\n--- Testing get_all_members ---")
    all_members = get_all_members()
    if all_members:
        for member in all_members:
            print(member)
    else:
        print("No members found or error occurred.")

    print("\n--- Testing get_all_plans ---")
    all_plans = get_all_plans()
    if all_plans:
        for plan in all_plans:
            print(plan)
    else:
        print("No plans found or error occurred.")

    print("\n--- Testing add_group_membership_to_db ---")
    if all_members and all_plans:
        test_member_id = all_members[0][0] # Get ID of first member
        test_plan_id = all_plans[0][0]     # Get ID of first plan
        today_str = datetime.now().strftime('%Y-%m-%d')

        gm_success = add_group_membership_to_db(
            member_id=test_member_id,
            plan_id=test_plan_id,
            payment_date=today_str,
            start_date=today_str,
            amount_paid=50.00,
            payment_method="Cash"
        )
        print(f"Added group membership for {all_members[0][1]}: {gm_success}")

        print("\n--- Testing get_memberships_for_member ---")
        if gm_success:
            member_history = get_memberships_for_member(test_member_id)
            if member_history:
                print(f"Membership history for member ID {test_member_id}:")
                for record in member_history:
                    print(record)
            else:
                print(f"No membership history found for member ID {test_member_id}, or an error occurred.")
        else:
            print("Skipping get_memberships_for_member test as prerequisite gm add failed.")

        # Example of trying to add with missing fields (handled by DB constraints or GUI validation later)
        # try:
        #     add_member_to_db(None, "5555555555")
        # except Exception as e:
        #     print(f"Error with None name: {e}")
    else:
        print("Skipping add_group_membership and get_history tests as no members or plans are available.")

    print("\n--- Testing get_pending_renewals ---")
    # This test in main is a bit limited as it depends on when it's run.
    # For more robust testing, specific end_dates need to be in the DB.
    today_for_renewal_test = datetime.now().strftime('%Y-%m-%d')
    pending_renewals_today = get_pending_renewals(today_for_renewal_test)
    if pending_renewals_today:
        print(f"Pending renewals for {datetime.strptime(today_for_renewal_test, '%Y-%m-%d').strftime('%B %Y')}:")
        for renewal in pending_renewals_today:
            print(renewal)
    else:
        print(f"No pending renewals found for {datetime.strptime(today_for_renewal_test, '%Y-%m-%d').strftime('%B %Y')}, or an error occurred.")

    print("\n--- Testing get_finance_report ---")
    # This test in main is also limited. More robust testing in test_database_manager.py
    last_month_test_date = datetime.now().replace(day=1) - timedelta(days=1)
    lm_year, lm_month = last_month_test_date.year, last_month_test_date.month
    total_revenue_lm = get_finance_report(lm_year, lm_month)
    if total_revenue_lm is not None:
        print(f"Total revenue for {calendar.month_name[lm_month]} {lm_year}: ${total_revenue_lm:.2f}")
    else:
        print(f"Could not retrieve finance report for {calendar.month_name[lm_month]} {lm_year}.")

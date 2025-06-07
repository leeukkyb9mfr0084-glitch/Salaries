import pytest
import pytest
import sqlite3
import os
from datetime import datetime, timedelta # Ensure timedelta is imported

# Modules to be tested
from reporter.database_manager import (
    add_member_to_db, get_all_members, get_db_connection,
    get_all_plans, add_group_membership_to_db, get_memberships_for_member,
    get_pending_renewals, get_finance_report
)
# Module needed for setting up test DB
from reporter.database import create_database, seed_initial_plans

# Define the test database file
TEST_DB_DIR = 'reporter/tests/test_data_dir' # To avoid cluttering reporter/tests
TEST_DB_FILE = os.path.join(TEST_DB_DIR, 'test_kranos_data.db')

@pytest.fixture
def db_conn(monkeypatch):
    """
    Pytest fixture to set up an in-memory SQLite database for testing.
    - Creates all necessary tables.
    - Monkeypatches DB_FILE in database_manager to use the test DB.
    - Provides a connection to this test database.
    - Cleans up the database file after tests.
    """
    # Ensure the directory for the test DB exists
    os.makedirs(TEST_DB_DIR, exist_ok=True)

    # 1. Create tables in the test-specific database file
    # create_database function handles connect, create tables, commit, close.
    create_database(TEST_DB_FILE) # This creates the tables

    # 2. Monkeypatch database_manager.DB_FILE to use TEST_DB_FILE
    # This ensures that functions within database_manager use our test DB
    monkeypatch.setattr('reporter.database_manager.DB_FILE', TEST_DB_FILE)

    # 3. Get a connection using the (now monkeypatched) get_db_connection
    # This connection can be used by tests to directly inspect/verify DB state.
    conn = get_db_connection() # This will now connect to TEST_DB_FILE

    # Seed initial plans into the test database, as get_all_plans will need them
    # and add_group_membership might rely on them via get_all_plans in the GUI flow (though test will use direct IDs)
    seed_initial_plans(conn) # Uses the connection to TEST_DB_FILE

    yield conn  # Provide the connection to the test functions

    # Teardown:
    if conn:
        conn.close()

    # Remove the test database file
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    # Remove the test data directory if it's empty
    if os.path.exists(TEST_DB_DIR) and not os.listdir(TEST_DB_DIR):
        os.rmdir(TEST_DB_DIR)


def test_add_member_successful(db_conn):
    """Tests successful addition of a new member."""
    name = "Test User"
    phone = "1234567890"

    success = add_member_to_db(name, phone)
    assert success is True, "add_member_to_db should return True on success."

    # Verify directly in the database
    cursor = db_conn.cursor()
    cursor.execute("SELECT client_name, phone, join_date FROM members WHERE phone = ?", (phone,))
    member = cursor.fetchone()

    assert member is not None, "Member was not found in the database."
    assert member[0] == name, f"Expected name '{name}', got '{member[0]}'."
    assert member[1] == phone, f"Expected phone '{phone}', got '{member[1]}'."

    # Check join_date format (YYYY-MM-DD) and that it's today
    today_date_str = datetime.now().strftime('%Y-%m-%d')
    assert member[2] == today_date_str, f"Expected join_date '{today_date_str}', got '{member[2]}'."

def test_add_member_duplicate_phone(db_conn):
    """Tests adding a member with a phone number that already exists."""
    name1 = "Test User1"
    phone = "1112223333" # Unique phone for this test

    success1 = add_member_to_db(name1, phone)
    assert success1 is True, "First member addition should be successful."

    name2 = "Test User2"
    # Attempt to add another member with the same phone number
    success2 = add_member_to_db(name2, phone)
    assert success2 is False, "Second member addition with duplicate phone should fail and return False."

    # Verify that only the first member was added
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM members WHERE phone = ?", (phone,))
    count = cursor.fetchone()[0]
    assert count == 1, "Only one member should exist with the given phone number."

def test_get_all_members_empty(db_conn):
    """Tests get_all_members when the database has no members."""
    members = get_all_members()
    assert isinstance(members, list), "Should return a list."
    assert len(members) == 0, "Should return an empty list when no members are present."

def test_get_all_members_multiple(db_conn):
    """Tests get_all_members with multiple members, checking content and order."""
    # Add members out of alphabetical order to test sorting
    member_data = [
        ("Charlie Brown", "3330001111"),
        ("Alice Wonderland", "1110002222"),
        ("Bob The Builder", "2220003333")
    ]

    for name, phone in member_data:
        assert add_member_to_db(name, phone) is True, f"Failed to add member {name}"

    members = get_all_members()
    assert len(members) == len(member_data), f"Expected {len(member_data)} members, got {len(members)}."

    # Verify names are sorted
    expected_names_sorted = sorted([m[0] for m in member_data])
    actual_names = [m[1] for m in members] # m[1] is client_name in (member_id, client_name, phone, join_date)

    assert actual_names == expected_names_sorted, \
        f"Members not sorted by name. Expected {expected_names_sorted}, got {actual_names}"

    # Verify content (optional, but good for sanity check)
    for i, expected_name in enumerate(expected_names_sorted):
        original_phone = ""
        for m_name, m_phone in member_data:
            if m_name == expected_name:
                original_phone = m_phone
                break

        # members list format: (member_id, client_name, phone, join_date)
        assert members[i][1] == expected_name
        assert members[i][2] == original_phone
        assert members[i][3] is not None # Join date should exist

def test_get_all_plans(db_conn):
    """Tests retrieval of all plans, expecting the seeded default plans."""
    # This definition should match what seed_initial_plans in database.py does.
    # This list is also defined in reporter/tests/test_database.py
    # Ideally, this would be a shared constant if it's used in multiple test files
    # For now, defining it here to resolve the import error directly.
    expected_plans_data = [
        ("Monthly - Unrestricted", 30),
        ("3 Months - Unrestricted", 90),
        ("Annual - Unrestricted", 365)
    ]

    plans_from_db = get_all_plans() # This uses the monkeypatched DB_FILE
    assert len(plans_from_db) == len(expected_plans_data), \
        f"Expected {len(expected_plans_data)} plans, got {len(plans_from_db)}"

    # Assuming get_all_plans orders by plan_name ASC as implemented.
    # Sort expected_plans_data by name for direct comparison.
    expected_plans_data.sort(key=lambda x: x[0])

    for i, expected_plan in enumerate(expected_plans_data):
        # plans_from_db: (plan_id, plan_name, duration_days)
        assert plans_from_db[i][1] == expected_plan[0], f"Expected plan name '{expected_plan[0]}', got '{plans_from_db[i][1]}'"
        assert plans_from_db[i][2] == expected_plan[1], f"Expected duration '{expected_plan[1]}' for plan '{plans_from_db[i][1]}', got '{plans_from_db[i][2]}'"

def test_add_group_membership(db_conn):
    """Tests adding a group membership and verifies data including end_date calculation."""
    # 1. Add a test member
    member_name = "Membership User"
    member_phone = "9998887777"
    assert add_member_to_db(member_name, member_phone) is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Test member not found after adding."
    member_id = member_id_row[0]

    # 2. Get a plan (assuming plans are seeded by the fixture)
    plans = get_all_plans()
    assert len(plans) > 0, "No plans found. Ensure plans are seeded for this test."
    test_plan = plans[0] # (plan_id, plan_name, duration_days)
    plan_id = test_plan[0]
    plan_duration_days = test_plan[2]

    # 3. Define membership details
    payment_date_str = "2024-01-15"
    start_date_str = "2024-01-20"
    amount_paid = 75.50
    payment_method = "Credit Card"

    # 4. Call add_group_membership_to_db
    success = add_group_membership_to_db(
        member_id, plan_id, payment_date_str, start_date_str, amount_paid, payment_method
    )
    assert success is True, "add_group_membership_to_db should return True on success."

    # 5. Verify directly in the database
    cursor.execute(
        "SELECT member_id, plan_id, payment_date, start_date, end_date, amount_paid, payment_method "
        "FROM group_memberships WHERE member_id = ?",
        (member_id,)
    )
    gm_record = cursor.fetchone()
    assert gm_record is not None, "Group membership record not found."

    (gm_member_id, gm_plan_id, gm_payment_date, gm_start_date,
     gm_end_date, gm_amount_paid, gm_payment_method) = gm_record

    assert gm_member_id == member_id
    assert gm_plan_id == plan_id
    assert gm_payment_date == payment_date_str
    assert gm_start_date == start_date_str
    assert gm_amount_paid == amount_paid
    assert gm_payment_method == payment_method

    # Verify end_date calculation
    expected_start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
    expected_end_date_obj = expected_start_date_obj + timedelta(days=plan_duration_days)
    expected_end_date_str = expected_end_date_obj.strftime('%Y-%m-%d')

    assert gm_end_date == expected_end_date_str, \
        f"End date mismatch. Expected {expected_end_date_str}, got {gm_end_date}."

def test_get_memberships_for_member(db_conn):
    """Tests retrieval of membership history for specific members."""
    # 1. Add Members
    member_a_id = add_member_to_db("Member A History", "1001001001")
    assert member_a_id is True # add_member_to_db returns True on success
    member_b_id = add_member_to_db("Member B History", "2002002002")
    assert member_b_id is True

    # Retrieve actual IDs
    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = '1001001001'")
    member_a_id = cursor.fetchone()[0]
    cursor.execute("SELECT member_id FROM members WHERE phone = '2002002002'")
    member_b_id = cursor.fetchone()[0]

    # 2. Get Plans (ensure they are seeded by fixture)
    plans = get_all_plans()
    assert len(plans) >= 2, "Need at least two plans for this test."
    plan1 = plans[0] # (plan_id, plan_name, duration_days)
    plan2 = plans[1]

    # 3. Add Group Memberships
    # Member A - Membership 1
    add_group_membership_to_db(member_a_id, plan1[0], "2023-01-01", "2023-01-01", 50, "CashA1")
    # Member A - Membership 2 (ordered earlier by start_date to test sorting)
    add_group_membership_to_db(member_a_id, plan2[0], "2022-12-01", "2022-12-01", 60, "CardA2")

    # Member B - Membership 1
    add_group_membership_to_db(member_b_id, plan1[0], "2023-02-01", "2023-02-10", 70, "CashB1")

    # 4. Test for Member A
    history_a = get_memberships_for_member(member_a_id)
    assert len(history_a) == 2, "Member A should have 2 membership records."
    # Results are ordered by start_date DESC
    assert history_a[0][0] == plan1[1] # Plan name of the latest membership (2023-01-01)
    assert history_a[0][2] == "2023-01-01" # Start date
    assert history_a[0][4] == 50 # Amount paid
    assert history_a[0][5] == "CashA1" # Payment method

    assert history_a[1][0] == plan2[1] # Plan name of the older membership (2022-12-01)
    assert history_a[1][2] == "2022-12-01" # Start date
    assert history_a[1][4] == 60 # Amount paid
    assert history_a[1][5] == "CardA2" # Payment method

    # 5. Test for Member B
    history_b = get_memberships_for_member(member_b_id)
    assert len(history_b) == 1, "Member B should have 1 membership record."
    assert history_b[0][0] == plan1[1] # Plan name
    assert history_b[0][2] == "2023-02-10" # Start date
    assert history_b[0][4] == 70 # Amount paid
    assert history_b[0][5] == "CashB1" # Payment method

def test_get_memberships_for_member_none(db_conn):
    """Tests retrieving memberships for a member who has none."""
    member_c_id_success = add_member_to_db("Member C NoHistory", "3003003003")
    assert member_c_id_success is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = '3003003003'")
    member_c_id = cursor.fetchone()[0]

    history_c = get_memberships_for_member(member_c_id)
    assert len(history_c) == 0, "Member C should have no membership history."

def test_get_pending_renewals(db_conn):
    """Tests retrieval of pending renewals for the current month."""
    # 1. Add Members and Plans
    member_r1_id = add_member_to_db("Renewal User1", "R001")
    assert member_r1_id is True
    member_r2_id = add_member_to_db("Renewal User2", "R002")
    assert member_r2_id is True
    member_n_id = add_member_to_db("NonRenewal User", "N001") # Ends next month
    assert member_n_id is True
    member_p_id = add_member_to_db("PastRenewal User", "P001") # Ended last month
    assert member_p_id is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id, client_name FROM members WHERE phone = 'R001'")
    r1_data = cursor.fetchone()
    member_r1_id, member_r1_name = r1_data[0], r1_data[1]

    cursor.execute("SELECT member_id FROM members WHERE phone = 'R002'")
    member_r2_id = cursor.fetchone()[0]

    cursor.execute("SELECT member_id FROM members WHERE phone = 'N001'")
    member_n_id = cursor.fetchone()[0]

    cursor.execute("SELECT member_id FROM members WHERE phone = 'P001'")
    member_p_id = cursor.fetchone()[0]

    plans = get_all_plans()
    assert len(plans) > 0, "Need at least one plan."
    plan_30_days = next((p for p in plans if p[2] == 30), None) # Find a 30-day plan
    assert plan_30_days is not None, "A 30-day plan is needed for reliable testing."
    plan_id_30 = plan_30_days[0]

    # 2. Setup Dates for Renewals
    today = datetime.today()
    current_month_start = today.replace(day=1)

    # Renewal 1: Ends later this month
    start_r1 = current_month_start # Starts 1st of current month
    # To make it end this month, its start_date + duration_days should be in this month.
    # If plan is 30 days, start_date should be such that end_date is within current month.
    # For simplicity, let's make end_date the 15th of current month.
    # So, start_date = 15th_current_month - 30_days_plan
    end_date_r1_target = current_month_start.replace(day=15)
    start_date_r1 = (end_date_r1_target - timedelta(days=plan_30_days[2])).strftime('%Y-%m-%d')
    payment_date_r1 = start_date_r1

    # Renewal 2: Ends at the end of this month
    # Let end_date be last day of current month
    next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1) # Handles month end
    end_date_r2_target = next_month_start - timedelta(days=1)
    start_date_r2 = (end_date_r2_target - timedelta(days=plan_30_days[2])).strftime('%Y-%m-%d')
    payment_date_r2 = start_date_r2

    # Non-Renewal: Ends next month
    start_date_n = (next_month_start.replace(day=5) - timedelta(days=plan_30_days[2])).strftime('%Y-%m-%d')
    payment_date_n = start_date_n

    # Past-Renewal: Ended last month
    last_month_end = current_month_start - timedelta(days=1)
    start_date_p = (last_month_end.replace(day=15) - timedelta(days=plan_30_days[2])).strftime('%Y-%m-%d')
    payment_date_p = start_date_p

    # 3. Add Group Memberships
    assert add_group_membership_to_db(member_r1_id, plan_id_30, payment_date_r1, start_date_r1, 50, "CashR1")
    assert add_group_membership_to_db(member_r2_id, plan_id_30, payment_date_r2, start_date_r2, 50, "CashR2")
    assert add_group_membership_to_db(member_n_id, plan_id_30, payment_date_n, start_date_n, 50, "CashN")
    assert add_group_membership_to_db(member_p_id, plan_id_30, payment_date_p, start_date_p, 50, "CashP")

    # 4. Call get_pending_renewals for today's date (current month)
    target_date_for_query = today.strftime('%Y-%m-%d')
    renewals = get_pending_renewals(target_date_for_query)

    assert len(renewals) == 2, "Should find exactly 2 renewals for the current month."

    renewal_names = sorted([r[0] for r in renewals]) # client_name is at index 0
    assert renewal_names[0] == "Renewal User1" # Check if correct members are returned
    assert renewal_names[1] == "Renewal User2"

    # Check end dates (assuming order by end_date ASC, client_name ASC)
    # renewal record: (client_name, phone, plan_name, end_date)
    assert renewals[0][3] == end_date_r1_target.strftime('%Y-%m-%d') # R1 ends on 15th
    assert renewals[1][3] == end_date_r2_target.strftime('%Y-%m-%d') # R2 ends end of month

def test_get_pending_renewals_none_for_month(db_conn):
    """Tests get_pending_renewals when no memberships end in the target month."""
    member_id = add_member_to_db("NoRenewUser", "NR001")
    assert member_id is True
    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = 'NR001'")
    member_id = cursor.fetchone()[0]

    plans = get_all_plans()
    plan_30_days = next((p for p in plans if p[2] == 30), None)
    assert plan_30_days is not None
    plan_id_30 = plan_30_days[0]

    today = datetime.today()
    # Membership ending next month
    next_month_start = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    start_date_next_month = (next_month_start.replace(day=5) - timedelta(days=plan_30_days[2])).strftime('%Y-%m-%d')
    assert add_group_membership_to_db(member_id, plan_id_30, start_date_next_month, start_date_next_month, 50, "CashNR")

    # Membership ending previous month
    current_month_start = today.replace(day=1)
    last_month_end = current_month_start - timedelta(days=1)
    start_date_prev_month = (last_month_end.replace(day=15) - timedelta(days=plan_30_days[2])).strftime('%Y-%m-%d')
    assert add_group_membership_to_db(member_id, plan_id_30, start_date_prev_month, start_date_prev_month, 50, "CashNR2")

    target_date_for_query = today.strftime('%Y-%m-%d') # Query for current month
    renewals = get_pending_renewals(target_date_for_query)
    assert len(renewals) == 0, "Should find no renewals for the current month."


def test_get_finance_report(db_conn):
    """Tests calculation of total revenue for a specific month."""
    # 1. Add Members and Plans
    member_f1_id = add_member_to_db("Finance User1", "F001")
    assert member_f1_id is True
    member_f2_id = add_member_to_db("Finance User2", "F002")
    assert member_f2_id is True
    member_f3_id = add_member_to_db("Finance User3", "F003")
    assert member_f3_id is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = 'F001'")
    member_f1_id = cursor.fetchone()[0]
    cursor.execute("SELECT member_id FROM members WHERE phone = 'F002'")
    member_f2_id = cursor.fetchone()[0]
    cursor.execute("SELECT member_id FROM members WHERE phone = 'F003'")
    member_f3_id = cursor.fetchone()[0]

    plans = get_all_plans()
    assert len(plans) > 0, "Need at least one plan."
    plan_any = plans[0] # (plan_id, plan_name, duration_days)

    # 2. Determine Previous Month and Other Months for Testing
    today = datetime.today()
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    prev_month = last_day_previous_month.month
    prev_year = last_day_previous_month.year

    # Payment date for previous month (e.g., 10th of previous month)
    pm_date1_str = last_day_previous_month.replace(day=10).strftime('%Y-%m-%d')
    pm_date2_str = last_day_previous_month.replace(day=20).strftime('%Y-%m-%d')

    # Payment date for current month
    cm_date_str = today.replace(day=5).strftime('%Y-%m-%d')

    # Payment date for month before previous month
    month_before_prev_month_end = last_day_previous_month.replace(day=1) - timedelta(days=1)
    bpm_date_str = month_before_prev_month_end.replace(day=15).strftime('%Y-%m-%d')

    # 3. Add Group Memberships with payments in different months
    # Payments in the previous month
    assert add_group_membership_to_db(member_f1_id, plan_any[0], pm_date1_str, pm_date1_str, 100.00, "CashFin1")
    assert add_group_membership_to_db(member_f2_id, plan_any[0], pm_date2_str, pm_date2_str, 50.50, "CardFin2")

    # Payment in the current month
    assert add_group_membership_to_db(member_f1_id, plan_any[0], cm_date_str, cm_date_str, 75.00, "CashFin3")

    # Payment in the month before previous month
    assert add_group_membership_to_db(member_f3_id, plan_any[0], bpm_date_str, bpm_date_str, 25.00, "CashFin4")

    # 4. Call get_finance_report for the previous month
    total_revenue_prev_month = get_finance_report(prev_year, prev_month)

    assert total_revenue_prev_month == 150.50, \
        f"Expected total revenue for {prev_year}-{prev_month} to be 150.50, got {total_revenue_prev_month}"

def test_get_finance_report_no_transactions(db_conn):
    """Tests get_finance_report for a month with no transactions."""
    today = datetime.today()
    # A month far in the future, assuming no data
    future_date = today + timedelta(days=365 * 2)
    future_year = future_date.year
    future_month = future_date.month

    total_revenue_future = get_finance_report(future_year, future_month)
    assert total_revenue_future == 0.0, \
        f"Expected 0.0 for a month with no transactions ({future_year}-{future_month}), got {total_revenue_future}"

    # Test for a specific past month known to have no transactions if needed,
    # but a future month is generally safer for "no transactions".
    # For example, test a month before any test data is added.
    # This requires knowing the exact range of test data payment_dates.
    # A simpler approach is to test a month that logically shouldn't have data.
    # For instance, year 1900, month 1
    total_revenue_ancient = get_finance_report(1900, 1)
    assert total_revenue_ancient == 0.0, \
         f"Expected 0.0 for an ancient month (1900-01), got {total_revenue_ancient}"


if __name__ == '__main__':
    # To run these tests using `python reporter/tests/test_database_manager.py`
    # You would need to invoke pytest functionalities or run them manually.
    # It's generally better to use `python -m pytest` from the root /app directory.
    print("To run these tests, navigate to the root '/app' directory and run: python -m pytest")

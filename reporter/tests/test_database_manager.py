import pytest
import pytest
import sqlite3
import os
from datetime import datetime, timedelta # Ensure timedelta is imported

# Modules to be tested
from reporter.database_manager import (
    add_member_to_db, get_all_members, get_db_connection,
    get_all_plans, add_group_membership_to_db, get_all_activity_for_member, # <- Renamed
    get_pending_renewals, get_finance_report, add_pt_booking # <- Added add_pt_booking
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
    # Assert that join_date is initially NULL (or None when fetched)
    # as per new logic where join_date is set by first activity.
    assert member[2] is None, f"Expected join_date to be None/NULL initially, got '{member[2]}'."

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

# This test is replaced by test_get_all_activity_for_member
# def test_get_memberships_for_member(db_conn):
#     """Tests retrieval of membership history for specific members."""
#     # 1. Add Members
#     member_a_id = add_member_to_db("Member A History", "1001001001")
#     assert member_a_id is True # add_member_to_db returns True on success
#     member_b_id = add_member_to_db("Member B History", "2002002002")
#     assert member_b_id is True
#
#     # Retrieve actual IDs
#     cursor = db_conn.cursor()
#     cursor.execute("SELECT member_id FROM members WHERE phone = '1001001001'")
#     member_a_id = cursor.fetchone()[0]
#     cursor.execute("SELECT member_id FROM members WHERE phone = '2002002002'")
#     member_b_id = cursor.fetchone()[0]
#
#     # 2. Get Plans (ensure they are seeded by fixture)
#     plans = get_all_plans()
#     assert len(plans) >= 2, "Need at least two plans for this test."
#     plan1 = plans[0] # (plan_id, plan_name, duration_days)
#     plan2 = plans[1]
#
#     # 3. Add Group Memberships
#     # Member A - Membership 1
#     add_group_membership_to_db(member_a_id, plan1[0], "2023-01-01", "2023-01-01", 50, "CashA1")
#     # Member A - Membership 2 (ordered earlier by start_date to test sorting)
#     add_group_membership_to_db(member_a_id, plan2[0], "2022-12-01", "2022-12-01", 60, "CardA2")
#
#     # Member B - Membership 1
#     add_group_membership_to_db(member_b_id, plan1[0], "2023-02-01", "2023-02-10", 70, "CashB1")
#
#     # 4. Test for Member A
#     history_a = get_all_activity_for_member(member_a_id) # Changed to new function
#     # ... assertions would need to be updated for new data structure and combined activities
#     assert len(history_a) == 2, "Member A should have 2 membership records."
#     # Results are ordered by start_date DESC
#     # This needs to be updated based on the new structure of get_all_activity_for_member
#     # For example, history_a[0][0] is now activity_type
#     # assert history_a[0][1] == plan1[1] # name_or_description
#     # assert history_a[0][3] == "2023-01-01" # start_date
#     # assert history_a[0][5] == 50 # amount_paid
#     # assert history_a[0][6] == "CashA1" # payment_method_or_sessions
#
#     # assert history_a[1][1] == plan2[1]
#     # assert history_a[1][3] == "2022-12-01"
#     # assert history_a[1][5] == 60
#     # assert history_a[1][6] == "CardA2"
#
#     # 5. Test for Member B
#     history_b = get_all_activity_for_member(member_b_id) # Changed to new function
#     assert len(history_b) == 1, "Member B should have 1 membership record."
#     # assert history_b[0][1] == plan1[1]
#     # assert history_b[0][3] == "2023-02-10"
#     # assert history_b[0][5] == 70
#     # assert history_b[0][6] == "CashB1"

def test_get_memberships_for_member_none(db_conn):
    """Tests retrieving memberships for a member who has none."""
    member_c_id_success = add_member_to_db("Member C NoHistory", "3003003003")
    assert member_c_id_success is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = '3003003003'")
    member_c_id = cursor.fetchone()[0]

    history_c = get_all_activity_for_member(member_c_id) # Use new function name
    assert len(history_c) == 0, "Member C should have no activity history."


# --- New and Updated Tests ---

def test_add_pt_booking(db_conn):
    """Tests adding a PT booking and verifies the inserted data."""
    # 1. Add a test member
    member_name = "PT User"
    member_phone = "PT123456"
    assert add_member_to_db(member_name, member_phone) is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Test member for PT booking not found."
    member_id = member_id_row[0]

    # 2. Define PT booking details
    start_date_str = "2024-03-01"
    sessions = 10
    amount_paid = 500.00

    # 3. Call add_pt_booking
    success = add_pt_booking(member_id, start_date_str, sessions, amount_paid)
    assert success is True, "add_pt_booking should return True on success."

    # 4. Verify directly in the database
    cursor.execute(
        "SELECT member_id, start_date, sessions, amount_paid FROM pt_bookings WHERE member_id = ?",
        (member_id,)
    )
    pt_record = cursor.fetchone()
    assert pt_record is not None, "PT booking record not found."

    (db_member_id, db_start_date, db_sessions, db_amount_paid) = pt_record
    assert db_member_id == member_id
    assert db_start_date == start_date_str
    assert db_sessions == sessions
    assert db_amount_paid == amount_paid

    # 5. Verify join_date update (as per join_date standardization)
    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    member_join_date = cursor.fetchone()[0]
    assert member_join_date == start_date_str, "Member join_date should be updated to PT start_date."


def test_get_all_activity_for_member(db_conn):
    """Tests retrieval of all activities (group and PT) for a member."""
    # 1. Add Member
    member_name = "Activity User"
    member_phone = "ACT001"
    assert add_member_to_db(member_name, member_phone) is True
    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id = cursor.fetchone()[0]

    # 2. Get a Plan
    plans = get_all_plans()
    assert len(plans) > 0, "No plans found."
    test_plan = plans[0] # (plan_id, plan_name, duration_days)
    plan_id = test_plan[0]
    plan_name = test_plan[1]

    # 3. Add Group Membership
    gm_start_date = "2024-02-15"
    gm_payment_date = "2024-02-10"
    gm_amount = 120.0
    gm_method = "Visa"
    assert add_group_membership_to_db(member_id, plan_id, gm_payment_date, gm_start_date, gm_amount, gm_method)

    # 4. Add PT Booking
    pt_start_date = "2024-03-05" # Later than GM for ordering
    pt_sessions = 8
    pt_amount = 450.0
    assert add_pt_booking(member_id, pt_start_date, pt_sessions, pt_amount)

    # Add another PT Booking with an earlier date to test ordering
    pt_early_start_date = "2024-01-20"
    pt_early_sessions = 5
    pt_early_amount = 300.0
    assert add_pt_booking(member_id, pt_early_start_date, pt_early_sessions, pt_early_amount)


    # 5. Call get_all_activity_for_member
    activities = get_all_activity_for_member(member_id)
    assert len(activities) == 3, "Expected 3 activities for the member."

    # Expected structure: (activity_type, name_or_description, payment_date, start_date, end_date, amount_paid, payment_method_or_sessions, activity_id)

    # Check ordering (by start_date DESC)
    assert activities[0][3] == pt_start_date # PT booking March 05
    assert activities[1][3] == gm_start_date # Group membership Feb 15
    assert activities[2][3] == pt_early_start_date # PT booking Jan 20

    # Verify content of the latest PT booking (activities[0])
    pt_latest_activity = activities[0]
    assert pt_latest_activity[0] == "Personal Training"
    assert pt_latest_activity[1] == "PT Session" # name_or_description
    assert pt_latest_activity[2] == pt_start_date # payment_date (same as start_date for PT)
    assert pt_latest_activity[3] == pt_start_date # start_date
    assert pt_latest_activity[4] is None # end_date
    assert pt_latest_activity[5] == pt_amount # amount_paid
    assert pt_latest_activity[6] == f"{pt_sessions} sessions" # payment_method_or_sessions
    assert pt_latest_activity[7] is not None # activity_id (booking_id)

    # Verify content of the Group Membership (activities[1])
    gm_activity = activities[1]
    assert gm_activity[0] == "Group Class"
    assert gm_activity[1] == plan_name # name_or_description (plan_name)
    assert gm_activity[2] == gm_payment_date # payment_date
    assert gm_activity[3] == gm_start_date # start_date
    assert gm_activity[4] is not None # end_date (should be calculated)
    assert gm_activity[5] == gm_amount # amount_paid
    assert gm_activity[6] == gm_method # payment_method_or_sessions
    assert gm_activity[7] is not None # activity_id (membership_id)

    # Verify content of the earliest PT booking (activities[2])
    pt_early_activity = activities[2]
    assert pt_early_activity[0] == "Personal Training"
    assert pt_early_activity[1] == "PT Session"
    assert pt_early_activity[2] == pt_early_start_date
    assert pt_early_activity[3] == pt_early_start_date
    assert pt_early_activity[4] is None
    assert pt_early_activity[5] == pt_early_amount
    assert pt_early_activity[6] == f"{pt_early_sessions} sessions"
    assert pt_early_activity[7] is not None


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


def test_get_finance_report_with_pt_bookings(db_conn):
    """Tests get_finance_report including revenue from PT bookings."""
    # 1. Add Members and Plans
    member_f1_id = add_member_to_db("Finance User PT1", "FPT001")
    assert member_f1_id is True
    member_f2_id = add_member_to_db("Finance User PT2", "FPT002")
    assert member_f2_id is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = 'FPT001'")
    member_f1_id = cursor.fetchone()[0]
    cursor.execute("SELECT member_id FROM members WHERE phone = 'FPT002'")
    member_f2_id = cursor.fetchone()[0]

    plans = get_all_plans()
    plan_any = plans[0]

    # 2. Determine Target Month/Year (e.g., previous month)
    today = datetime.today()
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    target_year = last_day_previous_month.year
    target_month = last_day_previous_month.month

    target_month_date1 = last_day_previous_month.replace(day=10).strftime('%Y-%m-%d')
    target_month_date2 = last_day_previous_month.replace(day=20).strftime('%Y-%m-%d')

    other_month_date = (last_day_previous_month.replace(day=1) - timedelta(days=15)).strftime('%Y-%m-%d') # Month before target

    # 3. Add Group Memberships
    # In target month
    assert add_group_membership_to_db(member_f1_id, plan_any[0], target_month_date1, target_month_date1, 100.00, "GM_Cash1")
    # Outside target month
    assert add_group_membership_to_db(member_f2_id, plan_any[0], other_month_date, other_month_date, 50.00, "GM_Cash2")

    # 4. Add PT Bookings
    # In target month (using start_date as payment recognition date)
    assert add_pt_booking(member_f1_id, target_month_date2, 10, 200.00) # 200.00
    assert add_pt_booking(member_f2_id, target_month_date1, 5, 150.00)  # 150.00
    # Outside target month
    assert add_pt_booking(member_f1_id, other_month_date, 8, 180.00)

    # 5. Calculate Expected Total
    # From Group Memberships in target month: 100.00
    # From PT Bookings in target month: 200.00 + 150.00 = 350.00
    expected_total_revenue = 100.00 + 350.00 # = 450.00

    # 6. Call get_finance_report
    actual_total_revenue = get_finance_report(target_year, target_month)
    assert actual_total_revenue == expected_total_revenue, \
        f"Expected total revenue {expected_total_revenue} for {target_year}-{target_month}, got {actual_total_revenue}"


def test_join_date_standardization_new_member_then_group_membership(db_conn):
    """Scenario 1: New member, then group membership. Join date becomes GM start date."""
    member_phone = "JD_GM01"
    assert add_member_to_db("JoinDate User GM", member_phone) is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id, join_date FROM members WHERE phone = ?", (member_phone,))
    member_id, initial_join_date = cursor.fetchone()
    assert initial_join_date is None, "Join date should be NULL on initial member add."

    plans = get_all_plans()
    plan_id = plans[0][0]
    gm_start_date = "2024-04-01"
    assert add_group_membership_to_db(member_id, plan_id, gm_start_date, gm_start_date, 50, "Cash")

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    updated_join_date = cursor.fetchone()[0]
    assert updated_join_date == gm_start_date, "Join date should be updated to group membership start date."


def test_join_date_standardization_new_member_then_pt_booking(db_conn):
    """Scenario 2: New member, then PT booking. Join date becomes PT start date."""
    member_phone = "JD_PT01"
    assert add_member_to_db("JoinDate User PT", member_phone) is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id, join_date FROM members WHERE phone = ?", (member_phone,))
    member_id, initial_join_date = cursor.fetchone()
    assert initial_join_date is None, "Join date should be NULL on initial member add."

    pt_start_date = "2024-05-10"
    assert add_pt_booking(member_id, pt_start_date, 10, 300)

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    updated_join_date = cursor.fetchone()[0]
    assert updated_join_date == pt_start_date, "Join date should be updated to PT booking start date."


def test_join_date_standardization_existing_member_earlier_activity(db_conn):
    """Scenario 3: Existing member, new activity earlier than current join_date."""
    member_phone = "JD_EARLY01"
    # Add member with an initial join_date (e.g. from a hypothetical import or older logic)
    # For this test, let's simulate it by first adding a PT booking
    assert add_member_to_db("JoinDate User Early", member_phone) is True
    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id = cursor.fetchone()[0]

    initial_activity_date = "2023-03-15"
    assert add_pt_booking(member_id, initial_activity_date, 5, 250) # This will set join_date to 2023-03-15

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    current_join_date = cursor.fetchone()[0]
    assert current_join_date == initial_activity_date

    # Now add a group membership with an earlier start date
    plans = get_all_plans()
    plan_id = plans[0][0]
    earlier_gm_start_date = "2023-03-01"
    assert add_group_membership_to_db(member_id, plan_id, earlier_gm_start_date, earlier_gm_start_date, 50, "Cash")

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    updated_join_date = cursor.fetchone()[0]
    assert updated_join_date == earlier_gm_start_date, "Join date should be updated to the earlier group membership start date."


def test_join_date_standardization_existing_member_later_activity(db_conn):
    """Scenario 4: Existing member, new activity later than current join_date."""
    member_phone = "JD_LATER01"
    assert add_member_to_db("JoinDate User Later", member_phone) is True
    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id = cursor.fetchone()[0]

    initial_activity_date = "2023-04-01"
    plans = get_all_plans()
    plan_id = plans[0][0]
    assert add_group_membership_to_db(member_id, plan_id, initial_activity_date, initial_activity_date, 60, "Card") # Sets join_date

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    current_join_date = cursor.fetchone()[0]
    assert current_join_date == initial_activity_date

    # Add a PT booking with a later start date
    later_pt_start_date = "2023-04-10"
    assert add_pt_booking(member_id, later_pt_start_date, 8, 280)

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    final_join_date = cursor.fetchone()[0]
    assert final_join_date == initial_activity_date, "Join date should remain the earlier date."


if __name__ == '__main__':
    # To run these tests using `python reporter/tests/test_database_manager.py`
    # You would need to invoke pytest functionalities or run them manually.
    # It's generally better to use `python -m pytest` from the root /app directory.
    print("To run these tests, navigate to the root '/app' directory and run: python -m pytest")

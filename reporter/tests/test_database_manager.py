import pytest
import pytest
import sqlite3
import os
from datetime import datetime, timedelta # Ensure timedelta is imported

# Modules to be tested
from reporter.database_manager import (
    add_member_to_db, get_all_members, get_db_connection,
    get_all_plans, get_all_plans_with_inactive, # Added get_all_plans_with_inactive
    add_plan, set_plan_active_status, # Added for test setup
    get_plan_by_name_and_duration, get_or_create_plan_id, # Added for testing
    get_all_activity_for_member,
    get_pending_renewals, get_finance_report, # add_pt_booking, # Removed
    add_transaction, # Added
    deactivate_member, delete_transaction, delete_plan, # Added for delete tests
    get_book_status, set_book_status # Added for book closing tests
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

    add_success, add_message = add_member_to_db(name, phone)
    assert add_success is True, f"add_member_to_db should return True on success. Message: {add_message}"

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

    add_success1, add_message1 = add_member_to_db(name1, phone)
    assert add_success1 is True, f"First member addition should be successful. Message: {add_message1}"

    name2 = "Test User2"
    # Attempt to add another member with the same phone number
    add_success2, add_message2 = add_member_to_db(name2, phone)
    assert add_success2 is False, f"Second member addition with duplicate phone should fail and return False. Message: {add_message2}"

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
        add_success, add_message = add_member_to_db(name, phone)
        assert add_success is True, f"Failed to add member {name}. Message: {add_message}"

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
    # In the context of get_all_members, join_date might be None if no activity has been logged.
    # This test adds members but doesn't log activity, so join_date should remain None.
    # The previous assertion `assert members[i][3] is not None` might be incorrect
    # if add_member_to_db does not set a join_date and no activities are added.
    # Let's verify current behavior of add_member_to_db.
    # add_member_to_db sets join_date to NULL initially.
    assert members[i][3] is None, f"Expected join_date to be None for member {expected_name}, got {members[i][3]}"


def test_get_all_members_filter_by_name(db_conn):
    """Tests get_all_members filtering by name."""
    member_data = [
        ("John Doe", "1112223333"),
        ("Jane Doe", "4445556666"),
        ("John Smith", "7778889999")
    ]
    for name, phone in member_data:
        add_success, add_message = add_member_to_db(name, phone)
        assert add_success is True, f"Failed to add member {name} for filter test. Message: {add_message}"

    # Filter by full name
    members = get_all_members(name_filter="John Doe")
    assert len(members) == 1
    assert members[0][1] == "John Doe"

    # Filter by partial name (case-insensitive)
    members = get_all_members(name_filter="john")
    assert len(members) == 2
    member_names = sorted([m[1] for m in members])
    assert member_names == ["John Doe", "John Smith"]

    # Filter by a name not present
    members = get_all_members(name_filter="NonExistent")
    assert len(members) == 0


def test_get_all_members_filter_by_phone(db_conn):
    """Tests get_all_members filtering by phone."""
    member_data = [
        ("User One", "1234567890"),
        ("User Two", "0987654321"),
        ("User Three", "1230000000")
    ]
    for name, phone in member_data:
        add_success, add_message = add_member_to_db(name, phone)
        assert add_success is True, f"Failed to add member {name} for phone filter test. Message: {add_message}"

    # Filter by full phone number
    members = get_all_members(phone_filter="1234567890")
    assert len(members) == 1
    assert members[0][2] == "1234567890"

    # Filter by partial phone number
    members = get_all_members(phone_filter="123")
    assert len(members) == 2
    member_phones = sorted([m[2] for m in members])
    assert member_phones == ["1230000000", "1234567890"]

    # Filter by a phone number not present
    members = get_all_members(phone_filter="111")
    assert len(members) == 0


def test_get_all_members_filter_by_name_and_phone(db_conn):
    """Tests get_all_members filtering by both name and phone."""
    member_data = [
        ("Alice Johnson", "1112223333"),
        ("Bob Johnson", "4445556666"),
        ("Alice Smith", "1117778888")
    ]
    for name, phone in member_data:
        add_success, add_message = add_member_to_db(name, phone)
        assert add_success is True, f"Failed to add member {name} for combined filter test. Message: {add_message}"

    # Filter by name and phone (exact match)
    members = get_all_members(name_filter="Alice Johnson", phone_filter="1112223333")
    assert len(members) == 1
    assert members[0][1] == "Alice Johnson"
    assert members[0][2] == "1112223333"

    # Filter by partial name and partial phone
    members = get_all_members(name_filter="Alice", phone_filter="111")
    assert len(members) == 2
    member_details = sorted([(m[1], m[2]) for m in members])
    assert member_details == [("Alice Johnson", "1112223333"), ("Alice Smith", "1117778888")]

    # Filter by name and phone (name matches, phone doesn't)
    members = get_all_members(name_filter="Alice Johnson", phone_filter="000")
    assert len(members) == 0

    # Filter by name and phone (phone matches, name doesn't)
    members = get_all_members(name_filter="NonExistent", phone_filter="1112223333")
    assert len(members) == 0


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
        # plans_from_db: (plan_id, plan_name, duration_days, is_active) - get_all_plans now returns is_active
        assert plans_from_db[i][1] == expected_plan[0], f"Expected plan name '{expected_plan[0]}', got '{plans_from_db[i][1]}'"
        assert plans_from_db[i][2] == expected_plan[1], f"Expected duration '{expected_plan[1]}' for plan '{plans_from_db[i][1]}', got '{plans_from_db[i][2]}'"
        assert plans_from_db[i][3] == 1, f"Expected plan '{expected_plan[0]}' to be active (1)."

def test_get_all_plans_no_plans(db_conn):
    """Tests get_all_plans when no plans are in the database."""
    # Clear existing plans seeded by fixture
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM plans")
    db_conn.commit()

    plans = get_all_plans()
    assert isinstance(plans, list)
    assert len(plans) == 0

# --- Tests for get_all_plans_with_inactive ---

def test_get_all_plans_with_inactive_no_plans(db_conn):
    """Tests get_all_plans_with_inactive when no plans are in the database."""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM plans")
    db_conn.commit()
    plans = get_all_plans_with_inactive()
    assert isinstance(plans, list)
    assert len(plans) == 0

def test_get_all_plans_with_inactive_only_active(db_conn):
    """Tests get_all_plans_with_inactive when only seeded (active) plans are present."""
    # Uses plans from seed_initial_plans
    expected_seeded_plan_count = 3 # Based on seed_initial_plans
    plans = get_all_plans_with_inactive()
    assert len(plans) == expected_seeded_plan_count
    for plan in plans:
        assert plan[3] == 1 # is_active flag, 1 for True

def test_get_all_plans_with_inactive_only_inactive(db_conn):
    """Tests get_all_plans_with_inactive when only inactive plans are present."""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM plans") # Clear seeded plans
    db_conn.commit()

    # Add some inactive plans
    add_success1, _, plan_id1 = add_plan("Inactive Plan 1", 10, is_active=False)
    add_success2, _, plan_id2 = add_plan("Inactive Plan 2", 20, is_active=False)
    assert add_success1 and plan_id1 is not None, "Failed to add Inactive Plan 1"
    assert add_success2 and plan_id2 is not None, "Failed to add Inactive Plan 2"

    plans = get_all_plans_with_inactive()
    assert len(plans) == 2
    for plan in plans:
        assert plan[3] == 0 # is_active flag, 0 for False

def test_get_all_plans_with_inactive_mixed(db_conn):
    """Tests get_all_plans_with_inactive with a mix of active and inactive plans."""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM plans") # Clear seeded plans
    db_conn.commit()

    # Add plans
    s1, _, _ = add_plan("Active Plan Mix", 30, is_active=True)
    s2, _, _ = add_plan("Inactive Plan Mix", 60, is_active=False)
    s3, _, _ = add_plan("Another Active Mix", 90, is_active=True)
    assert s1, "Failed to add Active Plan Mix"
    assert s2, "Failed to add Inactive Plan Mix"
    assert s3, "Failed to add Another Active Mix"

    plans = get_all_plans_with_inactive()
    assert len(plans) == 3

    active_count = sum(1 for plan in plans if plan[3] == 1) # 1 for True
    inactive_count = sum(1 for plan in plans if plan[3] == 0) # 0 for False

    assert active_count == 2
    assert inactive_count == 1

    # Check ordering by name
    plan_names = [p[1] for p in plans]
    assert plan_names == ["Active Plan Mix", "Another Active Mix", "Inactive Plan Mix"]

# --- Tests for get_plan_by_name_and_duration ---

def test_get_plan_by_name_and_duration_exists(db_conn):
    """Tests get_plan_by_name_and_duration for an existing plan."""
    # Uses seeded "Monthly - Unrestricted" which has 30 days (1 month * 30)
    plan = get_plan_by_name_and_duration("Monthly - Unrestricted", 1) # 1 month
    assert plan is not None
    assert plan[1] == "Monthly - Unrestricted"
    assert plan[2] == 30 # duration_days
    assert plan[3] == 1 # is_active, 1 for True

def test_get_plan_by_name_and_duration_not_exists(db_conn):
    """Tests get_plan_by_name_and_duration for a non-existent plan."""
    plan = get_plan_by_name_and_duration("NonExistent Plan XYZ", 10)
    assert plan is None

def test_get_plan_by_name_and_duration_wrong_duration(db_conn):
    """Tests get_plan_by_name_and_duration for an existing name but wrong duration."""
    plan = get_plan_by_name_and_duration("Monthly - Unrestricted", 2) # Seeded is 1 month
    assert plan is None

# --- Tests for get_or_create_plan_id ---

def test_get_or_create_plan_id_get_existing(db_conn):
    """Tests get_or_create_plan_id for an existing plan."""
    # Get one of the seeded plans
    cursor = db_conn.cursor()
    cursor.execute("SELECT plan_id, plan_name, duration_days FROM plans WHERE plan_name = 'Annual - Unrestricted'")
    existing_plan_row = cursor.fetchone()
    assert existing_plan_row is not None
    existing_plan_id, existing_plan_name, existing_duration_days = existing_plan_row

    retrieved_id = get_or_create_plan_id(existing_plan_name, existing_duration_days)
    assert retrieved_id == existing_plan_id

    # Ensure no new plan was created
    cursor.execute("SELECT COUNT(*) FROM plans")
    count = cursor.fetchone()[0]
    assert count == 3 # Still the 3 seeded plans

def test_get_or_create_plan_id_create_new(db_conn):
    """Tests get_or_create_plan_id for creating a new plan."""
    new_plan_name = "Super Duper Plan"
    new_plan_duration = 45 # days

    # Ensure it doesn't exist
    cursor = db_conn.cursor()
    cursor.execute("SELECT plan_id FROM plans WHERE plan_name = ?", (new_plan_name,))
    assert cursor.fetchone() is None

    new_plan_id = get_or_create_plan_id(new_plan_name, new_plan_duration)
    assert new_plan_id is not None

    # Verify it was created
    cursor.execute("SELECT plan_name, duration_days, is_active FROM plans WHERE plan_id = ?", (new_plan_id,))
    created_plan = cursor.fetchone()
    assert created_plan is not None
    assert created_plan[0] == new_plan_name
    assert created_plan[1] == new_plan_duration
    # Default is_active should be True as per table schema (or function logic if it sets it)
    # get_or_create_plan_id does not explicitly set is_active, so it relies on DB default or previous state.
    # The plans table `is_active` column has `DEFAULT TRUE`.
    assert created_plan[2] == 1 # is_active, 1 for True

    # Ensure count increased
    cursor.execute("SELECT COUNT(*) FROM plans")
    count = cursor.fetchone()[0]
    assert count == 4 # 3 seeded + 1 new


def test_add_transaction_group_class(db_conn):
    """Tests adding a group class transaction and verifies data including end_date calculation."""
    # 1. Add a test member
    member_name = "Membership User"
    member_phone = "9998887777"
    add_mem_success, add_mem_message = add_member_to_db(member_name, member_phone)
    assert add_mem_success is True, f"Failed to add member: {add_mem_message}"

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
    manual_end_date_str = "2024-02-28" # Explicitly provide an end date
    amount_paid = 75.50
    payment_method = "Credit Card"

    # 4. Call add_transaction for a 'Group Class' with explicit end_date
    success = add_transaction(
        transaction_type='Group Class',
        member_id=member_id,
        plan_id=plan_id,
        payment_date=payment_date_str,
        start_date=start_date_str,
        end_date=manual_end_date_str, # Pass the manual end date
        amount_paid=amount_paid,
        payment_method=payment_method
    )
    assert success[0] is True, "add_transaction for Group Class should return True on success."

    # 5. Verify directly in the database (transactions table)
    # Note: Fields will differ from the old group_memberships table
    cursor.execute(
        "SELECT member_id, plan_id, payment_date, start_date, end_date, amount_paid, payment_method, transaction_type "
        "FROM transactions WHERE member_id = ? AND transaction_type = 'Group Class'",
        (member_id,)
    )
    transaction_record = cursor.fetchone()
    assert transaction_record is not None, "Group Class transaction record not found."

    (t_member_id, t_plan_id, t_payment_date, t_start_date,
     t_end_date, t_amount_paid, t_payment_method, t_transaction_type) = transaction_record

    assert t_member_id == member_id
    assert t_plan_id == plan_id
    assert t_payment_date == payment_date_str
    assert t_start_date == start_date_str
    assert t_amount_paid == amount_paid
    assert t_payment_method == payment_method
    assert t_transaction_type == 'Group Class'

    # Verify end_date is the manually provided one, not auto-calculated
    assert t_end_date == manual_end_date_str, \
        f"End date mismatch. Expected manual {manual_end_date_str}, got {t_end_date}."

# This test is replaced by test_get_all_activity_for_member
# def test_get_memberships_for_member(db_conn):
#     """Tests retrieval of membership history for specific members."""
#     # 1. Add Members
#     add_success_a, _ = add_member_to_db("Member A History", "1001001001")
#     assert add_success_a is True # add_member_to_db returns True on success
#     add_success_b, _ = add_member_to_db("Member B History", "2002002002")
#     assert add_success_b is True
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
    add_success, add_message = add_member_to_db("Member C NoHistory", "3003003003")
    assert add_success is True, f"Failed to add member C NoHistory: {add_message}"

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = '3003003003'")
    member_c_id = cursor.fetchone()[0]

    history_c = get_all_activity_for_member(member_c_id) # Use new function name
    assert len(history_c) == 0, "Member C should have no activity history."


# --- New and Updated Tests ---

def test_add_transaction_group_class_invalid_plan_id(db_conn):
    """Tests add_transaction for a 'Group Class' with an invalid plan_id."""
    # 1. Add a test member
    member_name = "Transaction Test User"
    member_phone = "TRX001"
    add_mem_success, add_mem_message = add_member_to_db(member_name, member_phone)
    assert add_mem_success is True, f"Failed to add member: {add_mem_message}"
    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id = cursor.fetchone()[0]

    # 2. Attempt to add a Group Class transaction with a non-existent plan_id
    invalid_plan_id = 99999 # Assuming this ID won't exist
    payment_date_str = "2024-03-10"
    start_date_str = "2024-03-10"
    amount_paid = 50.00
    payment_method = "Cash"

    success = add_transaction(
        transaction_type='Group Class',
        member_id=member_id,
        plan_id=invalid_plan_id,
        payment_date=payment_date_str,
        start_date=start_date_str,
        amount_paid=amount_paid,
        payment_method=payment_method
    )
    # The function add_transaction is expected to print an error and return False
    assert success[0] is False, "add_transaction should return False for an invalid plan_id."

    # Verify no transaction was actually added
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ?", (member_id,))
    count = cursor.fetchone()[0]
    assert count == 0, "No transaction should have been added to the database."


def test_add_transaction_personal_training(db_conn):
    """Tests adding a Personal Training transaction and verifies the inserted data."""
    # 1. Add a test member
    member_name = "PT User"
    member_phone = "PT123456"
    add_mem_success, add_mem_message = add_member_to_db(member_name, member_phone)
    assert add_mem_success is True, f"Failed to add member: {add_mem_message}"

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Test member for PT booking not found."
    member_id = member_id_row[0]

    # 2. Define PT booking details
    start_date_str = "2024-03-01"
    manual_pt_end_date_str = "2024-03-31" # Explicitly provide an end date for PT
    sessions = 10
    amount_paid = 500.00

    # 3. Call add_transaction for 'Personal Training' with explicit end_date
    success = add_transaction(
        transaction_type='Personal Training',
        member_id=member_id,
        start_date=start_date_str, # payment_date will default to start_date
        end_date=manual_pt_end_date_str, # Pass the manual end date
        amount_paid=amount_paid,
        sessions=sessions
    )
    assert success[0] is True, "add_transaction for PT should return True on success."

    # 4. Verify directly in the database (transactions table)
    cursor.execute(
        "SELECT member_id, start_date, end_date, sessions, amount_paid, transaction_type FROM transactions WHERE member_id = ? AND transaction_type = 'Personal Training'",
        (member_id,)
    )
    pt_record = cursor.fetchone()
    assert pt_record is not None, "PT transaction record not found."

    (db_member_id, db_start_date, db_end_date, db_sessions, db_amount_paid, db_transaction_type) = pt_record
    assert db_member_id == member_id
    assert db_start_date == start_date_str
    assert db_end_date == manual_pt_end_date_str, f"PT end date mismatch. Expected {manual_pt_end_date_str}, got {db_end_date}."
    assert db_sessions == sessions
    assert db_amount_paid == amount_paid
    assert db_transaction_type == 'Personal Training'

    # 5. Verify join_date update (as per join_date standardization)
    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    member_join_date = cursor.fetchone()[0]
    assert member_join_date == start_date_str, "Member join_date should be updated to PT start_date."


def test_get_all_activity_for_member(db_conn):
    """Tests retrieval of all activities (group and PT) for a member."""
    # 1. Add Member
    member_name = "Activity User"
    member_phone = "ACT001"
    add_mem_success, add_mem_message = add_member_to_db(member_name, member_phone)
    assert add_mem_success is True, f"Failed to add member: {add_mem_message}"
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
    add_gm_success, _ = add_transaction(transaction_type='Group Class', member_id=member_id, plan_id=plan_id, payment_date=gm_payment_date, start_date=gm_start_date, amount_paid=gm_amount, payment_method=gm_method)
    assert add_gm_success

    # 4. Add PT Booking
    pt_start_date = "2024-03-05" # Later than GM for ordering
    pt_sessions = 8
    pt_amount = 450.0
    add_pt_success, _ = add_transaction(transaction_type='Personal Training', member_id=member_id, start_date=pt_start_date, sessions=pt_sessions, amount_paid=pt_amount)
    assert add_pt_success

    # Add another PT Booking with an earlier date to test ordering
    pt_early_start_date = "2024-01-20"
    pt_early_sessions = 5
    pt_early_amount = 300.0
    add_early_pt_success, _ = add_transaction(transaction_type='Personal Training', member_id=member_id, start_date=pt_early_start_date, sessions=pt_early_sessions, amount_paid=pt_early_amount)
    assert add_early_pt_success


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
    """Tests retrieval of pending renewals within the next 30 days."""
    cursor = db_conn.cursor()
    # Clear transactions and members for a clean slate for this test
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM members")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('members', 'transactions')")
    db_conn.commit()

    # 1. Setup: Add members and a plan
    member_data = {
        "User A": {"phone": "R001", "id": None, "name": "User A"},
        "User B": {"phone": "R002", "id": None, "name": "User B"},
        "User C": {"phone": "R003", "id": None, "name": "User C"},
        "User D": {"phone": "N001", "id": None, "name": "User D"}, # Will be outside window
        "User E": {"phone": "P001", "id": None, "name": "User E"}  # Will be in the past
    }
    for name, data in member_data.items():
        add_success, add_message = add_member_to_db(name, data["phone"])
        assert add_success is True, f"Failed to add member {name}: {add_message}"
        cursor.execute("SELECT member_id FROM members WHERE phone = ?", (data["phone"],))
        member_data[name]["id"] = cursor.fetchone()[0]

    plans = get_all_plans() # Seeded by fixture
    assert len(plans) > 0, "Need at least one plan for testing."
    test_plan = plans[0] # (plan_id, plan_name, duration_days, is_active)
    plan_id = test_plan[0]
    plan_name = test_plan[1]

    # 2. Define a target year and month for the test
    target_year = 2025
    target_month = 7 # July
    target_month_str = f"{target_year:04d}-{target_month:02d}"

    # Transactions to add
    # Member, end_date (YYYY-MM-DD), should_be_included_in_target_month_renewals?
    transactions_data = [
        (member_data["User A"], f"{target_year:04d}-{target_month:02d}-05", True),
        (member_data["User B"], f"{target_year:04d}-{target_month:02d}-15", True),
        (member_data["User C"], f"{target_year:04d}-{target_month:02d}-28", True),
        (member_data["User D"], f"{target_year:04d}-{target_month-1:02d}-25", False), # Previous month
        (member_data["User E"], f"{target_year:04d}-{target_month+1:02d}-02", False), # Next month
        (member_data["User A"], f"{target_year+1:04d}-{target_month:02d}-05", False), # Next year, same month
    ]

    expected_renewals_details = []
    common_start_date = f"{target_year:04d}-{target_month:02d}-01" # Arbitrary valid start date for transactions

    for member_info, end_date_str, should_be_included in transactions_data:
        # Ensure member is active by adding a transaction (any transaction makes them active for this test if they have one)
        # The get_pending_renewals function filters for m.is_active = 1.
        # add_member_to_db does not set is_active, it's set by the first transaction implicitly or by direct update.
        # For simplicity, we assume add_transaction handles join_date and thus implicitly activation path.
        # Or, we could explicitly update members to be active if needed, but let's assume transactions are enough.
        # The add_transaction will also set their join_date.

        # To ensure is_active is 1, we can add a dummy transaction if none exist, or set it.
        # However, the members are already added. The function get_pending_renewals filters for m.is_active=1.
        # The add_member_to_db does not set is_active. The first transaction does.
        # Here, we are adding the transaction that might be a renewal.
        # Let's ensure `is_active` is 1 for members we expect to see.
        if should_be_included:
             cursor.execute("UPDATE members SET is_active = 1 WHERE member_id = ?", (member_info["id"],))
    db_conn.commit() # Commit all member updates first

    for member_info, end_date_str, should_be_included in transactions_data:
        # Add the transaction that might be a renewal
        add_transaction_success, msg = add_transaction(
            transaction_type='Group Class', # get_pending_renewals filters for this type
            member_id=member_info["id"],
            plan_id=plan_id,
            payment_date=common_start_date, # Payment date can be same as start for simplicity here
            start_date=common_start_date,
            end_date=end_date_str,
            amount_paid=50,
            payment_method="CashTest"
        )
        assert add_transaction_success, f"Failed to add transaction for {member_info['name']} ending {end_date_str}. Error: {msg}"

        if should_be_included:
            expected_renewals_details.append({
                "client_name": member_info["name"],
                "phone": member_info["phone"],
                "plan_name": plan_name,
                "end_date": end_date_str
            })

    # Sort expected renewals by end_date, then by client_name (as per query's ORDER BY)
    expected_renewals_details.sort(key=lambda x: (x["end_date"], x["client_name"]))

    # 3. Call get_pending_renewals for the target month
    actual_renewals = get_pending_renewals(target_year, target_month)

    # 4. Assertions
    assert len(actual_renewals) == len(expected_renewals_details), \
        f"Expected {len(expected_renewals_details)} renewals for {target_month_str}, but got {len(actual_renewals)}. Actual: {actual_renewals}"

    for i, expected in enumerate(expected_renewals_details):
        actual_record = actual_renewals[i]
        assert actual_record[0] == expected["client_name"], f"Mismatch in client_name at index {i}"
        assert actual_record[1] == expected["phone"], f"Mismatch in phone at index {i}"
        assert actual_record[2] == expected["plan_name"], f"Mismatch in plan_name at index {i}"
        assert actual_record[3] == expected["end_date"], f"Mismatch in end_date at index {i}"

def test_get_pending_renewals_none_when_no_relevant_data(db_conn):
    """Tests get_pending_renewals returns empty list when no transactions are in the 30-day window."""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM members") # Also clear members to avoid foreign key issues if any were added
    db_conn.commit()

    # Add one member and one plan
    add_mem_success, _ = add_member_to_db("Test User No Renew", "TNR001")
    assert add_mem_success
    cursor.execute("SELECT member_id FROM members WHERE phone = 'TNR001'")
    member_id = cursor.fetchone()[0]

    plans = get_all_plans()
    plan_id = plans[0][0]

    today_obj = datetime.today().date()

    # Transaction ending far in the future
    end_date_future = (today_obj + timedelta(days=100)).strftime('%Y-%m-%d')
    add_future_success, _ = add_transaction(transaction_type='Group Class', member_id=member_id, plan_id=plan_id, payment_date=today_obj.strftime('%Y-%m-%d'), start_date=today_obj.strftime('%Y-%m-%d'), end_date=end_date_future, amount_paid=50)
    assert add_future_success

    # Transaction ending in the past
    end_date_past = (today_obj - timedelta(days=100)).strftime('%Y-%m-%d')
    add_past_success, _ = add_transaction(transaction_type='Group Class', member_id=member_id, plan_id=plan_id, payment_date=today_obj.strftime('%Y-%m-%d'), start_date=today_obj.strftime('%Y-%m-%d'), end_date=end_date_past, amount_paid=50)
    assert add_past_success

    # Call with a year and month guaranteed to have no data from the setup
    renewals = get_pending_renewals(year=1900, month=1)
    assert len(renewals) == 0, "Expected no renewals when all end_dates are outside the 30-day window."


def test_get_finance_report(db_conn):
    """Tests calculation of total revenue for a specific month."""
    # 1. Add Members and Plans
    add_s1, _ = add_member_to_db("Finance User1", "F001")
    assert add_s1 is True
    add_s2, _ = add_member_to_db("Finance User2", "F002")
    assert add_s2 is True
    add_s3, _ = add_member_to_db("Finance User3", "F003")
    assert add_s3 is True

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

    # 3. Add Group Memberships with payments in different months (as Transactions)
    # Payments in the previous month
    add_tx1_s, _ = add_transaction(transaction_type='Group Class', member_id=member_f1_id, plan_id=plan_any[0], payment_date=pm_date1_str, start_date=pm_date1_str, amount_paid=100.00, payment_method="CashFin1")
    assert add_tx1_s
    add_tx2_s, _ = add_transaction(transaction_type='Group Class', member_id=member_f2_id, plan_id=plan_any[0], payment_date=pm_date2_str, start_date=pm_date2_str, amount_paid=50.50, payment_method="CardFin2")
    assert add_tx2_s

    # Payment in the current month
    add_tx3_s, _ = add_transaction(transaction_type='Group Class', member_id=member_f1_id, plan_id=plan_any[0], payment_date=cm_date_str, start_date=cm_date_str, amount_paid=75.00, payment_method="CashFin3")
    assert add_tx3_s

    # Payment in the month before previous month
    add_tx4_s, _ = add_transaction(transaction_type='Group Class', member_id=member_f3_id, plan_id=plan_any[0], payment_date=bpm_date_str, start_date=bpm_date_str, amount_paid=25.00, payment_method="CashFin4")
    assert add_tx4_s

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
    add_s1, _ = add_member_to_db("Finance User PT1", "FPT001")
    assert add_s1 is True
    add_s2, _ = add_member_to_db("Finance User PT2", "FPT002")
    assert add_s2 is True

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

    # 3. Add Group Memberships (as Transactions)
    # In target month
    add_gm1_s, _ = add_transaction(transaction_type='Group Class', member_id=member_f1_id, plan_id=plan_any[0], payment_date=target_month_date1, start_date=target_month_date1, amount_paid=100.00, payment_method="GM_Cash1")
    assert add_gm1_s
    # Outside target month
    add_gm2_s, _ = add_transaction(transaction_type='Group Class', member_id=member_f2_id, plan_id=plan_any[0], payment_date=other_month_date, start_date=other_month_date, amount_paid=50.00, payment_method="GM_Cash2")
    assert add_gm2_s

    # 4. Add PT Bookings (as Transactions)
    # In target month (using start_date as payment recognition date for PT, payment_date for transaction table)
    add_pt1_s, _ = add_transaction(transaction_type='Personal Training', member_id=member_f1_id, payment_date=target_month_date2, start_date=target_month_date2, sessions=10, amount_paid=200.00) # 200.00
    assert add_pt1_s
    add_pt2_s, _ = add_transaction(transaction_type='Personal Training', member_id=member_f2_id, payment_date=target_month_date1, start_date=target_month_date1, sessions=5, amount_paid=150.00)  # 150.00
    assert add_pt2_s
    # Outside target month
    add_pt3_s, _ = add_transaction(transaction_type='Personal Training', member_id=member_f1_id, payment_date=other_month_date, start_date=other_month_date, sessions=8, amount_paid=180.00)
    assert add_pt3_s

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
    add_mem_s, _ = add_member_to_db("JoinDate User GM", member_phone)
    assert add_mem_s is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id, join_date FROM members WHERE phone = ?", (member_phone,))
    member_id, initial_join_date = cursor.fetchone()
    assert initial_join_date is None, "Join date should be NULL on initial member add."

    plans = get_all_plans()
    plan_id = plans[0][0]
    gm_start_date = "2024-04-01"
    add_tx_s, _ = add_transaction(transaction_type='Group Class', member_id=member_id, plan_id=plan_id, payment_date=gm_start_date, start_date=gm_start_date, amount_paid=50, payment_method="Cash")
    assert add_tx_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    updated_join_date = cursor.fetchone()[0]
    assert updated_join_date == gm_start_date, "Join date should be updated to group membership start date."


def test_join_date_standardization_new_member_then_pt_booking(db_conn):
    """Scenario 2: New member, then PT booking. Join date becomes PT start date."""
    member_phone = "JD_PT01"
    add_mem_s, _ = add_member_to_db("JoinDate User PT", member_phone)
    assert add_mem_s is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id, join_date FROM members WHERE phone = ?", (member_phone,))
    member_id, initial_join_date = cursor.fetchone()
    assert initial_join_date is None, "Join date should be NULL on initial member add."

    pt_start_date = "2024-05-10"
    add_tx_s, _ = add_transaction(transaction_type='Personal Training', member_id=member_id, start_date=pt_start_date, sessions=10, amount_paid=300)
    assert add_tx_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    updated_join_date = cursor.fetchone()[0]
    assert updated_join_date == pt_start_date, "Join date should be updated to PT booking start date."


def test_join_date_standardization_existing_member_earlier_activity(db_conn):
    """Scenario 3: Existing member, new activity earlier than current join_date."""
    member_phone = "JD_EARLY01"
    # Add member with an initial join_date (e.g. from a hypothetical import or older logic)
    # For this test, let's simulate it by first adding a PT booking
    add_mem_s, _ = add_member_to_db("JoinDate User Early", member_phone)
    assert add_mem_s is True
    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id = cursor.fetchone()[0]

    initial_activity_date = "2023-03-15"
    add_tx1_s, _ = add_transaction(transaction_type='Personal Training', member_id=member_id, start_date=initial_activity_date, sessions=5, amount_paid=250) # This will set join_date to 2023-03-15
    assert add_tx1_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    current_join_date = cursor.fetchone()[0]
    assert current_join_date == initial_activity_date

    # Now add a group membership with an earlier start date
    plans = get_all_plans()
    plan_id = plans[0][0]
    earlier_gm_start_date = "2023-03-01"
    add_tx2_s, _ = add_transaction(transaction_type='Group Class', member_id=member_id, plan_id=plan_id, payment_date=earlier_gm_start_date, start_date=earlier_gm_start_date, amount_paid=50, payment_method="Cash")
    assert add_tx2_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    updated_join_date = cursor.fetchone()[0]
    assert updated_join_date == earlier_gm_start_date, "Join date should be updated to the earlier group membership start date."


def test_join_date_standardization_existing_member_later_activity(db_conn):
    """Scenario 4: Existing member, new activity later than current join_date."""
    member_phone = "JD_LATER01"
    add_mem_s, _ = add_member_to_db("JoinDate User Later", member_phone)
    assert add_mem_s is True
    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id = cursor.fetchone()[0]

    initial_activity_date = "2023-04-01"
    plans = get_all_plans()
    plan_id = plans[0][0]
    add_tx1_s, _ = add_transaction(transaction_type='Group Class', member_id=member_id, plan_id=plan_id, payment_date=initial_activity_date, start_date=initial_activity_date, amount_paid=60, payment_method="Card") # Sets join_date
    assert add_tx1_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    current_join_date = cursor.fetchone()[0]
    assert current_join_date == initial_activity_date

    # Add a PT booking with a later start date
    later_pt_start_date = "2023-04-10"
    add_tx2_s, _ = add_transaction(transaction_type='Personal Training', member_id=member_id, start_date=later_pt_start_date, sessions=8, amount_paid=280)
    assert add_tx2_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    final_join_date = cursor.fetchone()[0]
    assert final_join_date == initial_activity_date, "Join date should remain the earlier date."


# --- Tests for delete operations ---

def test_deactivate_member(db_conn):
    """Tests deactivating a member and ensures their transactions are NOT deleted, and member is marked inactive."""
    # 1. Add a member
    member_name = "Member to Deactivate"
    member_phone = "DEACT001"
    add_mem_s, add_mem_msg = add_member_to_db(member_name, member_phone)
    assert add_mem_s is True, f"Failed to add member for deactivation test: {add_mem_msg}"
    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Failed to add member for deactivation test."
    member_id = member_id_row[0]

    # 2. Add transactions for the member
    plans = get_all_plans()
    assert len(plans) > 0, "No plans available to create transactions."
    plan_id = plans[0][0]
    initial_number_of_transactions_added = 2

    add_transaction(transaction_type='Group Class', member_id=member_id, plan_id=plan_id,
                    payment_date="2024-01-01", start_date="2024-01-01", amount_paid=50, payment_method="Cash")
    add_transaction(transaction_type='Personal Training', member_id=member_id, start_date="2024-01-05",
                    sessions=5, amount_paid=100)

    # Verify transactions were added
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ?", (member_id,))
    assert cursor.fetchone()[0] == initial_number_of_transactions_added, "Failed to add initial transactions for the member."

    # 3. Call deactivate_member
    # Assuming deactivate_member is imported or available in the scope
    from reporter.database_manager import deactivate_member # Ensure it's imported
    success, message = deactivate_member(member_id)
    assert success is True
    assert message == "Member deactivated successfully."

    # 4. Verify member is marked as inactive in DB but still exists
    cursor.execute("SELECT client_name, phone, is_active FROM members WHERE member_id = ?", (member_id,))
    deactivated_member_record = cursor.fetchone()
    assert deactivated_member_record is not None, "Member should still exist in the database after deactivation."
    assert deactivated_member_record[0] == member_name # client_name
    assert deactivated_member_record[1] == member_phone # phone
    assert deactivated_member_record[2] == 0, f"Member's is_active flag should be 0, but was {deactivated_member_record[2]}."

    # 5. Verify transactions for the member still exist
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ?", (member_id,))
    transaction_count = cursor.fetchone()[0]
    assert transaction_count == initial_number_of_transactions_added, \
        "Transactions for the deactivated member should not have been deleted."


def test_delete_transaction(db_conn):
    """Tests deleting a single transaction and ensures the member still exists."""
    # 1. Add a member
    member_name = "Transaction Test Member"
    member_phone = "TRXDEL001"
    add_mem_s, add_mem_msg = add_member_to_db(member_name, member_phone)
    assert add_mem_s is True, f"Failed to add member for transaction deletion test: {add_mem_msg}"
    cursor = db_conn.cursor()
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Failed to add member for transaction deletion test."
    member_id = member_id_row[0]

    # 2. Add a transaction for the member
    plans = get_all_plans()
    plan_id = plans[0][0]
    add_transaction(transaction_type='Group Class', member_id=member_id, plan_id=plan_id,
                    payment_date="2024-02-01", start_date="2024-02-01", amount_paid=60, payment_method="Card")

    # Get the transaction_id of the added transaction
    cursor.execute("SELECT transaction_id FROM transactions WHERE member_id = ? ORDER BY transaction_id DESC LIMIT 1", (member_id,)) # Get the last one
    transaction_id_row = cursor.fetchone()
    assert transaction_id_row is not None, "Failed to retrieve the added transaction."
    transaction_id_to_delete = transaction_id_row[0]

    # Add a second transaction to ensure only the specific one is deleted
    add_transaction(transaction_type='Personal Training', member_id=member_id, start_date="2024-02-05",
                    sessions=3, amount_paid=70)

    cursor.execute("SELECT transaction_id FROM transactions WHERE member_id = ? AND transaction_type = 'Personal Training'", (member_id,))
    other_transaction_id_row = cursor.fetchone()
    assert other_transaction_id_row is not None
    other_transaction_id = other_transaction_id_row[0]


    # 3. Call delete_transaction
    delete_transaction(transaction_id_to_delete)

    # 4. Assert the specific transaction is deleted
    cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id_to_delete,))
    assert cursor.fetchone() is None, "The specified transaction was not deleted."

    # 5. Assert other transactions for the member still exist
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ?", (member_id,))
    assert cursor.fetchone()[0] == 1, "Other transactions for the member were unintentionally deleted."
    cursor.execute("SELECT transaction_id FROM transactions WHERE member_id = ?", (member_id,))
    remaining_transaction_id = cursor.fetchone()[0]
    assert remaining_transaction_id == other_transaction_id, "The wrong transaction was deleted."


    # 6. Assert the member still exists
    cursor.execute("SELECT * FROM members WHERE member_id = ?", (member_id,))
    assert cursor.fetchone() is not None, "Member was unintentionally deleted."


def test_delete_plan(db_conn):
    """Tests deleting a plan, including cases where it's in use."""
    cursor = db_conn.cursor()

    # Scenario 1: Delete a plan that is not in use
    plan_name_unused = "Temporary Test Plan Unused"
    plan_duration_unused = 15
    # Use add_plan from database_manager, not direct SQL, to ensure consistency
    add_s_unused, msg_unused_add, unused_plan_id_val = add_plan(plan_name_unused, plan_duration_unused, is_active=True)
    assert add_s_unused and unused_plan_id_val is not None, f"Failed to add unused plan for deletion test: {msg_unused_add}"

    result_unused, message_unused = delete_plan(unused_plan_id_val)
    assert result_unused is True, f"delete_plan should return True for unused plan. Message: {message_unused}"
    assert message_unused == "Plan deleted successfully.", f"Unexpected message: {message_unused}"

    cursor.execute("SELECT * FROM plans WHERE plan_id = ?", (unused_plan_id_val,))
    assert cursor.fetchone() is None, "Unused plan was not actually deleted from the database."

    # Scenario 2: Attempt to delete a plan that is in use
    plan_name_used = "Temporary Test Plan Used"
    plan_duration_used = 45
    add_s_used, msg_used_add, used_plan_id_val = add_plan(plan_name_used, plan_duration_used, is_active=True)
    assert add_s_used and used_plan_id_val is not None, f"Failed to add used plan for deletion test: {msg_used_add}"

    # Add a member and a transaction linking to this plan
    member_name = "Plan User"
    member_phone = "PLANUSER01"
    add_mem_s, add_mem_msg = add_member_to_db(member_name, member_phone)
    assert add_mem_s is True, f"Failed to add member for plan test: {add_mem_msg}"
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None
    member_id = member_id_row[0]

    add_tx_s, _ = add_transaction(transaction_type='Group Class', member_id=member_id, plan_id=used_plan_id_val,
                    payment_date="2024-03-01", start_date="2024-03-01", amount_paid=80, payment_method="Online")
    assert add_tx_s

    result_used, message_used = delete_plan(used_plan_id_val)
    assert result_used is False, "delete_plan should return False for a plan in use."
    assert message_used == "Plan is in use and cannot be deleted.", f"Unexpected message: {message_used}"

    # Verify the plan was NOT deleted
    cursor.execute("SELECT * FROM plans WHERE plan_id = ?", (used_plan_id_val,))
    assert cursor.fetchone() is not None, "Used plan was deleted, but it shouldn't have been."

    # Verify the transaction linking to the plan still exists
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE plan_id = ?", (used_plan_id_val,))
    assert cursor.fetchone()[0] == 1, "Transaction linking to the used plan was unexpectedly deleted or altered."


if __name__ == '__main__':
    # To run these tests using `python reporter/tests/test_database_manager.py`
    # You would need to invoke pytest functionalities or run them manually.
    # It's generally better to use `python -m pytest` from the root /app directory.
    print("To run these tests, navigate to the root '/app' directory and run: python -m pytest")


# --- Tests for get_transactions_with_member_details ---

def setup_test_data_for_history_filters(conn: sqlite3.Connection):
    """Helper function to populate the database with specific data for testing history filters."""
    cursor = conn.cursor()
    # Clear existing data to ensure a clean slate for these specific tests
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM members")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('members', 'transactions')") # Reset auto-increment
    conn.commit()

    # Member 1: Alice (for name, phone, join_date tests)
    cursor.execute("INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
                   ("Alice Wonderland", "111-222-3333", "2023-01-01"))
    m_id_alice = cursor.lastrowid

    # Member 2: Bob (for name, phone, join_date tests)
    cursor.execute("INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
                   ("Bob The Builder", "222-333-4444", "2023-02-15"))
    m_id_bob = cursor.lastrowid

    # Member 3: Alice Other (for name filter distinction)
    cursor.execute("INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
                   ("Alice Other", "111-444-5555", "2023-01-01")) # Same join date as Alice Wonderland
    m_id_alice_other = cursor.lastrowid

    # Member 4: Charlie (no transactions)
    cursor.execute("INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
                   ("Charlie NoTrans", "333-555-6666", "2023-03-01"))


    # Transactions
    # Alice Wonderland
    cursor.execute("INSERT INTO transactions (member_id, transaction_type, amount_paid, start_date, payment_date) VALUES (?, ?, ?, ?, ?)",
                   (m_id_alice, "Group Class", 50.00, "2023-01-10", "2023-01-10")) # T1
    cursor.execute("INSERT INTO transactions (member_id, transaction_type, amount_paid, start_date, payment_date, sessions) VALUES (?, ?, ?, ?, ?, ?)",
                   (m_id_alice, "Personal Training", 70.00, "2023-03-05", "2023-03-05", 10)) # T2

    # Bob The Builder
    cursor.execute("INSERT INTO transactions (member_id, transaction_type, amount_paid, start_date, payment_date) VALUES (?, ?, ?, ?, ?)",
                   (m_id_bob, "Group Class", 60.00, "2023-02-20", "2023-02-20")) # T3

    # Alice Other
    cursor.execute("INSERT INTO transactions (member_id, transaction_type, amount_paid, start_date, payment_date) VALUES (?, ?, ?, ?, ?)",
                   (m_id_alice_other, "Group Class", 55.00, "2023-01-15", "2023-01-15")) # T4

    conn.commit()


def test_get_transactions_with_member_details_no_filters(db_conn):
    setup_test_data_for_history_filters(db_conn)
    # Import here to ensure DB_FILE is patched by db_conn fixture first
    from reporter.database_manager import get_transactions_with_member_details
    results = get_transactions_with_member_details()
    assert len(results) == 4, "Should return all 4 transactions"

def test_get_transactions_with_member_details_name_filter(db_conn):
    setup_test_data_for_history_filters(db_conn)
    from reporter.database_manager import get_transactions_with_member_details

    results_alice = get_transactions_with_member_details(name_filter="Alice")
    assert len(results_alice) == 3, "Should return 3 transactions for 'Alice' (Alice Wonderland, Alice Other)"
    for record in results_alice:
        assert "Alice" in record[10], "Client name should contain 'Alice'" # client_name is index 10

    results_bob = get_transactions_with_member_details(name_filter="Bob The Builder")
    assert len(results_bob) == 1, "Should return 1 transaction for 'Bob The Builder'"
    assert results_bob[0][10] == "Bob The Builder"

def test_get_transactions_with_member_details_phone_filter(db_conn):
    setup_test_data_for_history_filters(db_conn)
    from reporter.database_manager import get_transactions_with_member_details

    results = get_transactions_with_member_details(phone_filter="111-222-3333") # Alice Wonderland
    assert len(results) == 2, "Should return 2 transactions for Alice Wonderland's phone"
    assert results[0][11] == "111-222-3333" # phone is index 11

    results_partial = get_transactions_with_member_details(phone_filter="111") # Alice W and Alice O
    assert len(results_partial) == 3, "Should return 3 transactions for phones starting with '111'"

def test_get_transactions_with_member_details_join_date_filter(db_conn):
    setup_test_data_for_history_filters(db_conn)
    from reporter.database_manager import get_transactions_with_member_details

    results = get_transactions_with_member_details(join_date_filter="2023-01-01") # Alice W and Alice O
    assert len(results) == 3, "Should return 3 transactions for members joined on 2023-01-01"
    for record in results:
        assert record[12] == "2023-01-01" # join_date is index 12

def test_get_transactions_with_member_details_combined_filters(db_conn):
    setup_test_data_for_history_filters(db_conn)
    from reporter.database_manager import get_transactions_with_member_details

    # Name and Phone
    results = get_transactions_with_member_details(name_filter="Alice", phone_filter="111-444-5555") # Alice Other
    assert len(results) == 1, "Should return 1 transaction for Alice Other by name and phone"
    assert results[0][10] == "Alice Other"
    assert results[0][11] == "111-444-5555"

    # Name and Join Date
    results = get_transactions_with_member_details(name_filter="Bob", join_date_filter="2023-02-15") # Bob
    assert len(results) == 1, "Should return 1 transaction for Bob by name and join date"
    assert results[0][10] == "Bob The Builder"

def test_get_transactions_with_member_details_invalid_date_format_filter(db_conn):
    setup_test_data_for_history_filters(db_conn)
    from reporter.database_manager import get_transactions_with_member_details
    # This should ignore the invalid date filter and return all transactions
    results = get_transactions_with_member_details(join_date_filter="01/01/2023")
    assert len(results) == 4, "Should ignore invalid date format and return all transactions"

def test_get_transactions_with_member_details_no_results(db_conn):
    setup_test_data_for_history_filters(db_conn)
    from reporter.database_manager import get_transactions_with_member_details

    results = get_transactions_with_member_details(name_filter="NonExistentName")
    assert len(results) == 0, "Should return 0 transactions for a non-existent name"

    results = get_transactions_with_member_details(join_date_filter="1900-01-01")
    assert len(results) == 0, "Should return 0 transactions for a non-existent join date"

    results = get_transactions_with_member_details(name_filter="Alice", phone_filter="999-999-9999") # Alice exists, but not this phone
    assert len(results) == 0, "Should return 0 transactions for existing name but non-existent phone"


# --- Tests for Monthly Book Closing ---

def test_get_book_status_non_existent(db_conn):
    """Tests get_book_status for a month_key that doesn't exist, expecting 'open'."""
    month_key = "2099-12" # Assuming this key won't exist
    status = get_book_status(month_key)
    assert status == "open", f"Expected 'open' for non-existent month_key '{month_key}', got '{status}'"

def test_set_and_get_book_status_closed(db_conn):
    """Tests setting a month's book status to 'closed' and then retrieving it."""
    month_key = "2023-11"

    # Set status to closed
    set_success = set_book_status(month_key, "closed")
    assert set_success is True, f"set_book_status for '{month_key}' to 'closed' should return True."

    # Get status
    status = get_book_status(month_key)
    assert status == "closed", f"Expected status 'closed' for '{month_key}', got '{status}'"

def test_set_and_get_book_status_open(db_conn):
    """Tests setting a month's book status to 'open' and then retrieving it."""
    month_key = "2023-10"

    # Set status to open (might be default, but explicit set is good)
    set_success = set_book_status(month_key, "open")
    assert set_success is True, f"set_book_status for '{month_key}' to 'open' should return True."

    # Get status
    status = get_book_status(month_key)
    assert status == "open", f"Expected status 'open' for '{month_key}', got '{status}'"

def test_set_book_status_update_existing(db_conn):
    """Tests updating an existing month's book status from 'closed' to 'open'."""
    month_key = "2023-09"

    # Initial set to closed
    set_initial_success = set_book_status(month_key, "closed")
    assert set_initial_success is True, "Initial set_book_status to 'closed' failed."

    # Update to open
    set_update_success = set_book_status(month_key, "open")
    assert set_update_success is True, "Updating set_book_status to 'open' should return True."

    # Get status
    status = get_book_status(month_key)
    assert status == "open", f"Expected status 'open' for '{month_key}' after update, got '{status}'"

    # Verify directly in DB
    cursor = db_conn.cursor()
    cursor.execute("SELECT status FROM monthly_book_status WHERE month_key = ?", (month_key,))
    db_record = cursor.fetchone()
    assert db_record is not None, f"No record found in DB for month_key '{month_key}'"
    assert db_record[0] == "open", f"DB status for '{month_key}' should be 'open', got '{db_record[0]}'"

    cursor.execute("SELECT COUNT(*) FROM monthly_book_status WHERE month_key = ?", (month_key,))
    count = cursor.fetchone()[0]
    assert count == 1, f"Expected exactly one record for month_key '{month_key}', found {count}"


def _setup_member_and_plan_for_transaction_tests(db_conn, member_phone_suffix="TRN"):
    """Helper to create a member and get a plan_id for transaction tests."""
    cursor = db_conn.cursor()
    # Add a member
    member_name = f"Test Member {member_phone_suffix}"
    member_phone = f"MEMBER{member_phone_suffix}"
    add_mem_s, _ = add_member_to_db(member_name, member_phone) # Using existing function
    assert add_mem_s, f"Failed to add member in _setup_member_and_plan_for_transaction_tests for suffix {member_phone_suffix}"
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Failed to create member for transaction test."
    member_id = member_id_row[0]

    # Get a plan_id (assuming plans are seeded by db_conn fixture)
    cursor.execute("SELECT plan_id FROM plans LIMIT 1")
    plan_id_row = cursor.fetchone()
    assert plan_id_row is not None, "No plans found in DB; needed for transaction test."
    plan_id = plan_id_row[0]

    return member_id, plan_id

def test_add_transaction_when_books_closed(db_conn):
    """Tests that add_transaction is blocked when books for the payment_date month are closed."""
    member_id, plan_id = _setup_member_and_plan_for_transaction_tests(db_conn, "BC_ADD")

    month_key_closed = "2024-07"
    payment_date_in_closed_month = "2024-07-15"
    start_date = "2024-07-10" # Can be different from payment_date

    assert set_book_status(month_key_closed, "closed") is True, "Failed to close books for the test."

    success, message = add_transaction(
        transaction_type='Group Class',
        member_id=member_id,
        plan_id=plan_id,
        payment_date=payment_date_in_closed_month,
        start_date=start_date,
        amount_paid=100.00,
        payment_method="Cash"
    )

    assert success is False, "add_transaction should have failed due to closed books."
    expected_message = f"Cannot add transaction. Books for {month_key_closed} are closed."
    # Check if the returned message starts with the expected string, as it might have suffixes from DB manager.
    assert message.startswith(expected_message), f"Expected message '{expected_message}', got '{message}'"


    # Verify no transaction was added
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ? AND payment_date = ?",
                   (member_id, payment_date_in_closed_month))
    count = cursor.fetchone()[0]
    assert count == 0, "Transaction was added despite books being closed."

def test_delete_transaction_when_books_closed(db_conn):
    """Tests that delete_transaction is blocked when books for the transaction's month are closed."""
    member_id, plan_id = _setup_member_and_plan_for_transaction_tests(db_conn, "BC_DEL")

    month_key_closed = "2024-08"
    payment_date_in_closed_month = "2024-08-10"

    # Add a transaction first
    add_success, _ = add_transaction(
        transaction_type='Group Class',
        member_id=member_id,
        plan_id=plan_id,
        payment_date=payment_date_in_closed_month,
        start_date=payment_date_in_closed_month,
        amount_paid=120.00,
        payment_method="Card"
    )
    assert add_success is True, "Failed to add initial transaction for the test."

    cursor = db_conn.cursor()
    cursor.execute("SELECT transaction_id FROM transactions WHERE member_id = ? AND payment_date = ?",
                   (member_id, payment_date_in_closed_month))
    transaction_id_row = cursor.fetchone()
    assert transaction_id_row is not None, "Failed to retrieve the added transaction_id."
    transaction_id_to_delete = transaction_id_row[0]

    # Now, close the books for that month
    assert set_book_status(month_key_closed, "closed") is True, "Failed to close books for the test."

    # Attempt to delete the transaction
    delete_success, message = delete_transaction(transaction_id_to_delete)

    assert delete_success is False, "delete_transaction should have failed due to closed books."
    expected_message = f"Cannot delete transaction. Books for {month_key_closed} are closed."
    assert message.startswith(expected_message), f"Expected message '{expected_message}', got '{message}'"


    # Verify the transaction still exists
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE transaction_id = ?", (transaction_id_to_delete,))
    count = cursor.fetchone()[0]
    assert count == 1, "Transaction was deleted despite books being closed."

def test_add_transaction_when_books_open(db_conn):
    """Tests that add_transaction succeeds when books for the payment_date month are open."""
    member_id, plan_id = _setup_member_and_plan_for_transaction_tests(db_conn, "BO_ADD")

    month_key_open = "2024-09"
    payment_date_in_open_month = "2024-09-15"

    # Ensure books are open (either by default or explicitly setting)
    assert set_book_status(month_key_open, "open") is True

    success, message = add_transaction(
        transaction_type='Group Class',
        member_id=member_id,
        plan_id=plan_id,
        payment_date=payment_date_in_open_month,
        start_date=payment_date_in_open_month,
        amount_paid=100.00,
        payment_method="Cash"
    )

    assert success is True, f"add_transaction should succeed when books are open. Message: {message}"
    # The exact success message might vary, but a general check for "success" or similar could be done.
    # For now, checking boolean True is the primary concern.
    # assert "Transaction added successfully" in message # Example if checking message content

    # Verify transaction was added
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ? AND payment_date = ?",
                   (member_id, payment_date_in_open_month))
    count = cursor.fetchone()[0]
    assert count == 1, "Transaction was not added even though books were open."

def test_delete_transaction_when_books_open(db_conn):
    """Tests that delete_transaction succeeds when books for the transaction's month are open."""
    member_id, plan_id = _setup_member_and_plan_for_transaction_tests(db_conn, "BO_DEL")

    month_key_open = "2024-10"
    payment_date_in_open_month = "2024-10-10"

    # Add a transaction first
    add_success, _ = add_transaction(
        transaction_type='Group Class',
        member_id=member_id,
        plan_id=plan_id,
        payment_date=payment_date_in_open_month,
        start_date=payment_date_in_open_month,
        amount_paid=130.00,
        payment_method="Online"
    )
    assert add_success is True, "Failed to add initial transaction for the test."

    cursor = db_conn.cursor()
    cursor.execute("SELECT transaction_id FROM transactions WHERE member_id = ? AND payment_date = ?",
                   (member_id, payment_date_in_open_month))
    transaction_id_row = cursor.fetchone()
    assert transaction_id_row is not None, "Failed to retrieve the added transaction_id."
    transaction_id_to_delete = transaction_id_row[0]

    # Ensure books are open
    assert set_book_status(month_key_open, "open") is True

    # Attempt to delete the transaction
    delete_success, message = delete_transaction(transaction_id_to_delete)

    assert delete_success is True, f"delete_transaction should succeed when books are open. Message: {message}"
    # assert "Transaction deleted successfully" in message

    # Verify the transaction was deleted
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE transaction_id = ?", (transaction_id_to_delete,))
    count = cursor.fetchone()[0]
    assert count == 0, "Transaction was not deleted even though books were open."

import pytest
import pytest
import sqlite3
import os
from datetime import datetime, timedelta  # Ensure timedelta is imported

# Modules to be tested
from reporter.database_manager import DatabaseManager  # Updated import

# Module needed for setting up test DB
from reporter.database import create_database, seed_initial_plans

# Define the test database file
TEST_DB_DIR = "reporter/tests/test_data_dir"  # To avoid cluttering reporter/tests
TEST_DB_FILE = os.path.join(TEST_DB_DIR, "test_kranos_data.db")


@pytest.fixture
def db_manager_fixture():  # Renamed fixture
    """
    Pytest fixture to set up a test database and provide a DatabaseManager instance.
    - Creates all necessary tables in a test-specific DB file.
    - Seeds initial data like plans.
    - Provides a DatabaseManager instance connected to this test database.
    - Cleans up the database file after tests.
    """
    os.makedirs(TEST_DB_DIR, exist_ok=True)
    create_database(TEST_DB_FILE)  # Creates tables in TEST_DB_FILE

    conn = sqlite3.connect(TEST_DB_FILE)
    # Seed initial plans, as they are used in many tests
    seed_initial_plans(conn)

    db_manager = DatabaseManager(conn)
    yield db_manager  # Provide the manager instance

    # Teardown:
    conn.close()
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    if os.path.exists(TEST_DB_DIR) and not os.listdir(TEST_DB_DIR):
        os.rmdir(TEST_DB_DIR)


def test_add_member_successful(db_manager_fixture):  # Use new fixture
    """Tests successful addition of a new member."""
    name = "Test User"
    phone = "1234567890"

    add_success, add_message = db_manager_fixture.add_member_to_db(
        name, phone
    )  # Use db_manager_fixture
    assert (
        add_success is True
    ), f"add_member_to_db should return True on success. Message: {add_message}"

    # Verify directly in the database
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute(
        "SELECT client_name, phone, join_date FROM members WHERE phone = ?", (phone,)
    )
    member = cursor.fetchone()

    assert member is not None, "Member was not found in the database."
    assert member[0] == name, f"Expected name '{name}', got '{member[0]}'."
    assert member[1] == phone, f"Expected phone '{phone}', got '{member[1]}'."

    # Check join_date format (YYYY-MM-DD) and that it's today
    # Assert that join_date is initially NULL (or None when fetched)
    # as per new logic where join_date is set by first activity.
    assert (
        member[2] is None
    ), f"Expected join_date to be None/NULL initially, got '{member[2]}'."


def test_add_member_duplicate_phone(db_manager_fixture):  # Use new fixture
    """Tests adding a member with a phone number that already exists."""
    name1 = "Test User1"
    phone = "1112223333"  # Unique phone for this test

    add_success1, add_message1 = db_manager_fixture.add_member_to_db(
        name1, phone
    )  # Use db_manager_fixture
    assert (
        add_success1 is True
    ), f"First member addition should be successful. Message: {add_message1}"

    name2 = "Test User2"
    # Attempt to add another member with the same phone number
    add_success2, add_message2 = db_manager_fixture.add_member_to_db(
        name2, phone
    )  # Use db_manager_fixture
    assert (
        add_success2 is False
    ), f"Second member addition with duplicate phone should fail and return False. Message: {add_message2}"

    # Verify that only the first member was added
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT COUNT(*) FROM members WHERE phone = ?", (phone,))
    count = cursor.fetchone()[0]
    assert count == 1, "Only one member should exist with the given phone number."


def test_get_all_members_empty(db_manager_fixture):  # Use new fixture
    """Tests get_all_members when the database has no members."""
    members = db_manager_fixture.get_all_members()  # Use db_manager_fixture
    assert isinstance(members, list), "Should return a list."
    assert len(members) == 0, "Should return an empty list when no members are present."


def test_get_all_members_multiple(db_manager_fixture):  # Use new fixture
    """Tests get_all_members with multiple members, checking content and order."""
    # Add members out of alphabetical order to test sorting
    member_data = [
        ("Charlie Brown", "3330001111"),
        ("Alice Wonderland", "1110002222"),
        ("Bob The Builder", "2220003333"),
    ]

    for name, phone in member_data:
        add_success, add_message = db_manager_fixture.add_member_to_db(
            name, phone
        )  # Use db_manager_fixture
        assert (
            add_success is True
        ), f"Failed to add member {name}. Message: {add_message}"

    members = db_manager_fixture.get_all_members()  # Use db_manager_fixture
    assert len(members) == len(
        member_data
    ), f"Expected {len(member_data)} members, got {len(members)}."

    # Verify names are sorted
    expected_names_sorted = sorted([m[0] for m in member_data])
    actual_names = [
        m[1] for m in members
    ]  # m[1] is client_name in (member_id, client_name, phone, join_date)

    assert (
        actual_names == expected_names_sorted
    ), f"Members not sorted by name. Expected {expected_names_sorted}, got {actual_names}"

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
    # add_member_to_db sets join_date to NULL initially.
    assert (
        members[i][3] is None
    ), f"Expected join_date to be None for member {expected_name}, got {members[i][3]}"


def test_get_all_members_filter_by_name(db_manager_fixture):  # Use new fixture
    """Tests get_all_members filtering by name."""
    member_data = [
        ("John Doe", "1112223333"),
        ("Jane Doe", "4445556666"),
        ("John Smith", "7778889999"),
    ]
    for name, phone in member_data:
        add_success, add_message = db_manager_fixture.add_member_to_db(
            name, phone
        )  # Use db_manager_fixture
        assert (
            add_success is True
        ), f"Failed to add member {name} for filter test. Message: {add_message}"

    # Filter by full name
    members = db_manager_fixture.get_all_members(
        name_filter="John Doe"
    )  # Use db_manager_fixture
    assert len(members) == 1
    assert members[0][1] == "John Doe"

    # Filter by partial name (case-insensitive)
    members = db_manager_fixture.get_all_members(
        name_filter="john"
    )  # Use db_manager_fixture
    assert len(members) == 2
    member_names = sorted([m[1] for m in members])
    assert member_names == ["John Doe", "John Smith"]

    # Filter by a name not present
    members = db_manager_fixture.get_all_members(
        name_filter="NonExistent"
    )  # Use db_manager_fixture
    assert len(members) == 0


def test_get_all_members_filter_by_phone(db_manager_fixture):  # Use new fixture
    """Tests get_all_members filtering by phone."""
    member_data = [
        ("User One", "1234567890"),
        ("User Two", "0987654321"),
        ("User Three", "1230000000"),
    ]
    for name, phone in member_data:
        add_success, add_message = db_manager_fixture.add_member_to_db(
            name, phone
        )  # Use db_manager_fixture
        assert (
            add_success is True
        ), f"Failed to add member {name} for phone filter test. Message: {add_message}"

    # Filter by full phone number
    members = db_manager_fixture.get_all_members(
        phone_filter="1234567890"
    )  # Use db_manager_fixture
    assert len(members) == 1
    assert members[0][2] == "1234567890"

    # Filter by partial phone number
    members = db_manager_fixture.get_all_members(
        phone_filter="123"
    )  # Use db_manager_fixture
    assert len(members) == 2
    member_phones = sorted([m[2] for m in members])
    assert member_phones == ["1230000000", "1234567890"]

    # Filter by a phone number not present
    members = db_manager_fixture.get_all_members(
        phone_filter="111"
    )  # Use db_manager_fixture
    assert len(members) == 0


def test_get_all_members_filter_by_name_and_phone(
    db_manager_fixture,
):  # Use new fixture
    """Tests get_all_members filtering by both name and phone."""
    member_data = [
        ("Alice Johnson", "1112223333"),
        ("Bob Johnson", "4445556666"),
        ("Alice Smith", "1117778888"),
    ]
    for name, phone in member_data:
        add_success, add_message = db_manager_fixture.add_member_to_db(
            name, phone
        )  # Use db_manager_fixture
        assert (
            add_success is True
        ), f"Failed to add member {name} for combined filter test. Message: {add_message}"

    # Filter by name and phone (exact match)
    members = db_manager_fixture.get_all_members(
        name_filter="Alice Johnson", phone_filter="1112223333"
    )  # Use db_manager_fixture
    assert len(members) == 1
    assert members[0][1] == "Alice Johnson"
    assert members[0][2] == "1112223333"

    # Filter by partial name and partial phone
    members = db_manager_fixture.get_all_members(
        name_filter="Alice", phone_filter="111"
    )  # Use db_manager_fixture
    assert len(members) == 2
    member_details = sorted([(m[1], m[2]) for m in members])
    assert member_details == [
        ("Alice Johnson", "1112223333"),
        ("Alice Smith", "1117778888"),
    ]

    # Filter by name and phone (name matches, phone doesn't)
    members = db_manager_fixture.get_all_members(
        name_filter="Alice Johnson", phone_filter="000"
    )  # Use db_manager_fixture
    assert len(members) == 0

    # Filter by name and phone (phone matches, name doesn't)
    members = db_manager_fixture.get_all_members(
        name_filter="NonExistent", phone_filter="1112223333"
    )  # Use db_manager_fixture
    assert len(members) == 0


def test_get_all_plans(db_manager_fixture):  # Use new fixture
    """Tests retrieval of all plans, expecting the seeded default plans."""
    expected_plans_data = [
        ("Monthly - Unrestricted", 30),
        ("3 Months - Unrestricted", 90),
        ("Annual - Unrestricted", 365),
    ]

    plans_from_db = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    assert len(plans_from_db) == len(
        expected_plans_data
    ), f"Expected {len(expected_plans_data)} plans, got {len(plans_from_db)}"

    expected_plans_data.sort(key=lambda x: x[0])

    for i, expected_plan in enumerate(expected_plans_data):
        assert (
            plans_from_db[i][1] == expected_plan[0]
        ), f"Expected plan name '{expected_plan[0]}', got '{plans_from_db[i][1]}'"
        assert (
            plans_from_db[i][2] == expected_plan[1]
        ), f"Expected duration '{expected_plan[1]}' for plan '{plans_from_db[i][1]}', got '{plans_from_db[i][2]}'"
        assert (
            plans_from_db[i][3] == 1
        ), f"Expected plan '{expected_plan[0]}' to be active (1)."


def test_get_all_plans_no_plans(db_manager_fixture):  # Use new fixture
    """Tests get_all_plans when no plans are in the database."""
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("DELETE FROM plans")
    db_manager_fixture.conn.commit()  # Use db_manager_fixture.conn

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    assert isinstance(plans, list)
    assert len(plans) == 0


# --- Tests for get_all_plans_with_inactive ---


def test_get_all_plans_with_inactive_no_plans(db_manager_fixture):  # Use new fixture
    """Tests get_all_plans_with_inactive when no plans are in the database."""
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("DELETE FROM plans")
    db_manager_fixture.conn.commit()  # Use db_manager_fixture.conn
    plans = db_manager_fixture.get_all_plans_with_inactive()  # Use db_manager_fixture
    assert isinstance(plans, list)
    assert len(plans) == 0


def test_get_all_plans_with_inactive_only_active(db_manager_fixture):  # Use new fixture
    """Tests get_all_plans_with_inactive when only seeded (active) plans are present."""
    expected_seeded_plan_count = 3
    plans = db_manager_fixture.get_all_plans_with_inactive()  # Use db_manager_fixture
    assert len(plans) == expected_seeded_plan_count
    for plan in plans:
        assert plan[3] == 1


def test_get_all_plans_with_inactive_only_inactive(
    db_manager_fixture,
):  # Use new fixture
    """Tests get_all_plans_with_inactive when only inactive plans are present."""
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("DELETE FROM plans")
    db_manager_fixture.conn.commit()  # Use db_manager_fixture.conn

    plan_name1 = "Inactive Plan 1 - 10 Days"
    duration1 = 10
    add_success1, _, plan_id1 = db_manager_fixture.add_plan(
        plan_name1, duration1, is_active=False
    )  # Use db_manager_fixture
    plan_name2 = "Inactive Plan 2 - 20 Days"
    duration2 = 20
    add_success2, _, plan_id2 = db_manager_fixture.add_plan(
        plan_name2, duration2, is_active=False
    )  # Use db_manager_fixture
    assert add_success1 and plan_id1 is not None, "Failed to add Inactive Plan 1"
    assert add_success2 and plan_id2 is not None, "Failed to add Inactive Plan 2"

    plans = db_manager_fixture.get_all_plans_with_inactive()  # Use db_manager_fixture
    assert len(plans) == 2
    for plan in plans:
        assert plan[3] == 0


def test_get_all_plans_with_inactive_mixed(db_manager_fixture):  # Use new fixture
    """Tests get_all_plans_with_inactive with a mix of active and inactive plans."""
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("DELETE FROM plans")
    db_manager_fixture.conn.commit()  # Use db_manager_fixture.conn

    plan_name_active1 = "Active Plan Mix - 30 Days"
    duration_active1 = 30
    s1, _, _ = db_manager_fixture.add_plan(
        plan_name_active1, duration_active1, is_active=True
    )  # Use db_manager_fixture

    plan_name_inactive1 = "Inactive Plan Mix - 60 Days"
    duration_inactive1 = 60
    s2, _, _ = db_manager_fixture.add_plan(
        plan_name_inactive1, duration_inactive1, is_active=False
    )  # Use db_manager_fixture

    plan_name_active2 = "Another Active Mix - 90 Days"
    duration_active2 = 90
    s3, _, _ = db_manager_fixture.add_plan(
        plan_name_active2, duration_active2, is_active=True
    )  # Use db_manager_fixture

    assert s1, f"Failed to add {plan_name_active1}"
    assert s2, f"Failed to add {plan_name_inactive1}"
    assert s3, f"Failed to add {plan_name_active2}"

    plans = db_manager_fixture.get_all_plans_with_inactive()  # Use db_manager_fixture
    assert len(plans) == 3

    active_count = sum(1 for plan in plans if plan[3] == 1)
    inactive_count = sum(1 for plan in plans if plan[3] == 0)

    assert active_count == 2
    assert inactive_count == 1

    # Ensure order for assertion if it's not guaranteed by SQL (it is by name here)
    plan_names = sorted([p[1] for p in plans])
    expected_plan_names = sorted([plan_name_active1, plan_name_active2, plan_name_inactive1])
    assert plan_names == expected_plan_names


# --- Tests for get_plan_by_name_and_duration ---


def test_get_plan_by_name_and_duration_exists(db_manager_fixture):  # Use new fixture
    """Tests get_plan_by_name_and_duration for an existing plan."""
    # Seeded plan "Monthly - Unrestricted" has duration 30
    plan_name_seeded = "Monthly - Unrestricted"
    plan_duration_seeded = 30
    plan = db_manager_fixture.get_plan_by_name_and_duration(
        plan_name_seeded, plan_duration_seeded
    )  # Use db_manager_fixture
    assert plan is not None, f"Plan '{plan_name_seeded}' with duration {plan_duration_seeded} not found."
    assert plan[1] == plan_name_seeded
    assert plan[2] == plan_duration_seeded
    assert plan[3] == 1 # is_active


def test_get_plan_by_name_and_duration_not_exists(
    db_manager_fixture,
):  # Use new fixture
    """Tests get_plan_by_name_and_duration for a non-existent plan."""
    plan = db_manager_fixture.get_plan_by_name_and_duration(
        "NonExistent Plan XYZ", 10
    )  # Use db_manager_fixture
    assert plan is None


def test_get_plan_by_name_and_duration_wrong_duration(
    db_manager_fixture,
):  # Use new fixture
    """Tests get_plan_by_name_and_duration for an existing name but wrong duration."""
    plan = db_manager_fixture.get_plan_by_name_and_duration(
        "Monthly - Unrestricted", 2
    )  # Use db_manager_fixture
    assert plan is None


# --- Tests for get_or_create_plan_id ---


def test_get_or_create_plan_id_get_existing(db_manager_fixture):  # Use new fixture
    """Tests get_or_create_plan_id for an existing plan."""
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute(
        "SELECT plan_id, plan_name, duration_days FROM plans WHERE plan_name = 'Annual - Unrestricted'"
    )
    existing_plan_row = cursor.fetchone()
    assert existing_plan_row is not None
    existing_plan_id, existing_plan_name, existing_duration_days = existing_plan_row

    retrieved_id = db_manager_fixture.get_or_create_plan_id(
        existing_plan_name, existing_duration_days
    )  # Use db_manager_fixture
    assert retrieved_id == existing_plan_id

    cursor.execute("SELECT COUNT(*) FROM plans")
    count = cursor.fetchone()[0]
    assert count == 3


def test_get_or_create_plan_id_create_new(db_manager_fixture):  # Use new fixture
    """Tests get_or_create_plan_id for creating a new plan."""
    base_plan_name = "Super Duper Plan"
    new_plan_duration = 45
    formatted_new_plan_name = f"{base_plan_name} - {new_plan_duration} Days"

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT plan_id FROM plans WHERE plan_name = ?", (formatted_new_plan_name,))
    assert cursor.fetchone() is None, f"Plan '{formatted_new_plan_name}' should not exist yet."

    new_plan_id = db_manager_fixture.get_or_create_plan_id(
        formatted_new_plan_name, new_plan_duration
    )  # Use db_manager_fixture
    assert new_plan_id is not None

    cursor.execute(
        "SELECT plan_name, duration_days, is_active FROM plans WHERE plan_id = ?",
        (new_plan_id,),
    )
    created_plan = cursor.fetchone()
    assert created_plan is not None
    assert created_plan[0] == formatted_new_plan_name
    assert created_plan[1] == new_plan_duration
    assert created_plan[2] == 1

    cursor.execute("SELECT COUNT(*) FROM plans")
    count = cursor.fetchone()[0]
    assert count == 4


def test_add_transaction_group_class(db_manager_fixture):  # Use new fixture
    """Tests adding a group class transaction and verifies data including end_date calculation."""
    member_name = "Membership User"
    member_phone = "9998887777"
    add_mem_success, add_mem_message = db_manager_fixture.add_member_to_db(
        member_name, member_phone
    )  # Use db_manager_fixture
    assert add_mem_success is True, f"Failed to add member: {add_mem_message}"

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Test member not found after adding."
    member_id = member_id_row[0]

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    assert len(plans) > 0, "No plans found. Ensure plans are seeded for this test."
    test_plan = plans[0]
    plan_id = test_plan[0]
    # plan_duration_days = test_plan[2] # Not used in this test logic directly

    transaction_date_str = "2024-01-15"
    start_date_str = "2024-01-20"
    manual_end_date_str = "2024-02-28"
    amount = 75.50
    payment_method = "Credit Card"

    success, _ = db_manager_fixture.add_transaction(  # Use db_manager_fixture
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=transaction_date_str,
        start_date=start_date_str,
        end_date=manual_end_date_str,
        amount=amount,
        payment_method=payment_method,
    )
    assert (
        success is True
    ), "add_transaction for Group Class should return True on success."  # Check success tuple

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute(
        "SELECT member_id, plan_id, transaction_date, start_date, end_date, amount, payment_method, transaction_type "
        "FROM transactions WHERE member_id = ? AND transaction_type = 'Group Class'",
        (member_id,),
    )
    transaction_record = cursor.fetchone()
    assert transaction_record is not None, "Group Class transaction record not found."

    (
        t_member_id,
        t_plan_id,
        t_transaction_date,
        t_start_date,
        t_end_date,
        t_amount,
        t_payment_method,
        t_transaction_type,
    ) = transaction_record

    assert t_member_id == member_id
    assert t_plan_id == plan_id
    assert t_transaction_date == transaction_date_str
    assert t_start_date == start_date_str
    assert t_amount == amount
    assert t_payment_method == payment_method
    assert t_transaction_type == "Group Class"

    assert (
        t_end_date == manual_end_date_str
    ), f"End date mismatch. Expected manual {manual_end_date_str}, got {t_end_date}."


def test_get_memberships_for_member_none(db_manager_fixture):  # Use new fixture
    """Tests retrieving memberships for a member who has none."""
    add_success, add_message = db_manager_fixture.add_member_to_db(
        "Member C NoHistory", "3003003003"
    )  # Use db_manager_fixture
    assert add_success is True, f"Failed to add member C NoHistory: {add_message}"

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = '3003003003'")
    member_c_id = cursor.fetchone()[0]

    history_c = db_manager_fixture.get_all_activity_for_member(
        member_c_id
    )  # Use db_manager_fixture
    assert len(history_c) == 0, "Member C should have no activity history."


# --- New and Updated Tests ---


def test_add_transaction_group_class_invalid_plan_id(
    db_manager_fixture,
):  # Use new fixture
    """Tests add_transaction for a 'Group Class' with an invalid plan_id."""
    member_name = "Transaction Test User"
    member_phone = "TRX001"
    add_mem_success, add_mem_message = db_manager_fixture.add_member_to_db(
        member_name, member_phone
    )  # Use db_manager_fixture
    assert add_mem_success is True, f"Failed to add member: {add_mem_message}"
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id = cursor.fetchone()[0]

    invalid_plan_id = 99999
    transaction_date_str = "2024-03-10"
    start_date_str = "2024-03-10"
    amount = 50.00
    payment_method = "Cash"

    success, _ = db_manager_fixture.add_transaction(  # Use db_manager_fixture
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=invalid_plan_id,
        transaction_date=transaction_date_str,
        start_date=start_date_str,
        amount=amount,
        payment_method=payment_method,
    )
    assert (
        success is False
    ), "add_transaction should return False for an invalid plan_id."  # Check success tuple

    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE member_id = ?", (member_id,)
    )
    count = cursor.fetchone()[0]
    assert count == 0, "No transaction should have been added to the database."


def test_add_transaction_personal_training(db_manager_fixture):  # Use new fixture
    """Tests adding a Personal Training transaction and verifies the inserted data."""
    member_name = "PT User"
    member_phone = "PT123456"
    add_mem_success, add_mem_message = db_manager_fixture.add_member_to_db(
        member_name, member_phone
    )  # Use db_manager_fixture
    assert add_mem_success is True, f"Failed to add member: {add_mem_message}"

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Test member for PT booking not found."
    member_id = member_id_row[0]

    start_date_str = "2024-03-01"
    manual_pt_end_date_str = "2024-03-31"
    sessions = 10
    amount = 500.00

    success, _ = db_manager_fixture.add_transaction(  # Use db_manager_fixture
        transaction_type="Personal Training",
        member_id=member_id,
        start_date=start_date_str,
        end_date=manual_pt_end_date_str,
        amount=amount,
        sessions=sessions,
    )
    assert (
        success is True
    ), "add_transaction for PT should return True on success."  # Check success tuple

    cursor.execute(
        "SELECT member_id, start_date, end_date, sessions, amount, transaction_type FROM transactions WHERE member_id = ? AND transaction_type = 'Personal Training'",
        (member_id,),
    )
    pt_record = cursor.fetchone()
    assert pt_record is not None, "PT transaction record not found."

    (
        db_member_id,
        db_start_date,
        db_end_date,
        db_sessions,
        db_amount,
        db_transaction_type,
    ) = pt_record
    assert db_member_id == member_id
    assert db_start_date == start_date_str
    assert (
        db_end_date == manual_pt_end_date_str
    ), f"PT end date mismatch. Expected {manual_pt_end_date_str}, got {db_end_date}."
    assert db_sessions == sessions
    assert db_amount == amount
    assert db_transaction_type == "Personal Training"

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    member_join_date = cursor.fetchone()[0]
    assert (
        member_join_date == start_date_str
    ), "Member join_date should be updated to PT start_date."


def test_get_all_activity_for_member(db_manager_fixture):  # Use new fixture
    """Tests retrieval of all activities (group and PT) for a member."""
    member_name = "Activity User"
    member_phone = "ACT001"
    add_mem_success, add_mem_message = db_manager_fixture.add_member_to_db(
        member_name, member_phone
    )  # Use db_manager_fixture
    assert add_mem_success is True, f"Failed to add member: {add_mem_message}"
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id = cursor.fetchone()[0]

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    assert len(plans) > 0, "No plans found."
    test_plan = plans[0]
    plan_id = test_plan[0]
    plan_name = test_plan[1]

    gm_start_date = "2024-02-15"
    gm_transaction_date = "2024-02-10"
    gm_amount = 120.0
    gm_method = "Visa"
    add_gm_success, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=gm_transaction_date,
        start_date=gm_start_date,
        amount=gm_amount,
        payment_method=gm_method,
    )  # Use db_manager_fixture
    assert add_gm_success

    pt_start_date = "2024-03-05"
    pt_sessions = 8
    pt_amount = 450.0
    add_pt_success, _ = db_manager_fixture.add_transaction(
        transaction_type="Personal Training",
        member_id=member_id,
        start_date=pt_start_date,
        sessions=pt_sessions,
        amount=pt_amount,
        transaction_date=pt_start_date,
    )  # Use db_manager_fixture
    assert add_pt_success

    pt_early_start_date = "2024-01-20"
    pt_early_sessions = 5
    pt_early_amount = 300.0
    add_early_pt_success, _ = db_manager_fixture.add_transaction(
        transaction_type="Personal Training",
        member_id=member_id,
        start_date=pt_early_start_date,
        sessions=pt_early_sessions,
        amount=pt_early_amount,
        transaction_date=pt_early_start_date,
    )  # Use db_manager_fixture
    assert add_early_pt_success

    activities = db_manager_fixture.get_all_activity_for_member(
        member_id
    )  # Use db_manager_fixture
    assert len(activities) == 3, "Expected 3 activities for the member."

    # The get_all_activity_for_member sorts by start_date DESC.
    # Column indices for get_all_activity_for_member:
    # 0: transaction_type, 1: plan_name/PT Session, 2: transaction_date, 3: start_date,
    # 4: end_date, 5: amount, 6: payment_method/sessions, 7: transaction_id

    assert activities[0][3] == pt_start_date  # Check start_date of latest PT
    assert activities[1][3] == gm_start_date  # Check start_date of Group Class
    assert activities[2][3] == pt_early_start_date  # Check start_date of earliest PT

    pt_latest_activity = activities[0]
    assert pt_latest_activity[0] == "Personal Training"
    assert pt_latest_activity[1] == "PT Session"  # plan_name (becomes 'PT Session')
    assert (
        pt_latest_activity[2] == pt_start_date
    )  # transaction_date (now same as start_date for PT)
    assert pt_latest_activity[3] == pt_start_date  # start_date
    assert pt_latest_activity[4] is None  # end_date
    assert pt_latest_activity[5] == pt_amount  # amount
    assert (
        pt_latest_activity[6] == f"{pt_sessions} sessions"
    )  # payment_method (becomes sessions for PT)
    assert pt_latest_activity[7] is not None  # transaction_id

    gm_activity = activities[1]
    assert gm_activity[0] == "Group Class"
    assert gm_activity[1] == plan_name  # plan_name
    assert gm_activity[2] == gm_transaction_date  # transaction_date
    assert gm_activity[3] == gm_start_date  # start_date
    assert gm_activity[4] is not None  # end_date (calculated for Group Class)
    assert gm_activity[5] == gm_amount  # amount
    assert gm_activity[6] == gm_method  # payment_method
    assert gm_activity[7] is not None  # transaction_id

    pt_early_activity = activities[2]
    assert pt_early_activity[0] == "Personal Training"
    assert pt_early_activity[1] == "PT Session"
    assert pt_early_activity[2] == pt_early_start_date  # transaction_date
    assert pt_early_activity[3] == pt_early_start_date  # start_date
    assert pt_early_activity[4] is None
    assert pt_early_activity[5] == pt_early_amount  # amount
    assert pt_early_activity[6] == f"{pt_early_sessions} sessions"
    assert pt_early_activity[7] is not None


def test_get_pending_renewals(db_manager_fixture):  # Use new fixture
    """Tests retrieval of pending renewals within the next 30 days."""
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM members")
    cursor.execute(
        "DELETE FROM sqlite_sequence WHERE name IN ('members', 'transactions')"
    )
    db_manager_fixture.conn.commit()  # Use db_manager_fixture.conn

    member_data = {
        "User A": {"phone": "R001", "id": None, "name": "User A"},
        "User B": {"phone": "R002", "id": None, "name": "User B"},
        "User C": {"phone": "R003", "id": None, "name": "User C"},
        "User D": {"phone": "N001", "id": None, "name": "User D"},
        "User E": {"phone": "P001", "id": None, "name": "User E"},
    }
    for name, data in member_data.items():
        add_success, add_message = db_manager_fixture.add_member_to_db(
            name, data["phone"]
        )  # Use db_manager_fixture
        assert add_success is True, f"Failed to add member {name}: {add_message}"
        cursor.execute(
            "SELECT member_id FROM members WHERE phone = ?", (data["phone"],)
        )
        member_data[name]["id"] = cursor.fetchone()[0]

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    assert len(plans) > 0, "Need at least one plan for testing."
    test_plan = plans[0]
    plan_id = test_plan[0]
    plan_name = test_plan[1]

    target_year = 2025
    target_month = 7
    target_month_str = f"{target_year:04d}-{target_month:02d}"

    transactions_data = [
        (member_data["User A"], f"{target_year:04d}-{target_month:02d}-05", True),
        (member_data["User B"], f"{target_year:04d}-{target_month:02d}-15", True),
        (member_data["User C"], f"{target_year:04d}-{target_month:02d}-28", True),
        (member_data["User D"], f"{target_year:04d}-{target_month-1:02d}-25", False),
        (member_data["User E"], f"{target_year:04d}-{target_month+1:02d}-02", False),
        (member_data["User A"], f"{target_year+1:04d}-{target_month:02d}-05", False),
    ]

    expected_renewals_details = []
    common_start_date = f"{target_year:04d}-{target_month:02d}-01"

    for member_info, end_date_str, should_be_included in transactions_data:
        if should_be_included:
            cursor.execute(
                "UPDATE members SET is_active = 1 WHERE member_id = ?",
                (member_info["id"],),
            )
    db_manager_fixture.conn.commit()  # Use db_manager_fixture.conn

    for member_info, end_date_str, should_be_included in transactions_data:
        add_transaction_success, msg = (
            db_manager_fixture.add_transaction(  # Use db_manager_fixture
                transaction_type="Group Class",
                member_id=member_info["id"],
                plan_id=plan_id,
                transaction_date=common_start_date,
                start_date=common_start_date,
                end_date=end_date_str,
                amount=50,
                payment_method="CashTest",
            )
        )
        assert (
            add_transaction_success
        ), f"Failed to add transaction for {member_info['name']} ending {end_date_str}. Error: {msg}"

        if should_be_included:
            expected_renewals_details.append(
                {
                    "client_name": member_info["name"],
                    "phone": member_info["phone"],
                    "plan_name": plan_name,
                    "end_date": end_date_str,
                }
            )

    expected_renewals_details.sort(key=lambda x: (x["end_date"], x["client_name"]))

    actual_renewals = db_manager_fixture.get_pending_renewals(
        target_year, target_month
    )  # Use db_manager_fixture

    assert len(actual_renewals) == len(
        expected_renewals_details
    ), f"Expected {len(expected_renewals_details)} renewals for {target_month_str}, but got {len(actual_renewals)}. Actual: {actual_renewals}"

    for i, expected in enumerate(expected_renewals_details):
        actual_record = actual_renewals[i]
        assert (
            actual_record[0] == expected["client_name"]
        ), f"Mismatch in client_name at index {i}"
        assert actual_record[1] == expected["phone"], f"Mismatch in phone at index {i}"
        assert (
            actual_record[2] == expected["plan_name"]
        ), f"Mismatch in plan_name at index {i}"
        assert (
            actual_record[3] == expected["end_date"]
        ), f"Mismatch in end_date at index {i}"


def test_get_pending_renewals_none_when_no_relevant_data(
    db_manager_fixture,
):  # Use new fixture
    """Tests get_pending_renewals returns empty list when no transactions are in the 30-day window."""
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM members")
    db_manager_fixture.conn.commit()  # Use db_manager_fixture.conn

    add_mem_success, _ = db_manager_fixture.add_member_to_db(
        "Test User No Renew", "TNR001"
    )  # Use db_manager_fixture
    assert add_mem_success
    cursor.execute("SELECT member_id FROM members WHERE phone = 'TNR001'")
    member_id = cursor.fetchone()[0]

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    plan_id = plans[0][0]

    today_obj = datetime.today().date()

    end_date_future = (today_obj + timedelta(days=100)).strftime("%Y-%m-%d")
    add_future_success, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=today_obj.strftime("%Y-%m-%d"),
        start_date=today_obj.strftime("%Y-%m-%d"),
        end_date=end_date_future,
        amount=50,
    )  # Use db_manager_fixture
    assert add_future_success

    end_date_past = (today_obj - timedelta(days=100)).strftime("%Y-%m-%d")
    add_past_success, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=today_obj.strftime("%Y-%m-%d"),
        start_date=today_obj.strftime("%Y-%m-%d"),
        end_date=end_date_past,
        amount=50,
    )  # Use db_manager_fixture
    assert add_past_success

    renewals = db_manager_fixture.get_pending_renewals(
        year=1900, month=1
    )  # Use db_manager_fixture
    assert (
        len(renewals) == 0
    ), "Expected no renewals when all end_dates are outside the 30-day window."


def test_get_finance_report(db_manager_fixture):  # Use new fixture
    """Tests calculation of total revenue for a specific month."""
    add_s1, _ = db_manager_fixture.add_member_to_db(
        "Finance User1", "F001"
    )  # Use db_manager_fixture
    assert add_s1 is True
    add_s2, _ = db_manager_fixture.add_member_to_db(
        "Finance User2", "F002"
    )  # Use db_manager_fixture
    assert add_s2 is True
    add_s3, _ = db_manager_fixture.add_member_to_db(
        "Finance User3", "F003"
    )  # Use db_manager_fixture
    assert add_s3 is True

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = 'F001'")
    member_f1_id = cursor.fetchone()[0]
    cursor.execute("SELECT member_id FROM members WHERE phone = 'F002'")
    member_f2_id = cursor.fetchone()[0]
    cursor.execute("SELECT member_id FROM members WHERE phone = 'F003'")
    member_f3_id = cursor.fetchone()[0]

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    assert len(plans) > 0, "Need at least one plan."
    plan_any = plans[0]

    today = datetime.today()
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    prev_month = last_day_previous_month.month
    prev_year = last_day_previous_month.year

    pm_date1_str = last_day_previous_month.replace(day=10).strftime("%Y-%m-%d")
    pm_date2_str = last_day_previous_month.replace(day=20).strftime("%Y-%m-%d")
    cm_date_str = today.replace(day=5).strftime("%Y-%m-%d")
    month_before_prev_month_end = last_day_previous_month.replace(day=1) - timedelta(
        days=1
    )
    bpm_date_str = month_before_prev_month_end.replace(day=15).strftime("%Y-%m-%d")

    add_tx1_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_f1_id,
        plan_id=plan_any[0],
        transaction_date=pm_date1_str,
        start_date=pm_date1_str,
        amount=100.00,
        payment_method="CashFin1",
    )  # Use db_manager_fixture
    assert add_tx1_s
    add_tx2_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_f2_id,
        plan_id=plan_any[0],
        transaction_date=pm_date2_str,
        start_date=pm_date2_str,
        amount=50.50,
        payment_method="CardFin2",
    )  # Use db_manager_fixture
    assert add_tx2_s
    add_tx3_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_f1_id,
        plan_id=plan_any[0],
        transaction_date=cm_date_str,
        start_date=cm_date_str,
        amount=75.00,
        payment_method="CashFin3",
    )  # Use db_manager_fixture
    assert add_tx3_s
    add_tx4_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_f3_id,
        plan_id=plan_any[0],
        transaction_date=bpm_date_str,
        start_date=bpm_date_str,
        amount=25.00,
        payment_method="CashFin4",
    )  # Use db_manager_fixture
    assert add_tx4_s

    total_revenue_prev_month = db_manager_fixture.get_finance_report(
        prev_year, prev_month
    )  # Use db_manager_fixture

    assert (
        total_revenue_prev_month == 150.50
    ), f"Expected total revenue for {prev_year}-{prev_month} to be 150.50, got {total_revenue_prev_month}"


def test_get_finance_report_no_transactions(db_manager_fixture):  # Use new fixture
    """Tests get_finance_report for a month with no transactions."""
    today = datetime.today()
    future_date = today + timedelta(days=365 * 2)
    future_year = future_date.year
    future_month = future_date.month

    total_revenue_future = db_manager_fixture.get_finance_report(
        future_year, future_month
    )  # Use db_manager_fixture
    assert (
        total_revenue_future == 0.0
    ), f"Expected 0.0 for a month with no transactions ({future_year}-{future_month}), got {total_revenue_future}"
    total_revenue_ancient = db_manager_fixture.get_finance_report(
        1900, 1
    )  # Use db_manager_fixture
    assert (
        total_revenue_ancient == 0.0
    ), f"Expected 0.0 for an ancient month (1900-01), got {total_revenue_ancient}"


def test_get_finance_report_with_pt_bookings(db_manager_fixture):  # Use new fixture
    """Tests get_finance_report including revenue from PT bookings."""
    add_s1, _ = db_manager_fixture.add_member_to_db(
        "Finance User PT1", "FPT001"
    )  # Use db_manager_fixture
    assert add_s1 is True
    add_s2, _ = db_manager_fixture.add_member_to_db(
        "Finance User PT2", "FPT002"
    )  # Use db_manager_fixture
    assert add_s2 is True

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = 'FPT001'")
    member_f1_id = cursor.fetchone()[0]
    cursor.execute("SELECT member_id FROM members WHERE phone = 'FPT002'")
    member_f2_id = cursor.fetchone()[0]

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    plan_any = plans[0]

    today = datetime.today()
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    target_year = last_day_previous_month.year
    target_month = last_day_previous_month.month

    target_month_date1 = last_day_previous_month.replace(day=10).strftime("%Y-%m-%d")
    target_month_date2 = last_day_previous_month.replace(day=20).strftime("%Y-%m-%d")
    other_month_date = (
        last_day_previous_month.replace(day=1) - timedelta(days=15)
    ).strftime("%Y-%m-%d")

    add_gm1_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_f1_id,
        plan_id=plan_any[0],
        transaction_date=target_month_date1,
        start_date=target_month_date1,
        amount=100.00,
        payment_method="GM_Cash1",
    )  # Use db_manager_fixture
    assert add_gm1_s
    add_gm2_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_f2_id,
        plan_id=plan_any[0],
        transaction_date=other_month_date,
        start_date=other_month_date,
        amount=50.00,
        payment_method="GM_Cash2",
    )  # Use db_manager_fixture
    assert add_gm2_s

    add_pt1_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Personal Training",
        member_id=member_f1_id,
        transaction_date=target_month_date2,
        start_date=target_month_date2,
        sessions=10,
        amount=200.00,
    )  # Use db_manager_fixture
    assert add_pt1_s
    add_pt2_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Personal Training",
        member_id=member_f2_id,
        transaction_date=target_month_date1,
        start_date=target_month_date1,
        sessions=5,
        amount=150.00,
    )  # Use db_manager_fixture
    assert add_pt2_s
    add_pt3_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Personal Training",
        member_id=member_f1_id,
        transaction_date=other_month_date,
        start_date=other_month_date,
        sessions=8,
        amount=180.00,
    )  # Use db_manager_fixture
    assert add_pt3_s

    expected_total_revenue = 100.00 + 350.00

    actual_total_revenue = db_manager_fixture.get_finance_report(
        target_year, target_month
    )  # Use db_manager_fixture
    assert (
        actual_total_revenue == expected_total_revenue
    ), f"Expected total revenue {expected_total_revenue} for {target_year}-{target_month}, got {actual_total_revenue}"


def test_join_date_standardization_new_member_then_group_membership(
    db_manager_fixture,
):  # Use new fixture
    """Scenario 1: New member, then group membership. Join date becomes GM start date."""
    member_phone = "JD_GM01"
    add_mem_s, _ = db_manager_fixture.add_member_to_db(
        "JoinDate User GM", member_phone
    )  # Use db_manager_fixture
    assert add_mem_s is True

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute(
        "SELECT member_id, join_date FROM members WHERE phone = ?", (member_phone,)
    )
    member_id, initial_join_date = cursor.fetchone()
    assert initial_join_date is None, "Join date should be NULL on initial member add."

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    plan_id = plans[0][0]
    gm_start_date = "2024-04-01"
    add_tx_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=gm_start_date,
        start_date=gm_start_date,
        amount=50,
        payment_method="Cash",
    )  # Use db_manager_fixture
    assert add_tx_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    updated_join_date = cursor.fetchone()[0]
    assert (
        updated_join_date == gm_start_date
    ), "Join date should be updated to group membership start date."


def test_join_date_standardization_new_member_then_pt_booking(
    db_manager_fixture,
):  # Use new fixture
    """Scenario 2: New member, then PT booking. Join date becomes PT start date."""
    member_phone = "JD_PT01"
    add_mem_s, _ = db_manager_fixture.add_member_to_db(
        "JoinDate User PT", member_phone
    )  # Use db_manager_fixture
    assert add_mem_s is True

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute(
        "SELECT member_id, join_date FROM members WHERE phone = ?", (member_phone,)
    )
    member_id, initial_join_date = cursor.fetchone()
    assert initial_join_date is None, "Join date should be NULL on initial member add."

    pt_start_date = "2024-05-10"
    add_tx_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Personal Training",
        member_id=member_id,
        start_date=pt_start_date,
        sessions=10,
        amount=300,
        transaction_date=pt_start_date,
    )  # Use db_manager_fixture
    assert add_tx_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    updated_join_date = cursor.fetchone()[0]
    assert (
        updated_join_date == pt_start_date
    ), "Join date should be updated to PT booking start date."


def test_join_date_standardization_existing_member_earlier_activity(
    db_manager_fixture,
):  # Use new fixture
    """Scenario 3: Existing member, new activity earlier than current join_date."""
    member_phone = "JD_EARLY01"
    add_mem_s, _ = db_manager_fixture.add_member_to_db(
        "JoinDate User Early", member_phone
    )  # Use db_manager_fixture
    assert add_mem_s is True
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id = cursor.fetchone()[0]

    initial_activity_date = "2023-03-15"
    add_tx1_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Personal Training",
        member_id=member_id,
        start_date=initial_activity_date,
        sessions=5,
        amount=250,
        transaction_date=initial_activity_date,
    )  # Use db_manager_fixture
    assert add_tx1_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    current_join_date = cursor.fetchone()[0]
    assert current_join_date == initial_activity_date

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    plan_id = plans[0][0]
    earlier_gm_start_date = "2023-03-01"
    add_tx2_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=earlier_gm_start_date,
        start_date=earlier_gm_start_date,
        amount=50,
        payment_method="Cash",
    )  # Use db_manager_fixture
    assert add_tx2_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    updated_join_date = cursor.fetchone()[0]
    assert (
        updated_join_date == earlier_gm_start_date
    ), "Join date should be updated to the earlier group membership start date."


def test_join_date_standardization_existing_member_later_activity(
    db_manager_fixture,
):  # Use new fixture
    """Scenario 4: Existing member, new activity later than current join_date."""
    member_phone = "JD_LATER01"
    add_mem_s, _ = db_manager_fixture.add_member_to_db(
        "JoinDate User Later", member_phone
    )  # Use db_manager_fixture
    assert add_mem_s is True
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id = cursor.fetchone()[0]

    initial_activity_date = "2023-04-01"
    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    plan_id = plans[0][0]
    add_tx1_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=initial_activity_date,
        start_date=initial_activity_date,
        amount=60,
        payment_method="Card",
    )  # Use db_manager_fixture
    assert add_tx1_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    current_join_date = cursor.fetchone()[0]
    assert current_join_date == initial_activity_date

    later_pt_start_date = "2023-04-10"
    add_tx2_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Personal Training",
        member_id=member_id,
        start_date=later_pt_start_date,
        sessions=8,
        amount=280,
        transaction_date=later_pt_start_date,
    )  # Use db_manager_fixture
    assert add_tx2_s

    cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
    final_join_date = cursor.fetchone()[0]
    assert (
        final_join_date == initial_activity_date
    ), "Join date should remain the earlier date."


# --- Tests for delete operations ---


def test_deactivate_member(db_manager_fixture):  # Use new fixture
    """Tests deactivating a member and ensures their transactions are NOT deleted, and member is marked inactive."""
    member_name = "Member to Deactivate"
    member_phone = "DEACT001"
    add_mem_s, add_mem_msg = db_manager_fixture.add_member_to_db(
        member_name, member_phone
    )  # Use db_manager_fixture
    assert (
        add_mem_s is True
    ), f"Failed to add member for deactivation test: {add_mem_msg}"
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Failed to add member for deactivation test."
    member_id = member_id_row[0]

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    assert len(plans) > 0, "No plans available to create transactions."
    plan_id = plans[0][0]
    initial_number_of_transactions_added = 2

    db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date="2024-01-01",
        start_date="2024-01-01",
        amount=50,
        payment_method="Cash",
    )  # Use db_manager_fixture
    db_manager_fixture.add_transaction(
        transaction_type="Personal Training",
        member_id=member_id,
        start_date="2024-01-05",
        sessions=5,
        amount=100,
        transaction_date="2024-01-05",
    )  # Use db_manager_fixture

    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE member_id = ?", (member_id,)
    )
    assert (
        cursor.fetchone()[0] == initial_number_of_transactions_added
    ), "Failed to add initial transactions for the member."

    success, message = db_manager_fixture.deactivate_member(
        member_id
    )  # Use db_manager_fixture
    assert success is True
    assert message == "Member deactivated successfully."

    cursor.execute(
        "SELECT client_name, phone, is_active FROM members WHERE member_id = ?",
        (member_id,),
    )
    deactivated_member_record = cursor.fetchone()
    assert (
        deactivated_member_record is not None
    ), "Member should still exist in the database after deactivation."
    assert deactivated_member_record[0] == member_name
    assert deactivated_member_record[1] == member_phone
    assert (
        deactivated_member_record[2] == 0
    ), f"Member's is_active flag should be 0, but was {deactivated_member_record[2]}."

    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE member_id = ?", (member_id,)
    )
    transaction_count = cursor.fetchone()[0]
    assert (
        transaction_count == initial_number_of_transactions_added
    ), "Transactions for the deactivated member should not have been deleted."


def test_delete_transaction(db_manager_fixture):  # Use new fixture
    """Tests deleting a single transaction and ensures the member still exists."""
    member_name = "Transaction Test Member"
    member_phone = "TRXDEL001"
    add_mem_s, add_mem_msg = db_manager_fixture.add_member_to_db(
        member_name, member_phone
    )  # Use db_manager_fixture
    assert (
        add_mem_s is True
    ), f"Failed to add member for transaction deletion test: {add_mem_msg}"
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert (
        member_id_row is not None
    ), "Failed to add member for transaction deletion test."
    member_id = member_id_row[0]

    plans = db_manager_fixture.get_all_plans()  # Use db_manager_fixture
    plan_id = plans[0][0]
    db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date="2024-02-01",
        start_date="2024-02-01",
        amount=60,
        payment_method="Card",
    )  # Use db_manager_fixture

    cursor.execute(
        "SELECT transaction_id FROM transactions WHERE member_id = ? ORDER BY transaction_id DESC LIMIT 1",
        (member_id,),
    )
    transaction_id_row = cursor.fetchone()
    assert transaction_id_row is not None, "Failed to retrieve the added transaction."
    transaction_id_to_delete = transaction_id_row[0]

    db_manager_fixture.add_transaction(
        transaction_type="Personal Training",
        member_id=member_id,
        start_date="2024-02-05",
        sessions=3,
        amount=70,
        transaction_date="2024-02-05",
    )  # Use db_manager_fixture

    cursor.execute(
        "SELECT transaction_id FROM transactions WHERE member_id = ? AND transaction_type = 'Personal Training'",
        (member_id,),
    )
    other_transaction_id_row = cursor.fetchone()
    assert other_transaction_id_row is not None
    other_transaction_id = other_transaction_id_row[0]

    db_manager_fixture.delete_transaction(
        transaction_id_to_delete
    )  # Use db_manager_fixture

    cursor.execute(
        "SELECT * FROM transactions WHERE transaction_id = ?",
        (transaction_id_to_delete,),
    )
    assert cursor.fetchone() is None, "The specified transaction was not deleted."

    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE member_id = ?", (member_id,)
    )
    assert (
        cursor.fetchone()[0] == 1
    ), "Other transactions for the member were unintentionally deleted."
    cursor.execute(
        "SELECT transaction_id FROM transactions WHERE member_id = ?", (member_id,)
    )
    remaining_transaction_id = cursor.fetchone()[0]
    assert (
        remaining_transaction_id == other_transaction_id
    ), "The wrong transaction was deleted."

    cursor.execute("SELECT * FROM members WHERE member_id = ?", (member_id,))
    assert cursor.fetchone() is not None, "Member was unintentionally deleted."


def test_delete_plan(db_manager_fixture):  # Use new fixture
    """Tests deleting a plan, including cases where it's in use."""
    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn

    base_plan_name_unused = "Temporary Test Plan Unused"
    plan_duration_unused = 15
    formatted_plan_name_unused = f"{base_plan_name_unused} - {plan_duration_unused} Days"
    add_s_unused, msg_unused_add, unused_plan_id_val = db_manager_fixture.add_plan(
        formatted_plan_name_unused, plan_duration_unused, is_active=True
    )  # Use db_manager_fixture
    assert (
        add_s_unused and unused_plan_id_val is not None
    ), f"Failed to add unused plan for deletion test: {msg_unused_add}"

    result_unused, message_unused = db_manager_fixture.delete_plan(
        unused_plan_id_val
    )  # Use db_manager_fixture
    assert (
        result_unused is True
    ), f"delete_plan should return True for unused plan. Message: {message_unused}"
    assert (
        message_unused == "Plan deleted successfully."
    ), f"Unexpected message: {message_unused}"

    cursor.execute("SELECT * FROM plans WHERE plan_id = ?", (unused_plan_id_val,))
    assert (
        cursor.fetchone() is None
    ), "Unused plan was not actually deleted from the database."

    base_plan_name_used = "Temporary Test Plan Used"
    plan_duration_used = 45
    formatted_plan_name_used = f"{base_plan_name_used} - {plan_duration_used} Days"
    add_s_used, msg_used_add, used_plan_id_val = db_manager_fixture.add_plan(
        formatted_plan_name_used, plan_duration_used, is_active=True
    )  # Use db_manager_fixture
    assert (
        add_s_used and used_plan_id_val is not None
    ), f"Failed to add used plan '{formatted_plan_name_used}' for deletion test: {msg_used_add}"

    member_name = "Plan User"
    member_phone = "PLANUSER01"
    add_mem_s, add_mem_msg = db_manager_fixture.add_member_to_db(
        member_name, member_phone
    )  # Use db_manager_fixture
    assert add_mem_s is True, f"Failed to add member for plan test: {add_mem_msg}"
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None
    member_id = member_id_row[0]

    add_tx_s, _ = db_manager_fixture.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=used_plan_id_val,
        transaction_date="2024-03-01",
        start_date="2024-03-01",
        amount=80,
        payment_method="Online",
    )  # Use db_manager_fixture
    assert add_tx_s

    result_used, message_used = db_manager_fixture.delete_plan(
        used_plan_id_val
    )  # Use db_manager_fixture
    assert result_used is False, "delete_plan should return False for a plan in use."
    assert (
        message_used == "Plan is in use and cannot be deleted."
    ), f"Unexpected message: {message_used}"

    cursor.execute("SELECT * FROM plans WHERE plan_id = ?", (used_plan_id_val,))
    assert (
        cursor.fetchone() is not None
    ), "Used plan was deleted, but it shouldn't have been."

    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE plan_id = ?", (used_plan_id_val,)
    )
    assert (
        cursor.fetchone()[0] == 1
    ), "Transaction linking to the used plan was unexpectedly deleted or altered."


if __name__ == "__main__":
    # To run these tests using `python reporter/tests/test_database_manager.py`
    # You would need to invoke pytest functionalities or run them manually.
    # It's generally better to use `python -m pytest` from the root /app directory.
    print(
        "To run these tests, navigate to the root '/app' directory and run: python -m pytest"
    )


# --- Tests for get_transactions_with_member_details ---


def setup_test_data_for_history_filters(
    db_manager_fixture_conn: sqlite3.Connection,
):  # Use new fixture, pass conn
    """Helper function to populate the database with specific data for testing history filters."""
    cursor = db_manager_fixture_conn.cursor()  # Use passed connection
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM members")
    cursor.execute(
        "DELETE FROM sqlite_sequence WHERE name IN ('members', 'transactions')"
    )
    db_manager_fixture_conn.commit()  # Use passed connection

    cursor.execute(
        "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
        ("Alice Wonderland", "111-222-3333", "2023-01-01"),
    )
    m_id_alice = cursor.lastrowid
    cursor.execute(
        "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
        ("Bob The Builder", "222-333-4444", "2023-02-15"),
    )
    m_id_bob = cursor.lastrowid
    cursor.execute(
        "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
        ("Alice Other", "111-444-5555", "2023-01-01"),
    )
    m_id_alice_other = cursor.lastrowid
    cursor.execute(
        "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
        ("Charlie NoTrans", "333-555-6666", "2023-03-01"),
    )

    cursor.execute(
        "INSERT INTO transactions (member_id, transaction_type, amount, start_date, transaction_date) VALUES (?, ?, ?, ?, ?)",
        (m_id_alice, "Group Class", 50.00, "2023-01-10", "2023-01-10"),
    )
    cursor.execute(
        "INSERT INTO transactions (member_id, transaction_type, amount, start_date, transaction_date, sessions) VALUES (?, ?, ?, ?, ?, ?)",
        (m_id_alice, "Personal Training", 70.00, "2023-03-05", "2023-03-05", 10),
    )
    cursor.execute(
        "INSERT INTO transactions (member_id, transaction_type, amount, start_date, transaction_date) VALUES (?, ?, ?, ?, ?)",
        (m_id_bob, "Group Class", 60.00, "2023-02-20", "2023-02-20"),
    )
    cursor.execute(
        "INSERT INTO transactions (member_id, transaction_type, amount, start_date, transaction_date) VALUES (?, ?, ?, ?, ?)",
        (m_id_alice_other, "Group Class", 55.00, "2023-01-15", "2023-01-15"),
    )
    db_manager_fixture_conn.commit()  # Use passed connection


def test_get_transactions_with_member_details_no_filters(
    db_manager_fixture,
):  # Use new fixture
    setup_test_data_for_history_filters(
        db_manager_fixture.conn
    )  # Pass conn from fixture
    results = (
        db_manager_fixture.get_transactions_with_member_details()
    )  # Use db_manager_fixture
    assert len(results) == 4, "Should return all 4 transactions"


def test_get_transactions_with_member_details_name_filter(
    db_manager_fixture,
):  # Use new fixture
    setup_test_data_for_history_filters(db_manager_fixture.conn)  # Pass conn
    results_alice = db_manager_fixture.get_transactions_with_member_details(
        name_filter="Alice"
    )  # Use db_manager_fixture
    assert (
        len(results_alice) == 3
    ), "Should return 3 transactions for 'Alice' (Alice Wonderland, Alice Other)"
    for record in results_alice:
        assert "Alice" in record[10], "Client name should contain 'Alice'"

    results_bob = db_manager_fixture.get_transactions_with_member_details(
        name_filter="Bob The Builder"
    )  # Use db_manager_fixture
    assert len(results_bob) == 1, "Should return 1 transaction for 'Bob The Builder'"
    assert results_bob[0][10] == "Bob The Builder"


def test_get_transactions_with_member_details_phone_filter(
    db_manager_fixture,
):  # Use new fixture
    setup_test_data_for_history_filters(db_manager_fixture.conn)  # Pass conn
    results = db_manager_fixture.get_transactions_with_member_details(
        phone_filter="111-222-3333"
    )  # Use db_manager_fixture
    assert (
        len(results) == 2
    ), "Should return 2 transactions for Alice Wonderland's phone"
    assert results[0][11] == "111-222-3333"

    results_partial = db_manager_fixture.get_transactions_with_member_details(
        phone_filter="111"
    )  # Use db_manager_fixture
    assert (
        len(results_partial) == 3
    ), "Should return 3 transactions for phones starting with '111'"


def test_get_transactions_with_member_details_join_date_filter(
    db_manager_fixture,
):  # Use new fixture
    setup_test_data_for_history_filters(db_manager_fixture.conn)  # Pass conn
    results = db_manager_fixture.get_transactions_with_member_details(
        join_date_filter="2023-01-01"
    )  # Use db_manager_fixture
    assert (
        len(results) == 3
    ), "Should return 3 transactions for members joined on 2023-01-01"
    for record in results:
        assert record[12] == "2023-01-01"


def test_get_transactions_with_member_details_combined_filters(
    db_manager_fixture,
):  # Use new fixture
    setup_test_data_for_history_filters(db_manager_fixture.conn)  # Pass conn
    results = db_manager_fixture.get_transactions_with_member_details(
        name_filter="Alice", phone_filter="111-444-5555"
    )  # Use db_manager_fixture
    assert (
        len(results) == 1
    ), "Should return 1 transaction for Alice Other by name and phone"
    assert results[0][10] == "Alice Other"
    assert results[0][11] == "111-444-5555"

    results = db_manager_fixture.get_transactions_with_member_details(
        name_filter="Bob", join_date_filter="2023-02-15"
    )  # Use db_manager_fixture
    assert (
        len(results) == 1
    ), "Should return 1 transaction for Bob by name and join date"
    assert results[0][10] == "Bob The Builder"


def test_get_transactions_with_member_details_invalid_date_format_filter(
    db_manager_fixture,
):  # Use new fixture
    setup_test_data_for_history_filters(db_manager_fixture.conn)  # Pass conn
    results = db_manager_fixture.get_transactions_with_member_details(
        join_date_filter="01/01/2023"
    )  # Use db_manager_fixture
    assert (
        len(results) == 4
    ), "Should ignore invalid date format and return all transactions"


def test_get_transactions_with_member_details_no_results(
    db_manager_fixture,
):  # Use new fixture
    setup_test_data_for_history_filters(db_manager_fixture.conn)  # Pass conn
    results = db_manager_fixture.get_transactions_with_member_details(
        name_filter="NonExistentName"
    )  # Use db_manager_fixture
    assert len(results) == 0, "Should return 0 transactions for a non-existent name"

    results = db_manager_fixture.get_transactions_with_member_details(
        join_date_filter="1900-01-01"
    )  # Use db_manager_fixture
    assert (
        len(results) == 0
    ), "Should return 0 transactions for a non-existent join date"

    results = db_manager_fixture.get_transactions_with_member_details(
        name_filter="Alice", phone_filter="999-999-9999"
    )  # Use db_manager_fixture
    assert (
        len(results) == 0
    ), "Should return 0 transactions for existing name but non-existent phone"


# --- Tests for Monthly Book Closing ---


def test_get_book_status_non_existent(db_manager_fixture):  # Use new fixture
    """Tests get_book_status for a month_key that doesn't exist, expecting 'open'."""
    month_key = "2099-12"
    status = db_manager_fixture.get_book_status(month_key)  # Use db_manager_fixture
    assert (
        status == "open"
    ), f"Expected 'open' for non-existent month_key '{month_key}', got '{status}'"


def test_set_and_get_book_status_closed(db_manager_fixture):  # Use new fixture
    """Tests setting a month's book status to 'closed' and then retrieving it."""
    month_key = "2023-11"
    set_success = db_manager_fixture.set_book_status(
        month_key, "closed"
    )  # Use db_manager_fixture
    assert (
        set_success is True
    ), f"set_book_status for '{month_key}' to 'closed' should return True."
    status = db_manager_fixture.get_book_status(month_key)  # Use db_manager_fixture
    assert (
        status == "closed"
    ), f"Expected status 'closed' for '{month_key}', got '{status}'"


def test_set_and_get_book_status_open(db_manager_fixture):  # Use new fixture
    """Tests setting a month's book status to 'open' and then retrieving it."""
    month_key = "2023-10"
    set_success = db_manager_fixture.set_book_status(
        month_key, "open"
    )  # Use db_manager_fixture
    assert (
        set_success is True
    ), f"set_book_status for '{month_key}' to 'open' should return True."
    status = db_manager_fixture.get_book_status(month_key)  # Use db_manager_fixture
    assert status == "open", f"Expected status 'open' for '{month_key}', got '{status}'"


def test_set_book_status_update_existing(db_manager_fixture):  # Use new fixture
    """Tests updating an existing month's book status from 'closed' to 'open'."""
    month_key = "2023-09"
    set_initial_success = db_manager_fixture.set_book_status(
        month_key, "closed"
    )  # Use db_manager_fixture
    assert set_initial_success is True, "Initial set_book_status to 'closed' failed."
    set_update_success = db_manager_fixture.set_book_status(
        month_key, "open"
    )  # Use db_manager_fixture
    assert (
        set_update_success is True
    ), "Updating set_book_status to 'open' should return True."
    status = db_manager_fixture.get_book_status(month_key)  # Use db_manager_fixture
    assert (
        status == "open"
    ), f"Expected status 'open' for '{month_key}' after update, got '{status}'"

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute(
        "SELECT status FROM monthly_book_status WHERE month_key = ?", (month_key,)
    )
    db_record = cursor.fetchone()
    assert db_record is not None, f"No record found in DB for month_key '{month_key}'"
    assert (
        db_record[0] == "open"
    ), f"DB status for '{month_key}' should be 'open', got '{db_record[0]}'"
    cursor.execute(
        "SELECT COUNT(*) FROM monthly_book_status WHERE month_key = ?", (month_key,)
    )
    count = cursor.fetchone()[0]
    assert (
        count == 1
    ), f"Expected exactly one record for month_key '{month_key}', found {count}"


def _setup_member_and_plan_for_transaction_tests(
    db_manager_fixture_param, member_phone_suffix="TRN"
):  # Renamed param to avoid conflict
    """Helper to create a member and get a plan_id for transaction tests."""
    cursor = db_manager_fixture_param.conn.cursor()
    member_name = f"Test Member {member_phone_suffix}"
    member_phone = f"MEMBER{member_phone_suffix}"
    add_mem_s, _ = db_manager_fixture_param.add_member_to_db(member_name, member_phone)
    assert (
        add_mem_s
    ), f"Failed to add member in _setup_member_and_plan_for_transaction_tests for suffix {member_phone_suffix}"
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Failed to create member for transaction test."
    member_id = member_id_row[0]

    cursor.execute("SELECT plan_id FROM plans LIMIT 1")
    plan_id_row = cursor.fetchone()
    assert plan_id_row is not None, "No plans found in DB; needed for transaction test."
    plan_id = plan_id_row[0]
    return member_id, plan_id


def test_add_transaction_when_books_closed(db_manager_fixture):  # Use new fixture
    """Tests that add_transaction is blocked when books for the payment_date month are closed."""
    member_id, plan_id = _setup_member_and_plan_for_transaction_tests(
        db_manager_fixture, "BC_ADD"
    )  # Pass fixture

    month_key_closed = "2024-07"
    transaction_date_in_closed_month = "2024-07-15"
    start_date = "2024-07-10"

    assert (
        db_manager_fixture.set_book_status(month_key_closed, "closed") is True
    ), "Failed to close books for the test."  # Use db_manager_fixture

    success, message = db_manager_fixture.add_transaction(  # Use db_manager_fixture
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=transaction_date_in_closed_month,
        start_date=start_date,
        amount=100.00,
        payment_method="Cash",
    )
    assert success is False, "add_transaction should have failed due to closed books."
    expected_message = (
        f"Cannot add transaction. Books for {month_key_closed} are closed."
    )
    assert message.startswith(
        expected_message
    ), f"Expected message '{expected_message}', got '{message}'"

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE member_id = ? AND transaction_date = ?",
        (member_id, transaction_date_in_closed_month),
    )
    count = cursor.fetchone()[0]
    assert count == 0, "Transaction was added despite books being closed."


def test_delete_transaction_when_books_closed(db_manager_fixture):  # Use new fixture
    """Tests that delete_transaction is blocked when books for the transaction's month are closed."""
    member_id, plan_id = _setup_member_and_plan_for_transaction_tests(
        db_manager_fixture, "BC_DEL"
    )  # Pass fixture

    month_key_closed = "2024-08"
    transaction_date_in_closed_month = "2024-08-10"

    add_success, _ = db_manager_fixture.add_transaction(  # Use db_manager_fixture
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=transaction_date_in_closed_month,
        start_date=transaction_date_in_closed_month,
        amount=120.00,
        payment_method="Card",
    )
    assert add_success is True, "Failed to add initial transaction for the test."

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute(
        "SELECT transaction_id FROM transactions WHERE member_id = ? AND transaction_date = ?",
        (member_id, transaction_date_in_closed_month),
    )
    transaction_id_row = cursor.fetchone()
    assert (
        transaction_id_row is not None
    ), "Failed to retrieve the added transaction_id."
    transaction_id_to_delete = transaction_id_row[0]

    assert (
        db_manager_fixture.set_book_status(month_key_closed, "closed") is True
    ), "Failed to close books for the test."  # Use db_manager_fixture

    delete_success, message = db_manager_fixture.delete_transaction(
        transaction_id_to_delete
    )  # Use db_manager_fixture
    assert (
        delete_success is False
    ), "delete_transaction should have failed due to closed books."
    expected_message = (
        f"Cannot delete transaction. Books for {month_key_closed} are closed."
    )
    assert message.startswith(
        expected_message
    ), f"Expected message '{expected_message}', got '{message}'"

    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE transaction_id = ?",
        (transaction_id_to_delete,),
    )
    count = cursor.fetchone()[0]
    assert count == 1, "Transaction was deleted despite books being closed."


def test_add_transaction_when_books_open(db_manager_fixture):  # Use new fixture
    """Tests that add_transaction succeeds when books for the payment_date month are open."""
    member_id, plan_id = _setup_member_and_plan_for_transaction_tests(
        db_manager_fixture, "BO_ADD"
    )  # Pass fixture

    month_key_open = "2024-09"
    transaction_date_in_open_month = "2024-09-15"
    assert (
        db_manager_fixture.set_book_status(month_key_open, "open") is True
    )  # Use db_manager_fixture

    success, message = db_manager_fixture.add_transaction(  # Use db_manager_fixture
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=transaction_date_in_open_month,
        start_date=transaction_date_in_open_month,
        amount=100.00,
        payment_method="Cash",
    )
    assert (
        success is True
    ), f"add_transaction should succeed when books are open. Message: {message}"

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE member_id = ? AND transaction_date = ?",
        (member_id, transaction_date_in_open_month),
    )
    count = cursor.fetchone()[0]
    assert count == 1, "Transaction was not added even though books were open."


def test_delete_transaction_when_books_open(db_manager_fixture):  # Use new fixture
    """Tests that delete_transaction succeeds when books for the transaction's month are open."""
    member_id, plan_id = _setup_member_and_plan_for_transaction_tests(
        db_manager_fixture, "BO_DEL"
    )  # Pass fixture

    month_key_open = "2024-10"
    transaction_date_in_open_month = "2024-10-10"

    add_success, _ = db_manager_fixture.add_transaction(  # Use db_manager_fixture
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id,
        transaction_date=transaction_date_in_open_month,
        start_date=transaction_date_in_open_month,
        amount=130.00,
        payment_method="Online",
    )
    assert add_success is True, "Failed to add initial transaction for the test."

    cursor = db_manager_fixture.conn.cursor()  # Use db_manager_fixture.conn
    cursor.execute(
        "SELECT transaction_id FROM transactions WHERE member_id = ? AND transaction_date = ?",
        (member_id, transaction_date_in_open_month),
    )
    transaction_id_row = cursor.fetchone()
    assert (
        transaction_id_row is not None
    ), "Failed to retrieve the added transaction_id."
    transaction_id_to_delete = transaction_id_row[0]

    assert (
        db_manager_fixture.set_book_status(month_key_open, "open") is True
    )  # Use db_manager_fixture

    delete_success, message = db_manager_fixture.delete_transaction(
        transaction_id_to_delete
    )  # Use db_manager_fixture
    assert (
        delete_success is True
    ), f"delete_transaction should succeed when books are open. Message: {message}"

    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE transaction_id = ?",
        (transaction_id_to_delete,),
    )
    count = cursor.fetchone()[0]
    assert count == 0, "Transaction was not deleted even though books were open."


# --- Tests for Plan Name Formatting in get_or_create_plan_id ---

def test_get_or_create_plan_id_basic_creation_formatted_name(db_manager_fixture):
    """Scenario 1: Basic new plan creation with formatted name."""
    db_mngr = db_manager_fixture
    base_name = "Basic Plan"
    duration = 30
    price = 100
    plan_type = "GC"
    expected_formatted_name = f"{base_name} - {duration} Days"

    plan_id = db_mngr.get_or_create_plan_id(expected_formatted_name, duration, price, plan_type)
    assert plan_id is not None

    # Verify in DB
    cursor = db_mngr.conn.cursor()
    cursor.execute("SELECT plan_name, duration_days FROM plans WHERE plan_id = ?", (plan_id,))
    db_plan = cursor.fetchone()
    assert db_plan is not None
    assert db_plan[0] == expected_formatted_name
    assert db_plan[1] == duration

def test_get_or_create_plan_id_name_with_hyphens_numbers(db_manager_fixture):
    """Scenario 2: Plan name with existing hyphens or numbers."""
    db_mngr = db_manager_fixture
    base_name = "Special Plan - Tier 1" # This is treated as the full base name for formatting
    duration = 60
    price = 200
    plan_type = "GC"
    # The 'name' passed to get_or_create_plan_id IS the final name.
    # The formatting `f"{base} - {duration} Days"` happens *before* calling this method,
    # as per migrate_data.py changes.
    # So, this test should reflect that the formatted name is passed directly.
    formatted_name_to_pass = f"{base_name} - {duration} Days" # e.g., "Special Plan - Tier 1 - 60 Days"

    plan_id = db_mngr.get_or_create_plan_id(formatted_name_to_pass, duration, price, plan_type)
    assert plan_id is not None

    # Verify in DB
    cursor = db_mngr.conn.cursor()
    cursor.execute("SELECT plan_name, duration_days FROM plans WHERE plan_id = ?", (plan_id,))
    db_plan = cursor.fetchone()
    assert db_plan is not None
    assert db_plan[0] == formatted_name_to_pass
    assert db_plan[1] == duration

def test_get_or_create_plan_id_recall_same_formatted_name_and_duration(db_manager_fixture):
    """Scenario 4: Re-calling with the same formatted name and duration."""
    db_mngr = db_manager_fixture
    base_name = "Recall Plan"
    duration = 90
    price = 150
    plan_type = "PT"
    formatted_name = f"{base_name} - {duration} Days"

    plan_id1 = db_mngr.get_or_create_plan_id(formatted_name, duration, price, plan_type)
    assert plan_id1 is not None

    plan_id2 = db_mngr.get_or_create_plan_id(formatted_name, duration, price, plan_type)
    assert plan_id2 is not None
    assert plan_id1 == plan_id2, "Should retrieve the same plan ID on recall."

    # Verify only one such plan exists
    cursor = db_mngr.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM plans WHERE plan_name = ? AND duration_days = ?", (formatted_name, duration))
    count = cursor.fetchone()[0]
    assert count == 1

def test_get_or_create_plan_id_same_base_different_durations(db_manager_fixture):
    """Scenario 5: Creating plans with the same base name but different durations."""
    db_mngr = db_manager_fixture
    base_name = "MultiDur Plan"
    price = 100
    plan_type = "GC"

    duration1 = 30
    formatted_name1 = f"{base_name} - {duration1} Days"
    plan_id1 = db_mngr.get_or_create_plan_id(formatted_name1, duration1, price, plan_type)
    assert plan_id1 is not None

    duration2 = 60
    formatted_name2 = f"{base_name} - {duration2} Days"
    plan_id2 = db_mngr.get_or_create_plan_id(formatted_name2, duration2, price, plan_type)
    assert plan_id2 is not None

    assert plan_id1 != plan_id2, "Plans with different durations (and thus different formatted names) should have different IDs."

    # Verify both exist with correct details
    cursor = db_mngr.conn.cursor()
    cursor.execute("SELECT plan_name, duration_days FROM plans WHERE plan_id = ?", (plan_id1,))
    db_plan1 = cursor.fetchone()
    assert db_plan1 is not None
    assert db_plan1[0] == formatted_name1
    assert db_plan1[1] == duration1

    cursor.execute("SELECT plan_name, duration_days FROM plans WHERE plan_id = ?", (plan_id2,))
    db_plan2 = cursor.fetchone()
    assert db_plan2 is not None
    assert db_plan2[0] == formatted_name2
    assert db_plan2[1] == duration2

import pytest
import sqlite3
import os
from datetime import datetime, date, timedelta

from reporter.database_manager import DatabaseManager
from reporter.database import create_database

# Define the test database path
TEST_DB_PATH = "test_app.db"

@pytest.fixture(scope="function")
def db_manager():
    """
    Fixture to set up and tear down a test database for each test function.
    - Creates a new database file 'test_app.db'.
    - Initializes the schema using create_database from reporter.database.
    - Yields a DatabaseManager instance connected to this test database.
    - Cleans up by closing the connection and deleting 'test_app.db'.
    """
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    create_database(TEST_DB_PATH) # This creates tables

    conn = sqlite3.connect(TEST_DB_PATH)
    manager = DatabaseManager(conn)

    yield manager

    if conn:
        conn.close()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

# --- Helper functions for dates ---
def today_str():
    return date.today().strftime("%Y-%m-%d")

def future_date_str(days: int):
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")

def past_date_str(days: int):
    return (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")

# --- Tests for create_membership_record ---

def test_create_membership_record_success(db_manager: DatabaseManager):
    # 1. Create dummy member and plan
    cursor = db_manager.conn.cursor()
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Test Member", "1234567890", "test@example.com", today_str(), 1))
    member_id = cursor.lastrowid
    cursor.execute("INSERT INTO plans (name, price, type, is_active) VALUES (?, ?, ?, ?)",
                   ("Test Plan", 100, "Standard", 1))
    plan_id = cursor.lastrowid
    db_manager.conn.commit()

    # 2. Prepare valid data
    membership_data = {
        "member_id": member_id,
        "plan_id": plan_id,
        "plan_duration_days": 30,
        "amount_paid": 100.0,
        "start_date": today_str()
    }

    # 3. Call create_membership_record
    success, message = db_manager.create_membership_record(membership_data)

    # 4. Verify success message
    assert success is True
    assert message == "Membership record created successfully."

    # 5. Verify the record in the database
    cursor.execute("SELECT member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active FROM memberships WHERE member_id = ?", (member_id,))
    record = cursor.fetchone()
    assert record is not None
    assert record[0] == member_id
    assert record[1] == plan_id
    assert record[2] == today_str()
    expected_end_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    assert record[3] == expected_end_date
    assert record[4] == 100.0
    assert record[5] == today_str() # purchase_date
    assert record[6] == "New" # membership_type
    assert record[7] == 1 # is_active (True)

def test_create_membership_record_missing_member(db_manager: DatabaseManager):
    # 1. Create a dummy plan
    cursor = db_manager.conn.cursor()
    cursor.execute("INSERT INTO plans (name, price, type, is_active) VALUES (?, ?, ?, ?)",
                   ("Test Plan", 100, "Standard", 1))
    plan_id = cursor.lastrowid
    db_manager.conn.commit()

    # 2. Prepare data with a non-existent member_id
    non_existent_member_id = 99999
    membership_data = {
        "member_id": non_existent_member_id,
        "plan_id": plan_id,
        "plan_duration_days": 30,
        "amount_paid": 100.0,
        "start_date": today_str()
    }

    # 3. Call create_membership_record
    success, message = db_manager.create_membership_record(membership_data)

    # 4. Verify failure and error message
    assert success is False
    assert "FOREIGN KEY constraint failed" in message or "Database error" in message

    # 5. Verify no record was created
    cursor.execute("SELECT COUNT(*) FROM memberships WHERE member_id = ?", (non_existent_member_id,))
    count = cursor.fetchone()[0]
    assert count == 0

def test_create_membership_record_missing_plan(db_manager: DatabaseManager):
    # 1. Create a dummy member
    cursor = db_manager.conn.cursor()
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Test Member", "1234567890", "test@example.com", today_str(), 1))
    member_id = cursor.lastrowid
    db_manager.conn.commit()

    # 2. Prepare data with a non-existent plan_id
    non_existent_plan_id = 99998
    membership_data = {
        "member_id": member_id,
        "plan_id": non_existent_plan_id,
        "plan_duration_days": 30,
        "amount_paid": 100.0,
        "start_date": today_str()
    }

    # 3. Call create_membership_record
    success, message = db_manager.create_membership_record(membership_data)

    # 4. Verify failure and error message
    assert success is False
    assert "FOREIGN KEY constraint failed" in message or "Database error" in message

    # 5. Verify no record was created
    cursor.execute("SELECT COUNT(*) FROM memberships WHERE plan_id = ?", (non_existent_plan_id,))
    count = cursor.fetchone()[0]
    assert count == 0

def test_create_membership_record_invalid_data(db_manager: DatabaseManager):
    # Test with various missing keys
    required_keys = ["member_id", "plan_id", "plan_duration_days", "amount_paid", "start_date"]

    # Create valid dummy member and plan to ensure errors are due to missing keys, not FK constraints
    cursor = db_manager.conn.cursor()
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Valid Member", "1112223333", "valid@example.com", today_str(), 1))
    member_id = cursor.lastrowid
    cursor.execute("INSERT INTO plans (name, price, type, is_active) VALUES (?, ?, ?, ?)",
                   ("Valid Plan", 50, "Basic", 1))
    plan_id = cursor.lastrowid
    db_manager.conn.commit()

    base_data = {
        "member_id": member_id,
        "plan_id": plan_id,
        "plan_duration_days": 30,
        "amount_paid": 50.0,
        "start_date": today_str()
    }

    for key_to_remove in required_keys:
        data_copy = base_data.copy()
        del data_copy[key_to_remove]

        success, message = db_manager.create_membership_record(data_copy)
        assert success is False
        assert f"Missing required data: {key_to_remove}" in message or "Missing required data" in message # More general check

    # Test with invalid start_date format
    invalid_date_data = base_data.copy()
    invalid_date_data["start_date"] = "invalid-date-format"
    success, message = db_manager.create_membership_record(invalid_date_data)
    assert success is False
    assert "Date format error for start_date" in message

# --- Tests for generate_financial_report_data ---

def test_generate_financial_report_empty(db_manager: DatabaseManager):
    start_period = past_date_str(30)
    end_period = today_str()

    report_data = db_manager.generate_financial_report_data(start_period, end_period)

    assert report_data["summary"]["total_revenue"] == 0.0
    assert report_data["details"] == []

def test_generate_financial_report_with_data(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    # Member 1
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Member One", "100000001", "one@example.com", past_date_str(60), 1))
    member1_id = cursor.lastrowid
    # Member 2
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Member Two", "100000002", "two@example.com", past_date_str(40), 1))
    member2_id = cursor.lastrowid
    # Plan 1
    cursor.execute("INSERT INTO plans (name, price, type, is_active) VALUES (?, ?, ?, ?)",
                   ("Monthly Gold", 100, "Gold", 1))
    plan1_id = cursor.lastrowid
    # Plan 2
    cursor.execute("INSERT INTO plans (name, price, type, is_active) VALUES (?, ?, ?, ?)",
                   ("Annual Silver", 500, "Silver", 1))
    plan2_id = cursor.lastrowid
    db_manager.conn.commit()

    # Membership 1: purchased 15 days ago, within report period
    m1_data = {"member_id": member1_id, "plan_id": plan1_id, "plan_duration_days": 30, "amount_paid": 100.0, "start_date": past_date_str(15)}
    # Manually set purchase_date for precise testing, as create_membership_record uses today_str()
    db_manager.conn.execute(
        "INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (member1_id, plan1_id, past_date_str(15), future_date_str(15), 100.0, past_date_str(15), "New", 1)
    )

    # Membership 2: purchased 5 days ago, within report period
    m2_data = {"member_id": member2_id, "plan_id": plan1_id, "plan_duration_days": 30, "amount_paid": 120.0, "start_date": past_date_str(5)}
    db_manager.conn.execute(
        "INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (member2_id, plan1_id, past_date_str(5), future_date_str(25), 120.0, past_date_str(5), "New", 1)
    )

    # Membership 3: purchased 45 days ago, outside report period (before start)
    m3_data = {"member_id": member1_id, "plan_id": plan2_id, "plan_duration_days": 365, "amount_paid": 500.0, "start_date": past_date_str(45)}
    db_manager.conn.execute(
        "INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (member1_id, plan2_id, past_date_str(45), future_date_str(320), 500.0, past_date_str(45), "New", 1)
    )

    # Membership 4: purchase_date is today, but start_date is in future (should be included based on purchase_date)
    m4_data = {"member_id": member2_id, "plan_id": plan2_id, "plan_duration_days": 365, "amount_paid": 550.0, "start_date": future_date_str(10)}
    db_manager.conn.execute(
        "INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (member2_id, plan2_id, future_date_str(10), future_date_str(375), 550.0, today_str(), "New", 1)
    )
    db_manager.conn.commit()

    report_start_date = past_date_str(30)
    report_end_date = today_str()

    report_data = db_manager.generate_financial_report_data(report_start_date, report_end_date)

    # Total revenue should be 100.0 (m1) + 120.0 (m2) + 550.0 (m4) = 770.0
    assert report_data["summary"]["total_revenue"] == 770.0
    assert len(report_data["details"]) == 3

    details = sorted(report_data["details"], key=lambda x: x["purchase_date"])

    # Check Membership 1 details
    assert details[0]["member_name"] == "Member One"
    assert details[0]["plan_name"] == "Monthly Gold"
    assert details[0]["amount_paid"] == 100.0
    assert details[0]["purchase_date"] == past_date_str(15)

    # Check Membership 2 details
    assert details[1]["member_name"] == "Member Two"
    assert details[1]["plan_name"] == "Monthly Gold"
    assert details[1]["amount_paid"] == 120.0
    assert details[1]["purchase_date"] == past_date_str(5)

    # Check Membership 4 details
    assert details[2]["member_name"] == "Member Two"
    assert details[2]["plan_name"] == "Annual Silver" # Plan 2
    assert details[2]["amount_paid"] == 550.0
    assert details[2]["purchase_date"] == today_str()

# --- Tests for generate_renewal_report_data ---

def test_generate_renewal_report_empty(db_manager: DatabaseManager):
    # Add a member and a plan
    cursor = db_manager.conn.cursor()
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Test Member", "1234567890", "renewal@example.com", past_date_str(100), 1))
    member_id = cursor.lastrowid
    cursor.execute("INSERT INTO plans (name, price, type, is_active) VALUES (?, ?, ?, ?)",
                   ("Test Plan", 10, "Standard", 1))
    plan_id = cursor.lastrowid
    db_manager.conn.commit()

    # Add a membership that ends far in the future
    start_date = today_str()
    end_date = future_date_str(60) # Ends in 60 days, so not in renewal window
    db_manager.conn.execute(
        "INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (member_id, plan_id, start_date, end_date, 10.0, today_str(), "New", 1)
    )
    # Add a membership that ended in the past
    start_date_past = past_date_str(60)
    end_date_past = past_date_str(30) # Ended 30 days ago
    db_manager.conn.execute(
        "INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (member_id, plan_id, start_date_past, end_date_past, 10.0, past_date_str(60), "Renewal", 1) # is_active might be False in reality
    )
    db_manager.conn.commit()

    report_data = db_manager.generate_renewal_report_data()
    assert report_data == []

def test_generate_renewal_report_with_upcoming_renewals(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    # Members
    m1_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Upcoming Member', '200000001', 'up1@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m2_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Soon Member', '200000002', 'up2@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m3_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Today Member', '200000003', 'up3@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m4_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Edge Case Member', '200000004', 'up4@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m5_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Future Member', '200000005', 'up5@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m6_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Past Member', '200000006', 'up6@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m7_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Inactive Member', '200000007', 'up7@example.com', ?, 1)", (past_date_str(50),)).lastrowid

    # Plans
    p1_id = cursor.execute("INSERT INTO plans (name, price, type, is_active) VALUES ('Renewal Plan A', 50, 'A', 1)").lastrowid
    p2_id = cursor.execute("INSERT INTO plans (name, price, type, is_active) VALUES ('Renewal Plan B', 60, 'B', 1)").lastrowid
    db_manager.conn.commit()

    # Memberships
    # Ends in 15 days (upcoming)
    cursor.execute("INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m1_id, p1_id, past_date_str(15), future_date_str(15), 50, past_date_str(15), "New", 1))
    # Ends in 29 days (upcoming)
    cursor.execute("INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m2_id, p1_id, past_date_str(1), future_date_str(29), 50, past_date_str(1), "New", 1))
    # Ends today (upcoming)
    cursor.execute("INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m3_id, p2_id, past_date_str(30), today_str(), 60, past_date_str(30), "Renewal", 1))
    # Ends in 30 days (upcoming - edge of window)
    cursor.execute("INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m4_id, p2_id, today_str(), future_date_str(30), 60, today_str(), "New", 1))

    # Ends in 31 days (outside window)
    cursor.execute("INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m5_id, p1_id, today_str(), future_date_str(31), 50, today_str(), "New", 1))
    # Ended 5 days ago (outside window)
    cursor.execute("INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m6_id, p1_id, past_date_str(35), past_date_str(5), 50, past_date_str(35), "Renewal", 1))
    # Ends in 10 days but inactive (outside criteria)
    cursor.execute("INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m7_id, p2_id, past_date_str(20), future_date_str(10), 60, past_date_str(20), "New", 0)) # is_active = 0
    db_manager.conn.commit()

    report_data = db_manager.generate_renewal_report_data()

    assert len(report_data) == 4

    report_data_sorted = sorted(report_data, key=lambda x: x["end_date"])

    # Member 3 (ends today)
    assert report_data_sorted[0]["member_name"] == "Today Member"
    assert report_data_sorted[0]["plan_name"] == "Renewal Plan B"
    assert report_data_sorted[0]["end_date"] == today_str()
    assert report_data_sorted[0]["member_phone"] == "200000003"

    # Member 1 (ends in 15 days)
    assert report_data_sorted[1]["member_name"] == "Upcoming Member"
    assert report_data_sorted[1]["plan_name"] == "Renewal Plan A"
    assert report_data_sorted[1]["end_date"] == future_date_str(15)

    # Member 2 (ends in 29 days)
    assert report_data_sorted[2]["member_name"] == "Soon Member"
    assert report_data_sorted[2]["plan_name"] == "Renewal Plan A"
    assert report_data_sorted[2]["end_date"] == future_date_str(29)

    # Member 4 (ends in 30 days)
    assert report_data_sorted[3]["member_name"] == "Edge Case Member"
    assert report_data_sorted[3]["plan_name"] == "Renewal Plan B"
    assert report_data_sorted[3]["end_date"] == future_date_str(30)

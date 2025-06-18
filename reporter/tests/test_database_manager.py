import pytest
import sqlite3
import os
from datetime import datetime, date, timedelta

from reporter.database_manager import DatabaseManager
from reporter.database import create_database

# Define the test database path
TEST_DB_PATH = "test_app_manager.db"

@pytest.fixture(scope="function")
def db_manager():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    create_database(TEST_DB_PATH)
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    manager = DatabaseManager(conn)
    yield manager
    if conn:
        conn.close()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def today_str():
    return date.today().strftime("%Y-%m-%d")

def future_date_str(days: int):
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")

def past_date_str(days: int):
    return (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")

def test_create_group_class_membership_success(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Test Member", "1234567890", "test@example.com", today_str(), 1))
    member_id = cursor.lastrowid
    cursor.execute("INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Test Plan", 30, 100.0, "Test Plan - 30 days", 1))
    plan_id = cursor.lastrowid
    db_manager.conn.commit()
    start_date_val = today_str()
    amount_paid_val = 100.0
    membership_id = db_manager.create_group_class_membership(
        member_id=member_id,
        plan_id=plan_id,
        start_date_str=start_date_val,
        amount_paid=amount_paid_val
    )
    assert membership_id is not None
    assert isinstance(membership_id, int)
    # Updated to select status and auto_renewal_enabled instead of is_active
    cursor.execute("SELECT member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, status, auto_renewal_enabled FROM group_class_memberships WHERE id = ?", (membership_id,))
    record = cursor.fetchone()
    assert record is not None
    assert record[0] == member_id
    assert record[1] == plan_id
    assert record[2] == start_date_val
    expected_end_date = (datetime.strptime(start_date_val, "%Y-%m-%d").date() + timedelta(days=30-1)).strftime("%Y-%m-%d")
    assert record[3] == expected_end_date
    assert record[4] == amount_paid_val
    assert date.fromisoformat(record[5].split(" ")[0]) == date.today() # purchase_date is a datetime string
    assert record[6] == "New" # membership_type
    assert record[7] == "Active" # status (default value)
    assert record[8] == 0 # auto_renewal_enabled (default value)

def test_create_group_class_membership_missing_member(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    cursor.execute("INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Test Plan", 30, 100.0, "Test Plan - 30 days", 1))
    plan_id = cursor.lastrowid
    db_manager.conn.commit()
    non_existent_member_id = 99999
    with pytest.raises(sqlite3.IntegrityError) as excinfo:
        db_manager.create_group_class_membership(
            member_id=non_existent_member_id,
            plan_id=plan_id,
            start_date_str=today_str(),
            amount_paid=100.0
        )
    assert "FOREIGN KEY constraint failed" in str(excinfo.value)
    new_cursor = db_manager.conn.cursor()
    new_cursor.execute("SELECT COUNT(*) FROM group_class_memberships WHERE member_id = ?", (non_existent_member_id,))
    count = new_cursor.fetchone()[0]
    assert count == 0

def test_create_group_class_membership_missing_plan(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Test Member", "1234567890", "test@example.com", today_str(), 1))
    member_id = cursor.lastrowid
    db_manager.conn.commit()
    non_existent_plan_id = 99998
    with pytest.raises(ValueError) as excinfo:
        db_manager.create_group_class_membership(
            member_id=member_id,
            plan_id=non_existent_plan_id,
            start_date_str=today_str(),
            amount_paid=100.0
        )
    assert f"Group Plan with ID {non_existent_plan_id} not found." in str(excinfo.value)
    cursor.execute("SELECT COUNT(*) FROM group_class_memberships WHERE plan_id = ?", (non_existent_plan_id,))
    count = cursor.fetchone()[0]
    assert count == 0

def test_create_group_class_membership_invalid_data(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Valid Member", "1112223333", "valid@example.com", today_str(), 1))
    member_id = cursor.lastrowid
    cursor.execute("INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Valid Plan", 30, 50.0, "Valid Plan - 30 days", 1))
    plan_id = cursor.lastrowid
    db_manager.conn.commit()
    with pytest.raises(ValueError) as excinfo:
        db_manager.create_group_class_membership(
            member_id=member_id,
            plan_id=plan_id,
            start_date_str="invalid-date-format",
            amount_paid=50.0
        )
    assert "Invalid start_date format: invalid-date-format. Expected YYYY-MM-DD." in str(excinfo.value)
    with pytest.raises(TypeError):
        db_manager.create_group_class_membership(member_id=member_id, plan_id=plan_id)

def test_generate_financial_report_empty(db_manager: DatabaseManager):
    start_period = past_date_str(30)
    end_period = today_str()
    report_data = db_manager.generate_financial_report_data(start_period, end_period)
    assert report_data["summary"]["total_revenue"] == 0.0
    assert report_data["details"] == []

def test_generate_financial_report_with_data(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    m1_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Member One', '100000001', 'one@example.com', ?, 1)", (past_date_str(60),)).lastrowid
    m2_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Member Two', '100000002', 'two@example.com', ?, 1)", (past_date_str(40),)).lastrowid
    gp1_id = cursor.execute("INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active) VALUES ('Monthly Gold', 30, 100.0, 'Monthly Gold - 30 days', 1)").lastrowid
    gp2_id = cursor.execute("INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active) VALUES ('Annual Silver', 365, 500.0, 'Annual Silver - 365 days', 1)").lastrowid
    db_manager.conn.commit()

    # Group Class Memberships
    db_manager.conn.execute(
        "INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (m1_id, gp1_id, past_date_str(15), (datetime.strptime(past_date_str(15),"%Y-%m-%d")+timedelta(days=30-1)).strftime("%Y-%m-%d"), 100.0, past_date_str(15), "New", 1)
    )
    db_manager.conn.execute(
        "INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (m2_id, gp1_id, past_date_str(5), (datetime.strptime(past_date_str(5),"%Y-%m-%d")+timedelta(days=30-1)).strftime("%Y-%m-%d"), 120.0, past_date_str(5), "New", 1)
    )
    # PT Memberships
    db_manager.conn.execute(
        "INSERT INTO pt_memberships (member_id, purchase_date, amount_paid, sessions_total, sessions_remaining, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (m1_id, past_date_str(10), 75.0, 5, 5, "5 PT sessions for Member One")
    )
    db_manager.conn.execute(
        "INSERT INTO pt_memberships (member_id, purchase_date, amount_paid, sessions_total, sessions_remaining, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (m2_id, today_str(), 250.0, 20, 20, "20 PT sessions for Member Two")
    )
    # Outside period
    db_manager.conn.execute(
        "INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (m1_id, gp2_id, past_date_str(45), (datetime.strptime(past_date_str(45),"%Y-%m-%d")+timedelta(days=365-1)).strftime("%Y-%m-%d"), 500.0, past_date_str(45), "New", 1)
    )
    db_manager.conn.commit()

    report_start_date = past_date_str(30)
    report_end_date = today_str()
    report_data = db_manager.generate_financial_report_data(report_start_date, report_end_date)

    assert report_data["summary"]["total_revenue"] == 100.0 + 120.0 + 75.0 + 250.0 # 545.0
    assert len(report_data["details"]) == 4

    details = sorted(report_data["details"], key=lambda x: x["purchase_date"])

    assert details[0]["member_name"] == "Member One"
    assert details[0]["item_name"] == "Monthly Gold" # From group_plans.name
    assert details[0]["amount_paid"] == 100.0
    assert details[0]["purchase_date"] == past_date_str(15)
    assert details[0]["type"] == "Group Class"

    assert details[1]["member_name"] == "Member One"
    assert details[1]["item_name"] == "5 PT Sessions" # From pt_memberships sessions_total
    assert details[1]["amount_paid"] == 75.0
    assert details[1]["purchase_date"] == past_date_str(10)
    assert details[1]["type"] == "Personal Training"

    assert details[2]["member_name"] == "Member Two"
    assert details[2]["item_name"] == "Monthly Gold"
    assert details[2]["amount_paid"] == 120.0
    assert details[2]["purchase_date"] == past_date_str(5)
    assert details[2]["type"] == "Group Class"

    assert details[3]["member_name"] == "Member Two"
    assert details[3]["item_name"] == "20 PT Sessions" # From pt_memberships sessions_total
    assert details[3]["amount_paid"] == 250.0
    assert details[3]["purchase_date"] == today_str()
    assert details[3]["type"] == "Personal Training"


def test_generate_renewal_report_empty(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Test Member", "1234567890", "renewal@example.com", past_date_str(100), 1))
    member_id = cursor.lastrowid
    cursor.execute("INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("Test Plan", 30, 10.0, "Test Plan - 30 days", 1))
    plan_id = cursor.lastrowid
    db_manager.conn.commit()
    start_date_val = today_str()
    db_manager.create_group_class_membership(member_id, plan_id, start_date_val, 10.0)
    cursor.execute("UPDATE group_class_memberships SET end_date = ? WHERE member_id = ? AND plan_id = ?", (future_date_str(60), member_id, plan_id))
    start_date_past = past_date_str(60)
    end_date_past = past_date_str(30)
    db_manager.conn.execute(
        "INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (member_id, plan_id, start_date_past, end_date_past, 10.0, past_date_str(60), "Renewal", 0)
    )
    db_manager.conn.commit()
    report_data = db_manager.generate_renewal_report_data()
    assert report_data == []

def test_generate_renewal_report_with_upcoming_renewals(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    m1_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Upcoming Member', '200000001', 'up1@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m2_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Soon Member', '200000002', 'up2@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m3_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Today Member', '200000003', 'up3@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m4_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Edge Case Member', '200000004', 'up4@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m5_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Future Member', '200000005', 'up5@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m6_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Past Member', '200000006', 'up6@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    m7_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Inactive Member', '200000007', 'up7@example.com', ?, 1)", (past_date_str(50),)).lastrowid
    p1_id = cursor.execute("INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active) VALUES ('Renewal Plan A', 30, 50.0, 'Renewal Plan A - 30 days', 1)").lastrowid
    p2_id = cursor.execute("INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active) VALUES ('Renewal Plan B', 60, 60.0, 'Renewal Plan B - 60 days', 1)").lastrowid
    db_manager.conn.commit()
    start_m1 = (datetime.strptime(future_date_str(15), "%Y-%m-%d").date() - timedelta(days=30-1)).strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m1_id, p1_id, start_m1, future_date_str(15), 50, start_m1, "New", 1))
    start_m2 = (datetime.strptime(future_date_str(29), "%Y-%m-%d").date() - timedelta(days=30-1)).strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m2_id, p1_id, start_m2, future_date_str(29), 50, start_m2, "New", 1))
    start_m3 = (datetime.strptime(today_str(), "%Y-%m-%d").date() - timedelta(days=60-1)).strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m3_id, p2_id, start_m3, today_str(), 60, start_m3, "Renewal", 1))
    start_m4 = (datetime.strptime(future_date_str(30), "%Y-%m-%d").date() - timedelta(days=60-1)).strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m4_id, p2_id, start_m4, future_date_str(30), 60, start_m4, "New", 1))
    start_m5 = (datetime.strptime(future_date_str(31), "%Y-%m-%d").date() - timedelta(days=30-1)).strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m5_id, p1_id, start_m5, future_date_str(31), 50, start_m5, "New", 1))
    start_m6 = (datetime.strptime(past_date_str(5), "%Y-%m-%d").date() - timedelta(days=30-1)).strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m6_id, p1_id, start_m6, past_date_str(5), 50, start_m6, "Renewal", 1))
    start_m7 = (datetime.strptime(future_date_str(10), "%Y-%m-%d").date() - timedelta(days=60-1)).strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO group_class_memberships (member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active) VALUES (?,?,?,?,?,?,?,?)",
                   (m7_id, p2_id, start_m7, future_date_str(10), 60, start_m7, "New", 0))
    db_manager.conn.commit()
    report_data = db_manager.generate_renewal_report_data()
    assert len(report_data) == 4
    report_data_sorted = sorted(report_data, key=lambda x: x["end_date"])
    assert report_data_sorted[0]["member_name"] == "Today Member"
    assert report_data_sorted[0]["plan_name"] == "Renewal Plan B" # plan_name from group_plans.name
    assert report_data_sorted[0]["end_date"] == today_str()
    assert report_data_sorted[0]["member_phone"] == "200000003"
    assert report_data_sorted[1]["member_name"] == "Upcoming Member"
    assert report_data_sorted[1]["plan_name"] == "Renewal Plan A"
    assert report_data_sorted[1]["end_date"] == future_date_str(15)
    assert report_data_sorted[2]["member_name"] == "Soon Member"
    assert report_data_sorted[2]["plan_name"] == "Renewal Plan A"
    assert report_data_sorted[2]["end_date"] == future_date_str(29)
    assert report_data_sorted[3]["member_name"] == "Edge Case Member"
    assert report_data_sorted[3]["plan_name"] == "Renewal Plan B"
    assert report_data_sorted[3]["end_date"] == future_date_str(30)

# --- PT Membership Stubs ---
def test_add_pt_membership_stub(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    m_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('PT User', '7778889999', 'pt@example.com', ?, 1)", (today_str(),)).lastrowid
    db_manager.conn.commit()
    # add_pt_membership now requires sessions_remaining
    pt_id = db_manager.add_pt_membership(m_id, today_str(), 150.0, 10, "Test PT notes", 10) # sessions_remaining = 10
    assert pt_id is not None
    record = cursor.execute("SELECT member_id, sessions_total, sessions_remaining, notes FROM pt_memberships WHERE id = ?", (pt_id,)).fetchone()
    assert record is not None
    assert record[0] == m_id
    assert record[1] == 10 # sessions_total
    assert record[2] == 10 # sessions_remaining
    assert record[3] == "Test PT notes"

def test_get_all_pt_memberships_for_view(db_manager: DatabaseManager): # Renamed from test_get_all_pt_memberships_stub and updated
    cursor = db_manager.conn.cursor()
    m_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('PT User View', '7778889900', 'pt_view@example.com', ?, 1)", (today_str(),)).lastrowid
    db_manager.conn.commit()

    # Add sample data using the updated add_pt_membership
    db_manager.add_pt_membership(m_id, today_str(), 150.0, 10, "Test PT notes new", 8) # sessions_total=10, sessions_remaining=8
    db_manager.add_pt_membership(m_id, past_date_str(5), 70.0, 5, "Old PT notes", 2)  # sessions_total=5, sessions_remaining=2

    all_pt_memberships_view = db_manager.get_all_pt_memberships_for_view()
    assert len(all_pt_memberships_view) == 2

    # Results are ordered by purchase_date DESC, then id DESC
    # So, the one created with today_str() should be first.
    latest_membership = all_pt_memberships_view[0]
    older_membership = all_pt_memberships_view[1]

    assert latest_membership.member_name == 'PT User View'
    assert latest_membership.sessions_total == 10
    assert latest_membership.sessions_remaining == 8
    assert latest_membership.notes == "Test PT notes new"
    assert latest_membership.purchase_date == today_str()

    assert older_membership.member_name == 'PT User View'
    assert older_membership.sessions_total == 5
    assert older_membership.sessions_remaining == 2
    assert older_membership.notes == "Old PT notes"
    assert older_membership.purchase_date == past_date_str(5)

# Test for simplified MemberView
def test_get_all_members_for_view(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    m1_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Member Alpha', '000000001', 'alpha@example.com', ?, 1)", (past_date_str(10),)).lastrowid
    m2_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('Member Beta', '000000002', 'beta@example.com', ?, 0)", (past_date_str(5),)).lastrowid
    db_manager.conn.commit()

    members_view = db_manager.get_all_members_for_view()
    assert len(members_view) == 2

    # MemberView DTO should have: id, name, phone, email, join_date, is_active
    # Order is by name ASC from the db_manager method
    alpha = members_view[0]
    beta = members_view[1]

    assert alpha.id == m1_id
    assert alpha.name == "Member Alpha"
    assert alpha.phone == "000000001"
    assert alpha.email == "alpha@example.com"
    assert alpha.join_date == past_date_str(10)
    assert alpha.is_active == 1 # is_active is int (0 or 1) in DB

    assert beta.id == m2_id
    assert beta.name == "Member Beta"
    assert beta.phone == "000000002"
    assert beta.email == "beta@example.com"
    assert beta.join_date == past_date_str(5)
    assert beta.is_active == 0

# Test for GroupClassMembershipView (including amount_paid, no display_names)
def test_get_all_group_class_memberships_for_view(db_manager: DatabaseManager):
    cursor = db_manager.conn.cursor()
    m1_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('GC Member A', '111000001', 'gc_a@example.com', ?, 1)", (past_date_str(20),)).lastrowid
    p1_id = cursor.execute("INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active, description, status) VALUES ('GC Plan X', 30, 75.0, 'GC Plan X - 30 days', 1, 'Desc X', 'Active')", ).lastrowid
    db_manager.conn.commit()

    start_date_val = past_date_str(15)
    amount_paid_val = 70.0 # different from plan default to test it's from membership record
    # Create membership using db_manager method which relies on table defaults for status/auto_renewal
    gcm_id = db_manager.create_group_class_membership(m1_id, p1_id, start_date_val, amount_paid_val)
    assert gcm_id is not None

    memberships_view = db_manager.get_all_group_class_memberships_for_view()
    assert len(memberships_view) == 1

    view_item = memberships_view[0]
    # GroupClassMembershipView DTO: id, member_id, member_name, plan_id, plan_name, start_date, end_date, status, auto_renewal_enabled, amount_paid
    assert view_item.id == gcm_id
    assert view_item.member_id == m1_id
    assert view_item.member_name == "GC Member A"
    assert view_item.plan_id == p1_id
    assert view_item.plan_name == "GC Plan X" # From group_plans.name
    assert view_item.start_date == start_date_val
    expected_end_date = (datetime.strptime(start_date_val, "%Y-%m-%d").date() + timedelta(days=30-1)).strftime("%Y-%m-%d")
    assert view_item.end_date == expected_end_date
    assert view_item.status == "Active" # Default from table
    assert view_item.auto_renewal_enabled == 0 # Default from table
    assert view_item.amount_paid == amount_paid_val # Should be from the membership record


def test_delete_pt_membership_stub(db_manager: DatabaseManager): # Kept stub name, but updated call
    cursor = db_manager.conn.cursor()
    m_id = cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES ('PT User 3', '7778889901', 'pt3@example.com', ?, 1)", (today_str(),)).lastrowid
    db_manager.conn.commit()
    pt_id = db_manager.add_pt_membership(m_id, today_str(), 150.0, 10, "To be deleted", 10) # Added sessions_remaining
    assert pt_id is not None

    deleted = db_manager.delete_pt_membership(pt_id)
    assert deleted is True

    record = cursor.execute("SELECT * FROM pt_memberships WHERE id = ?", (pt_id,)).fetchone()
    assert record is None

    not_deleted = db_manager.delete_pt_membership(9999) # Non-existent ID
    assert not_deleted is False

# TODO: Add tests for renamed plan functions (add_group_plan etc.)
# TODO: Add tests for other member and membership functions (get_all, update status etc.)
# TODO: Update financial report tests more thoroughly for new structure (type, item_name) and PT data. (Partially done)

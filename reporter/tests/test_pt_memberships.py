import pytest
import sqlite3
import os
from datetime import date

from reporter.database_manager import DatabaseManager
from reporter.database import create_database

# Define the test database path
TEST_DB_PATH = "test_pt_memberships_app.db"

@pytest.fixture(scope="function")
def db_manager_pt(): # Renamed fixture to avoid conflict if run with other test files
    """
    Fixture to set up and tear down a test database for PT membership tests.
    """
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    create_database(TEST_DB_PATH)

    conn = sqlite3.connect(TEST_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    manager = DatabaseManager(conn)

    # Setup: Create a dummy member to associate PT memberships with
    cursor = conn.cursor()
    cursor.execute("INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                   ("PT Test Member", "7890123456", "pt.test@example.com", date.today().strftime("%Y-%m-%d"), 1))
    conn.commit()
    # Store member_id in the manager instance or return it if preferred, for tests to use
    # For simplicity, tests can re-fetch or assume member_id = 1 if it's the only one.
    # Or, make it part of the yielded tuple: yield manager, member_id

    yield manager # Only manager is yielded for now

    if conn:
        conn.close()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_add_pt_membership_success(db_manager_pt: DatabaseManager):
    """Tests adding a PT membership successfully."""
    cursor = db_manager_pt.conn.cursor()
    cursor.execute("SELECT id FROM members WHERE phone = '7890123456'")
    member_row = cursor.fetchone()
    assert member_row is not None, "Test member not found"
    member_id = member_row[0]

    purchase_d = date.today().strftime("%Y-%m-%d")
    amount_p = 150.0
    sessions_p = 10
    notes_val = "Initial PT package"

    pt_membership_id = db_manager_pt.add_pt_membership(member_id, purchase_d, amount_p, sessions_p, notes_val)
    assert pt_membership_id is not None
    assert isinstance(pt_membership_id, int)

    # Verify in DB
    new_cursor = db_manager_pt.conn.cursor()
    new_cursor.execute("SELECT member_id, purchase_date, amount_paid, sessions_purchased, sessions_remaining, notes FROM pt_memberships WHERE id = ?", (pt_membership_id,))
    record = new_cursor.fetchone()
    assert record is not None
    assert record[0] == member_id
    assert record[1] == purchase_d
    assert record[2] == amount_p
    assert record[3] == sessions_p
    assert record[4] == sessions_p # sessions_remaining should equal sessions_purchased
    assert record[5] == notes_val

def test_get_all_pt_memberships_empty(db_manager_pt: DatabaseManager):
    """Tests retrieving all PT memberships when none exist."""
    all_pt_memberships = db_manager_pt.get_all_pt_memberships()
    assert isinstance(all_pt_memberships, list)
    assert len(all_pt_memberships) == 0

def test_get_all_pt_memberships_with_data(db_manager_pt: DatabaseManager):
    """Tests retrieving all PT memberships with some data."""
    cursor = db_manager_pt.conn.cursor()
    cursor.execute("SELECT id FROM members WHERE phone = '7890123456'")
    member_row = cursor.fetchone()
    assert member_row is not None, "Test member not found"
    member_id = member_row[0]

    db_manager_pt.add_pt_membership(member_id, date.today().strftime("%Y-%m-%d"), 150.0, 10, "Package 1")
    db_manager_pt.add_pt_membership(member_id, date.today().strftime("%Y-%m-%d"), 280.0, 20, "Package 2")

    all_pt_memberships = db_manager_pt.get_all_pt_memberships()
    assert len(all_pt_memberships) == 2
    # Results are ordered by purchase_date DESC, then by id DESC (implicitly by add order if same date)
    assert all_pt_memberships[0]["sessions_purchased"] == 20
    assert all_pt_memberships[1]["sessions_purchased"] == 10
    assert all_pt_memberships[0]["member_name"] == "PT Test Member"


def test_delete_pt_membership_success(db_manager_pt: DatabaseManager):
    """Tests deleting a PT membership successfully."""
    cursor = db_manager_pt.conn.cursor()
    cursor.execute("SELECT id FROM members WHERE phone = '7890123456'")
    member_row = cursor.fetchone()
    assert member_row is not None, "Test member not found"
    member_id = member_row[0]

    pt_membership_id = db_manager_pt.add_pt_membership(member_id, date.today().strftime("%Y-%m-%d"), 100.0, 5, "To delete")
    assert pt_membership_id is not None

    deleted = db_manager_pt.delete_pt_membership(pt_membership_id)
    assert deleted is True

    # Verify not in DB
    new_cursor = db_manager_pt.conn.cursor()
    new_cursor.execute("SELECT * FROM pt_memberships WHERE id = ?", (pt_membership_id,))
    assert new_cursor.fetchone() is None

def test_delete_pt_membership_non_existent(db_manager_pt: DatabaseManager):
    """Tests deleting a non-existent PT membership."""
    deleted = db_manager_pt.delete_pt_membership(9999) # Non-existent ID
    assert deleted is False

if __name__ == "__main__":
    pytest.main()

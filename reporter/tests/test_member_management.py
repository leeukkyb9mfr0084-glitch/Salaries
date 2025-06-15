```python
import pytest
import os
import sys
import sqlite3
from datetime import date

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from reporter import database
from reporter import database_manager
from reporter.database_manager import DatabaseManager
from reporter.app_api import AppAPI

@pytest.fixture
def api_db_fixture(monkeypatch):
    db_path = os.path.abspath("test_member_management.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    monkeypatch.setattr(database_manager, "DB_FILE", db_path)
    database.create_database(db_path)

    conn = sqlite3.connect(db_path)
    db_mngr = DatabaseManager(conn)
    # No initial plan seeding needed for these tests yet,
    # but can be added if specific tests require pre-existing plans.
    # database.seed_initial_plans(db_mngr.conn)

    app_api = AppAPI(conn)

    yield app_api, db_mngr

    conn.close()
    if os.path.exists(db_path):
        os.remove(db_path)

# Tests for app_api.add_member
def test_add_member_success(api_db_fixture):
    app_api, db_mngr = api_db_fixture
    success, message = app_api.add_member(name="New Member", phone="1112223333")
    assert success is True
    assert message == "Member added successfully."
    members = db_mngr.get_all_members(phone_filter="1112223333")
    assert len(members) == 1
    assert members[0][1] == "New Member"

def test_add_member_with_join_date_success(api_db_fixture):
    app_api, db_mngr = api_db_fixture
    join_date_str = "2023-01-15"
    success, message = app_api.add_member(name="Join Date Member", phone="2223334444", join_date=join_date_str)
    assert success is True
    assert message == "Member added successfully."
    members = db_mngr.get_all_members(phone_filter="2223334444")
    assert len(members) == 1
    assert members[0][1] == "Join Date Member"
    assert members[0][3] == join_date_str # join_date is at index 3

def test_add_member_missing_name(api_db_fixture):
    app_api, _ = api_db_fixture
    success, message = app_api.add_member(name="", phone="3334445555")
    assert success is False
    assert "Member name and phone number cannot be empty" in message

def test_add_member_missing_phone(api_db_fixture):
    app_api, _ = api_db_fixture
    success, message = app_api.add_member(name="No Phone Member", phone="")
    assert success is False
    assert "Member name and phone number cannot be empty" in message

def test_add_member_duplicate_phone(api_db_fixture):
    app_api, _ = api_db_fixture
    app_api.add_member(name="Original Member", phone="4445556666") # Add first member
    success, message = app_api.add_member(name="Duplicate Phone Member", phone="4445556666") # Try to add another with same phone
    assert success is False
    assert "likely already exists" in message
```

# Tests for app_api.search_members
def test_search_members_non_existent(api_db_fixture):
    app_api, _ = api_db_fixture
    app_api.add_member(name="Existing Member", phone="5556667777")
    members = app_api.search_members(query="NonExistent")
    assert len(members) == 0

def test_search_members_by_partial_name(api_db_fixture):
    app_api, _ = api_db_fixture
    app_api.add_member(name="SearchMeByName", phone="6667778888")
    members = app_api.search_members(query="SearchMe")
    assert len(members) == 1
    assert members[0][1] == "SearchMeByName"

def test_search_members_by_full_name(api_db_fixture):
    app_api, _ = api_db_fixture
    app_api.add_member(name="FullNameSearch", phone="7778889999")
    members = app_api.search_members(query="FullNameSearch")
    assert len(members) == 1
    assert members[0][1] == "FullNameSearch"

def test_search_members_by_partial_phone(api_db_fixture):
    app_api, _ = api_db_fixture
    app_api.add_member(name="PhoneSearchPartial", phone="8889990000")
    members = app_api.search_members(query="888999")
    assert len(members) == 1
    assert members[0][2] == "8889990000"

def test_search_members_by_full_phone(api_db_fixture):
    app_api, _ = api_db_fixture
    app_api.add_member(name="PhoneSearchFull", phone="9990001111")
    members = app_api.search_members(query="9990001111")
    assert len(members) == 1
    assert members[0][2] == "9990001111"

def test_search_members_case_insensitivity_name(api_db_fixture):
    app_api, _ = api_db_fixture
    app_api.add_member(name="CaseTestMember", phone="1231231234")
    members_lower = app_api.search_members(query="casetestmember")
    assert len(members_lower) == 1
    assert members_lower[0][1] == "CaseTestMember"
    members_upper = app_api.search_members(query="CASET") # Corrected based on assumption
    assert len(members_upper) == 1
    assert members_upper[0][1] == "CaseTestMember"

# Tests for app_api.deactivate_member
def test_deactivate_member_non_existent(api_db_fixture):
    app_api, _ = api_db_fixture
    # Attempt to deactivate a member ID that doesn't exist
    success, message = app_api.deactivate_member(member_id=9999)
    assert success is False
    assert "Failed to deactivate member. Member not found" in message # Or similar error

def test_deactivate_member_success(api_db_fixture):
    app_api, db_mngr = api_db_fixture
    # Add a member
    # app_api.add_member returns success, message. We need the member_id for deactivation.
    # Using db_mngr.add_member_to_db which returns success, message, member_id (if successful)
    # However, app_api.add_member is already tested and is the public API, so let's use it
    # and then fetch the member to get their ID.
    add_success, _ = app_api.add_member(name="ToDeactivate", phone="1010101010")
    assert add_success is True # Ensure member was added

    member_details = db_mngr.get_all_members(phone_filter="1010101010")
    assert len(member_details) == 1
    member_id = member_details[0][0]
    # Assuming get_all_members returns (member_id, client_name, phone, join_date, is_active)
    # and is_active is at index 4.
    assert member_details[0][4] == 1 # is_active is initially true (1)

    # Deactivate the member
    success, message = app_api.deactivate_member(member_id=member_id)
    assert success is True
    assert message == "Member deactivated successfully."

    # Verify member is inactive using db_mngr by fetching all members including inactive ones
    # This requires a way to fetch inactive members, or checking is_active status directly.
    # get_all_members by default only fetches active ones.
    # We'll check the DB directly for simplicity here.
    cursor = db_mngr.conn.cursor()
    cursor.execute("SELECT is_active FROM members WHERE member_id = ?", (member_id,))
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == 0 # is_active should be 0 (False)

    # Verify member is not returned by default get_all_members (which fetches active)
    active_members_after_deactivation = db_mngr.get_all_members(phone_filter="1010101010")
    assert len(active_members_after_deactivation) == 0

# Tests for app_api.get_member_by_phone
def test_get_member_by_phone_exists(api_db_fixture):
    app_api, _ = api_db_fixture
    phone_to_test = "2020202020"
    add_success, _ = app_api.add_member(name="PhoneCheck", phone=phone_to_test)
    assert add_success is True

    member_data = app_api.get_member_by_phone(phone=phone_to_test)
    assert member_data is not None
    assert member_data[0] is not None # member_id
    assert member_data[1] == "PhoneCheck" # client_name
    # member_data from AppAPI.get_member_by_phone maps to db_mngr.get_member_by_phone
    # which returns: member_id, client_name, phone, join_date, is_active
    assert member_data[2] == phone_to_test # phone
    assert member_data[4] == 1 # is_active should be 1 (True)

def test_get_member_by_phone_not_exists(api_db_fixture):
    app_api, _ = api_db_fixture
    phone_to_test = "3030303030"
    # Ensure no member exists with this phone
    member_data = app_api.get_member_by_phone(phone=phone_to_test)
    assert member_data is None

def test_get_member_by_phone_deactivated(api_db_fixture):
    app_api, db_mngr = api_db_fixture
    phone_to_test = "4040404040"
    add_success, _ = app_api.add_member(name="DeactivatedPhoneCheck", phone=phone_to_test)
    assert add_success is True

    member_info = db_mngr.get_all_members(phone_filter=phone_to_test)
    assert len(member_info) == 1
    member_id = member_info[0][0]

    deactivate_success, _ = app_api.deactivate_member(member_id=member_id)
    assert deactivate_success is True

    # get_member_by_phone should only return active members ideally,
    # based on its current implementation in database_manager.py (WHERE is_active = 1)
    member_data = app_api.get_member_by_phone(phone=phone_to_test)
    assert member_data is None

import sqlite3
import pytest
from datetime import date
from typing import List, Dict, Optional

from reporter.database_manager import DatabaseManager
from reporter.database import create_database # To set up schema in memory
from reporter.models import MemberView # Import DTO

# Fixture for database manager with an in-memory database
@pytest.fixture
def db_manager() -> DatabaseManager:
    conn = create_database(":memory:") # Use the actual schema creation
    # No need to seed initial plans for member tests specifically
    conn.execute("PRAGMA foreign_keys = ON;") # Ensure FKs are on for :memory:
    manager = DatabaseManager(connection=conn)
    return manager

# Test data
MEMBER_JOHN = {"name": "John Doe", "phone": "1234567890", "email": "john.doe@example.com"}
MEMBER_JANE = {"name": "Jane Smith", "phone": "0987654321", "email": "jane.smith@example.com"}
MEMBER_ALICE = {"name": "Alice Brown", "phone": "1122334455", "email": "alice.brown@example.com"}

def test_add_member_success(db_manager: DatabaseManager):
    member_id = db_manager.add_member(MEMBER_JOHN["name"], MEMBER_JOHN["phone"], MEMBER_JOHN["email"])
    assert member_id is not None
    assert isinstance(member_id, int)

    # Verify by fetching the member
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name, phone, email, join_date, is_active FROM members WHERE id = ?", (member_id,))
    member_data = cursor.fetchone()
    assert member_data is not None
    assert member_data[0] == MEMBER_JOHN["name"]
    assert member_data[1] == MEMBER_JOHN["phone"]
    assert member_data[2] == MEMBER_JOHN["email"]
    assert member_data[3] == date.today().strftime("%Y-%m-%d")
    assert member_data[4] == 1 # is_active

def test_add_member_duplicate_phone(db_manager: DatabaseManager):
    db_manager.add_member(MEMBER_JOHN["name"], MEMBER_JOHN["phone"], MEMBER_JOHN["email"])
    with pytest.raises(ValueError, match=f"Phone number {MEMBER_JOHN['phone']} already exists."):
        db_manager.add_member("Another Name", MEMBER_JOHN["phone"], "another.email@example.com")

def test_add_member_null_phone(db_manager: DatabaseManager):
    with pytest.raises(sqlite3.IntegrityError): # NOT NULL constraint
        db_manager.add_member(name="Test Null Phone", phone=None, email="null_phone@example.com")

def test_get_all_members_empty(db_manager: DatabaseManager):
    members = db_manager.get_all_members()
    assert isinstance(members, list)
    assert len(members) == 0

def test_get_all_members_multiple(db_manager: DatabaseManager):
    db_manager.add_member(MEMBER_JOHN["name"], MEMBER_JOHN["phone"], MEMBER_JOHN["email"])
    db_manager.add_member(MEMBER_JANE["name"], MEMBER_JANE["phone"], MEMBER_JANE["email"])
    db_manager.add_member(MEMBER_ALICE["name"], MEMBER_ALICE["phone"], MEMBER_ALICE["email"])

    members = db_manager.get_all_members() # This now returns List[MemberView]
    assert len(members) == 3
    # Names should be sorted: Alice, Jane, John
    assert isinstance(members[0], MemberView)
    assert members[0].name == MEMBER_ALICE["name"]
    assert isinstance(members[1], MemberView)
    assert members[1].name == MEMBER_JANE["name"]
    assert isinstance(members[2], MemberView)
    assert members[2].name == MEMBER_JOHN["name"]

    # Check structure of one member (now a MemberView object)
    john_details = next(m for m in members if m.name == MEMBER_JOHN["name"])
    assert john_details.phone == MEMBER_JOHN["phone"]
    assert john_details.email == MEMBER_JOHN["email"]
    assert john_details.join_date == date.today().strftime("%Y-%m-%d")
    assert john_details.is_active is True # is_active is bool in DTO

def test_update_member_success_all_fields(db_manager: DatabaseManager):
    member_id = db_manager.add_member(MEMBER_JOHN["name"], MEMBER_JOHN["phone"], MEMBER_JOHN["email"])
    assert member_id is not None

    updated_name = "Johnathan Doe Updated"
    updated_phone = "1010101010"
    updated_email = "john.doe.updated@example.com"
    updated_is_active = False

    result = db_manager.update_member(member_id, updated_name, updated_phone, updated_email, updated_is_active)
    assert result is True

    # Verify by fetching
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name, phone, email, is_active FROM members WHERE id = ?", (member_id,))
    member_data = cursor.fetchone()
    assert member_data is not None
    assert member_data[0] == updated_name
    assert member_data[1] == updated_phone
    assert member_data[2] == updated_email
    assert member_data[3] == (1 if updated_is_active else 0)

def test_update_member_partial_fields(db_manager: DatabaseManager):
    member_id = db_manager.add_member(MEMBER_JANE["name"], MEMBER_JANE["phone"], MEMBER_JANE["email"])
    assert member_id is not None

    updated_name = "Jane Smith-Jones"
    result = db_manager.update_member(member_id, name=updated_name, is_active=False)
    assert result is True

    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name, phone, email, is_active FROM members WHERE id = ?", (member_id,))
    member_data = cursor.fetchone()
    assert member_data is not None
    assert member_data[0] == updated_name
    assert member_data[1] == MEMBER_JANE["phone"] # Original phone
    assert member_data[2] == MEMBER_JANE["email"] # Original email
    assert member_data[3] == 0 # is_active updated

def test_update_member_phone_uniqueness_violation(db_manager: DatabaseManager):
    member1_id = db_manager.add_member(MEMBER_JOHN["name"], MEMBER_JOHN["phone"], MEMBER_JOHN["email"])
    member2_id = db_manager.add_member(MEMBER_JANE["name"], MEMBER_JANE["phone"], MEMBER_JANE["email"])
    assert member1_id is not None and member2_id is not None

    with pytest.raises(ValueError, match=f"Phone number {MEMBER_JOHN['phone']} already exists for another member."):
        db_manager.update_member(member2_id, phone=MEMBER_JOHN["phone"])

def test_update_member_phone_no_change(db_manager: DatabaseManager):
    member_id = db_manager.add_member(MEMBER_JOHN["name"], MEMBER_JOHN["phone"], MEMBER_JOHN["email"])
    assert member_id is not None
    # Update with the same phone number it already has
    result = db_manager.update_member(member_id, phone=MEMBER_JOHN["phone"])
    assert result is True # Should succeed

def test_update_member_non_existent(db_manager: DatabaseManager):
    result = db_manager.update_member(999, name="Non Existent")
    assert result is False

def test_delete_member_success(db_manager: DatabaseManager):
    member_id = db_manager.add_member(MEMBER_JOHN["name"], MEMBER_JOHN["phone"], MEMBER_JOHN["email"])
    assert member_id is not None

    result = db_manager.delete_member(member_id)
    assert result is True

    # Verify by trying to fetch
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    assert cursor.fetchone() is None

def test_delete_member_non_existent(db_manager: DatabaseManager):
    result = db_manager.delete_member(999)
    assert result is False

if __name__ == "__main__":
    pytest.main()

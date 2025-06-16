import sqlite3
import pytest
from typing import List, Dict, Optional

from reporter.database_manager import DatabaseManager
from reporter.database import create_database # To set up schema in memory

# Fixture for database manager with an in-memory database
@pytest.fixture
def db_manager() -> DatabaseManager:
    conn = create_database(":memory:") # Use the actual schema creation
    # No need to seed initial plans from database.py for these tests,
    # as we want to control plan creation directly.
    manager = DatabaseManager(connection=conn)
    return manager

# Test data for plans
PLAN_MONTHLY = {"name": "Monthly Gold", "duration_days": 30, "default_amount": 100.0}
PLAN_QUARTERLY = {"name": "Quarterly Silver", "duration_days": 90, "default_amount": 270.0}
PLAN_ANNUAL = {"name": "Annual Bronze", "duration_days": 365, "default_amount": 1000.0}

def generate_expected_display_name(name: str, duration_days: int) -> str:
    return f"{name} - {duration_days} days"

def test_add_plan_success(db_manager: DatabaseManager):
    plan_id = db_manager.add_plan(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"], PLAN_MONTHLY["default_amount"])
    assert plan_id is not None
    assert isinstance(plan_id, int)

    expected_display_name = generate_expected_display_name(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"])

    # Verify by fetching the plan
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name, duration_days, default_amount, display_name, is_active FROM plans WHERE id = ?", (plan_id,))
    plan_data = cursor.fetchone()
    assert plan_data is not None
    assert plan_data[0] == PLAN_MONTHLY["name"]
    assert plan_data[1] == PLAN_MONTHLY["duration_days"]
    assert plan_data[2] == PLAN_MONTHLY["default_amount"]
    assert plan_data[3] == expected_display_name
    assert plan_data[4] == 1 # is_active

def test_add_plan_duplicate_display_name(db_manager: DatabaseManager):
    # Add first plan
    db_manager.add_plan(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"], PLAN_MONTHLY["default_amount"])

    # Attempt to add another plan that would generate the same display_name
    # (e.g. same name and duration_days, different amount)
    expected_display_name = generate_expected_display_name(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"])
    with pytest.raises(ValueError, match=f"Display name '{expected_display_name}' already exists."):
        db_manager.add_plan(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"], PLAN_MONTHLY["default_amount"] + 50.0)

def test_get_all_plans_empty(db_manager: DatabaseManager):
    plans = db_manager.get_all_plans()
    assert isinstance(plans, list)
    assert len(plans) == 0

def test_get_all_plans_multiple(db_manager: DatabaseManager):
    db_manager.add_plan(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"], PLAN_MONTHLY["default_amount"])
    db_manager.add_plan(PLAN_QUARTERLY["name"], PLAN_QUARTERLY["duration_days"], PLAN_QUARTERLY["default_amount"])
    db_manager.add_plan(PLAN_ANNUAL["name"], PLAN_ANNUAL["duration_days"], PLAN_ANNUAL["default_amount"])

    plans = db_manager.get_all_plans()
    assert len(plans) == 3
    # Plans should be sorted by name: Annual Bronze, Monthly Gold, Quarterly Silver
    assert plans[0]["name"] == PLAN_ANNUAL["name"]
    assert plans[1]["name"] == PLAN_MONTHLY["name"]
    assert plans[2]["name"] == PLAN_QUARTERLY["name"]

    # Check structure of one plan
    monthly_details = next(p for p in plans if p["name"] == PLAN_MONTHLY["name"])
    expected_monthly_display_name = generate_expected_display_name(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"])
    assert monthly_details["duration_days"] == PLAN_MONTHLY["duration_days"]
    assert monthly_details["default_amount"] == PLAN_MONTHLY["default_amount"]
    assert monthly_details["display_name"] == expected_monthly_display_name
    assert monthly_details["is_active"] == 1

def test_update_plan_success_all_fields(db_manager: DatabaseManager):
    plan_id = db_manager.add_plan(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"], PLAN_MONTHLY["default_amount"])
    assert plan_id is not None

    updated_name = "Monthly Platinum"
    updated_duration = 31 # Changed duration
    updated_amount = 120.0
    updated_is_active = False
    expected_new_display_name = generate_expected_display_name(updated_name, updated_duration)

    result = db_manager.update_plan(plan_id, updated_name, updated_duration, updated_amount, updated_is_active)
    assert result is True

    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name, duration_days, default_amount, display_name, is_active FROM plans WHERE id = ?", (plan_id,))
    plan_data = cursor.fetchone()
    assert plan_data is not None
    assert plan_data[0] == updated_name
    assert plan_data[1] == updated_duration
    assert plan_data[2] == updated_amount
    assert plan_data[3] == expected_new_display_name
    assert plan_data[4] == (1 if updated_is_active else 0)

def test_update_plan_partial_fields_no_display_name_change(db_manager: DatabaseManager):
    plan_id = db_manager.add_plan(PLAN_QUARTERLY["name"], PLAN_QUARTERLY["duration_days"], PLAN_QUARTERLY["default_amount"])
    assert plan_id is not None
    original_display_name = generate_expected_display_name(PLAN_QUARTERLY["name"], PLAN_QUARTERLY["duration_days"])

    updated_amount = 280.0
    result = db_manager.update_plan(plan_id, default_amount=updated_amount, is_active=False)
    assert result is True

    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name, duration_days, default_amount, display_name, is_active FROM plans WHERE id = ?", (plan_id,))
    plan_data = cursor.fetchone()
    assert plan_data is not None
    assert plan_data[0] == PLAN_QUARTERLY["name"] # Original name
    assert plan_data[1] == PLAN_QUARTERLY["duration_days"] # Original duration
    assert plan_data[2] == updated_amount
    assert plan_data[3] == original_display_name # Display name should not change
    assert plan_data[4] == 0 # is_active updated

def test_update_plan_display_name_uniqueness_violation(db_manager: DatabaseManager):
    plan1_id = db_manager.add_plan(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"], PLAN_MONTHLY["default_amount"])
    plan2_id = db_manager.add_plan(PLAN_QUARTERLY["name"], PLAN_QUARTERLY["duration_days"], PLAN_QUARTERLY["default_amount"])
    assert plan1_id is not None and plan2_id is not None

    # Try to update plan2 to have the same name and duration as plan1
    expected_colliding_display_name = generate_expected_display_name(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"])
    with pytest.raises(ValueError, match=f"Display name '{expected_colliding_display_name}' already exists for another plan."):
        db_manager.update_plan(plan2_id, name=PLAN_MONTHLY["name"], duration_days=PLAN_MONTHLY["duration_days"])

def test_update_plan_same_details_no_display_name_change(db_manager: DatabaseManager):
    plan_id = db_manager.add_plan(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"], PLAN_MONTHLY["default_amount"])
    assert plan_id is not None
    original_display_name = generate_expected_display_name(PLAN_MONTHLY["name"], PLAN_MONTHLY["duration_days"])

    # Update with same name and duration, but different amount (should not trigger display_name regeneration error)
    result = db_manager.update_plan(plan_id, name=PLAN_MONTHLY["name"], duration_days=PLAN_MONTHLY["duration_days"], default_amount=105.0)
    assert result is True

    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT display_name, default_amount FROM plans WHERE id = ?", (plan_id,))
    plan_data = cursor.fetchone()
    assert plan_data[0] == original_display_name
    assert plan_data[1] == 105.0

def test_update_plan_non_existent(db_manager: DatabaseManager):
    result = db_manager.update_plan(999, name="Non Existent Plan")
    assert result is False

def test_delete_plan_success(db_manager: DatabaseManager):
    plan_id = db_manager.add_plan(PLAN_ANNUAL["name"], PLAN_ANNUAL["duration_days"], PLAN_ANNUAL["default_amount"])
    assert plan_id is not None

    result = db_manager.delete_plan(plan_id)
    assert result is True

    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
    assert cursor.fetchone() is None

def test_delete_plan_non_existent(db_manager: DatabaseManager):
    result = db_manager.delete_plan(999)
    assert result is False

if __name__ == "__main__":
    pytest.main()

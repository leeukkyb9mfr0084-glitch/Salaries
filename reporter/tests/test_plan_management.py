import sqlite3
import pytest
from typing import List, Dict, Optional

from reporter.database_manager import DatabaseManager
from reporter.database import create_database
from reporter.models import GroupPlanView # Import DTO

@pytest.fixture
def db_manager() -> DatabaseManager:
    conn = create_database(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;") # Ensure FKs are on for :memory:
    manager = DatabaseManager(connection=conn)
    return manager

# Test data for group plans
GROUP_PLAN_MONTHLY = {"name": "Monthly Gold", "duration_days": 30, "default_amount": 100.0}
GROUP_PLAN_QUARTERLY = {"name": "Quarterly Silver", "duration_days": 90, "default_amount": 270.0}
GROUP_PLAN_ANNUAL = {"name": "Annual Bronze", "duration_days": 365, "default_amount": 1000.0}

def generate_expected_display_name(name: str, duration_days: int) -> str:
    return f"{name} - {duration_days} days"

def test_add_group_plan_success(db_manager: DatabaseManager): # RENAMED
    plan_id = db_manager.add_group_plan(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"], GROUP_PLAN_MONTHLY["default_amount"]) # RENAMED
    assert plan_id is not None
    assert isinstance(plan_id, int)

    expected_display_name = generate_expected_display_name(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"])

    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name, duration_days, default_amount, display_name, is_active FROM group_plans WHERE id = ?", (plan_id,)) # RENAMED table
    plan_data = cursor.fetchone()
    assert plan_data is not None
    assert plan_data[0] == GROUP_PLAN_MONTHLY["name"]
    assert plan_data[1] == GROUP_PLAN_MONTHLY["duration_days"]
    assert plan_data[2] == GROUP_PLAN_MONTHLY["default_amount"]
    assert plan_data[3] == expected_display_name
    assert plan_data[4] == 1

def test_add_group_plan_duplicate_display_name(db_manager: DatabaseManager): # RENAMED
    db_manager.add_group_plan(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"], GROUP_PLAN_MONTHLY["default_amount"]) # RENAMED

    expected_display_name = generate_expected_display_name(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"])
    with pytest.raises(ValueError, match=f"Display name '{expected_display_name}' already exists."): # Error message from DB manager might still say "Display name"
        db_manager.add_group_plan(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"], GROUP_PLAN_MONTHLY["default_amount"] + 50.0) # RENAMED

def test_get_all_group_plans_empty(db_manager: DatabaseManager): # RENAMED
    plans = db_manager.get_all_group_plans() # RENAMED
    assert isinstance(plans, list)
    assert len(plans) == 0

def test_get_all_group_plans_multiple(db_manager: DatabaseManager): # RENAMED
    db_manager.add_group_plan(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"], GROUP_PLAN_MONTHLY["default_amount"]) # RENAMED
    db_manager.add_group_plan(GROUP_PLAN_QUARTERLY["name"], GROUP_PLAN_QUARTERLY["duration_days"], GROUP_PLAN_QUARTERLY["default_amount"]) # RENAMED
    db_manager.add_group_plan(GROUP_PLAN_ANNUAL["name"], GROUP_PLAN_ANNUAL["duration_days"], GROUP_PLAN_ANNUAL["default_amount"]) # RENAMED

    plans = db_manager.get_all_group_plans() # RENAMED - now returns List[GroupPlanView]
    assert len(plans) == 3
    # Assuming sort order by name ASC (Annual, Monthly, Quarterly based on current names)
    assert isinstance(plans[0], GroupPlanView)
    assert plans[0].name == GROUP_PLAN_ANNUAL["name"]
    assert isinstance(plans[1], GroupPlanView)
    assert plans[1].name == GROUP_PLAN_MONTHLY["name"]
    assert isinstance(plans[2], GroupPlanView)
    assert plans[2].name == GROUP_PLAN_QUARTERLY["name"]

    monthly_details = next(p for p in plans if p.name == GROUP_PLAN_MONTHLY["name"])
    expected_monthly_display_name = generate_expected_display_name(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"])
    assert monthly_details.duration_days == GROUP_PLAN_MONTHLY["duration_days"]
    assert monthly_details.default_amount == GROUP_PLAN_MONTHLY["default_amount"]
    assert monthly_details.display_name == expected_monthly_display_name
    assert monthly_details.is_active is True # is_active is bool in DTO

def test_update_group_plan_success_all_fields(db_manager: DatabaseManager): # RENAMED
    plan_id = db_manager.add_group_plan(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"], GROUP_PLAN_MONTHLY["default_amount"]) # RENAMED
    assert plan_id is not None

    updated_name = "Monthly Platinum"
    updated_duration = 31
    updated_amount = 120.0
    updated_is_active = False # New schema uses BOOLEAN, so False is appropriate
    expected_new_display_name = generate_expected_display_name(updated_name, updated_duration)

    result = db_manager.update_group_plan(plan_id, updated_name, updated_duration, updated_amount, updated_is_active) # RENAMED
    assert result is True

    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name, duration_days, default_amount, display_name, is_active FROM group_plans WHERE id = ?", (plan_id,)) # RENAMED table
    plan_data = cursor.fetchone()
    assert plan_data is not None
    assert plan_data[0] == updated_name
    assert plan_data[1] == updated_duration
    assert plan_data[2] == updated_amount
    assert plan_data[3] == expected_new_display_name
    assert plan_data[4] == (0 if not updated_is_active else 1) # DB stores boolean as 0 or 1

def test_update_group_plan_partial_fields_no_display_name_change(db_manager: DatabaseManager): # RENAMED
    plan_id = db_manager.add_group_plan(GROUP_PLAN_QUARTERLY["name"], GROUP_PLAN_QUARTERLY["duration_days"], GROUP_PLAN_QUARTERLY["default_amount"]) # RENAMED
    assert plan_id is not None
    original_display_name = generate_expected_display_name(GROUP_PLAN_QUARTERLY["name"], GROUP_PLAN_QUARTERLY["duration_days"])

    updated_amount = 280.0
    result = db_manager.update_group_plan(plan_id, default_amount=updated_amount, is_active=False) # RENAMED
    assert result is True

    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name, duration_days, default_amount, display_name, is_active FROM group_plans WHERE id = ?", (plan_id,)) # RENAMED table
    plan_data = cursor.fetchone()
    assert plan_data is not None
    assert plan_data[0] == GROUP_PLAN_QUARTERLY["name"]
    assert plan_data[1] == GROUP_PLAN_QUARTERLY["duration_days"]
    assert plan_data[2] == updated_amount
    assert plan_data[3] == original_display_name
    assert plan_data[4] == 0

def test_update_group_plan_display_name_uniqueness_violation(db_manager: DatabaseManager): # RENAMED
    plan1_id = db_manager.add_group_plan(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"], GROUP_PLAN_MONTHLY["default_amount"]) # RENAMED
    plan2_id = db_manager.add_group_plan(GROUP_PLAN_QUARTERLY["name"], GROUP_PLAN_QUARTERLY["duration_days"], GROUP_PLAN_QUARTERLY["default_amount"]) # RENAMED
    assert plan1_id is not None and plan2_id is not None

    expected_colliding_display_name = generate_expected_display_name(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"])
    with pytest.raises(ValueError, match=f"Display name '{expected_colliding_display_name}' already exists for another group_plan."): # Adjusted error message
        db_manager.update_group_plan(plan2_id, name=GROUP_PLAN_MONTHLY["name"], duration_days=GROUP_PLAN_MONTHLY["duration_days"]) # RENAMED

def test_update_group_plan_same_details_no_display_name_change(db_manager: DatabaseManager): # RENAMED
    plan_id = db_manager.add_group_plan(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"], GROUP_PLAN_MONTHLY["default_amount"]) # RENAMED
    assert plan_id is not None
    original_display_name = generate_expected_display_name(GROUP_PLAN_MONTHLY["name"], GROUP_PLAN_MONTHLY["duration_days"])

    result = db_manager.update_group_plan(plan_id, name=GROUP_PLAN_MONTHLY["name"], duration_days=GROUP_PLAN_MONTHLY["duration_days"], default_amount=105.0) # RENAMED
    assert result is True

    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT display_name, default_amount FROM group_plans WHERE id = ?", (plan_id,)) # RENAMED table
    plan_data = cursor.fetchone()
    assert plan_data[0] == original_display_name
    assert plan_data[1] == 105.0

def test_update_group_plan_non_existent(db_manager: DatabaseManager): # RENAMED
    result = db_manager.update_group_plan(999, name="Non Existent Plan") # RENAMED
    assert result is False

def test_delete_group_plan_success(db_manager: DatabaseManager): # RENAMED
    plan_id = db_manager.add_group_plan(GROUP_PLAN_ANNUAL["name"], GROUP_PLAN_ANNUAL["duration_days"], GROUP_PLAN_ANNUAL["default_amount"]) # RENAMED
    assert plan_id is not None

    result = db_manager.delete_group_plan(plan_id) # RENAMED
    assert result is True

    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT * FROM group_plans WHERE id = ?", (plan_id,)) # RENAMED table
    assert cursor.fetchone() is None

def test_delete_group_plan_non_existent(db_manager: DatabaseManager): # RENAMED
    result = db_manager.delete_group_plan(999) # RENAMED
    assert result is False

if __name__ == "__main__":
    pytest.main()

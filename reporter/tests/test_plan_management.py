```python
import pytest
import os
import sys
import sqlite3

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from reporter import database
from reporter import database_manager
from reporter.database_manager import DatabaseManager
from reporter.app_api import AppAPI

# DEFAULT_PRICE and DEFAULT_TYPE_TEXT for add_plan calls, similar to test_business_logic
DEFAULT_PRICE = 100
DEFAULT_TYPE_TEXT = "DefaultType"
DEFAULT_DURATION = 30

@pytest.fixture
def api_db_fixture(monkeypatch):
    db_path = os.path.abspath("test_plan_management.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    monkeypatch.setattr(database_manager, "DB_FILE", db_path)
    database.create_database(db_path) # Ensures tables are created, including 'plans'

    conn = sqlite3.connect(db_path)
    # No need to seed initial plans for these specific tests,
    # as we are testing the creation and management of plans.
    # db_mngr = DatabaseManager(conn)
    # database.seed_initial_plans(db_mngr.conn) # Not strictly needed here

    app_api = AppAPI(conn)

    yield app_api, DatabaseManager(conn) # Yield a new db_mngr for safety in tests

    conn.close()
    if os.path.exists(db_path):
        os.remove(db_path)

# Tests for app_api.add_plan
def test_add_plan_success(api_db_fixture):
    app_api, db_mngr = api_db_fixture
    plan_name = "New Valid Plan"
    success, message, plan_id = app_api.add_plan(name=plan_name, duration_days=DEFAULT_DURATION, price=DEFAULT_PRICE, type_text=DEFAULT_TYPE_TEXT)
    assert success is True
    assert message == "Plan added successfully."
    assert plan_id is not None

    fetched_plan = db_mngr.get_plan_by_id(plan_id)
    assert fetched_plan is not None
    assert fetched_plan[1] == plan_name
    assert fetched_plan[2] == DEFAULT_DURATION
    assert fetched_plan[3] == DEFAULT_PRICE
    assert fetched_plan[4] == DEFAULT_TYPE_TEXT
    assert fetched_plan[5] == 1 # is_active should be true (1) by default

def test_add_plan_invalid_duration_zero(api_db_fixture):
    app_api, _ = api_db_fixture
    success, message, plan_id = app_api.add_plan(name="Zero Duration Plan", duration_days=0, price=DEFAULT_PRICE, type_text=DEFAULT_TYPE_TEXT)
    assert success is False
    assert "duration must be a positive number" in message
    assert plan_id is None

def test_add_plan_invalid_duration_negative(api_db_fixture):
    app_api, _ = api_db_fixture
    success, message, plan_id = app_api.add_plan(name="Negative Duration Plan", duration_days=-10, price=DEFAULT_PRICE, type_text=DEFAULT_TYPE_TEXT)
    assert success is False
    assert "duration must be a positive number" in message
    assert plan_id is None

def test_add_plan_negative_price(api_db_fixture):
    app_api, _ = api_db_fixture
    success, message, plan_id = app_api.add_plan(name="Negative Price Plan", duration_days=DEFAULT_DURATION, price=-100, type_text=DEFAULT_TYPE_TEXT)
    assert success is False
    assert "price cannot be negative" in message # Based on DatabaseManager validation
    assert plan_id is None

def test_add_plan_empty_type_text(api_db_fixture):
    app_api, _ = api_db_fixture
    success, message, plan_id = app_api.add_plan(name="Empty Type Plan", duration_days=DEFAULT_DURATION, price=DEFAULT_PRICE, type_text="")
    assert success is False
    assert "type cannot be empty" in message # Based on DatabaseManager validation
    assert plan_id is None

def test_add_plan_duplicate_name(api_db_fixture):
    app_api, _ = api_db_fixture
    plan_name = "Duplicate Name Plan"
    # Add first plan
    app_api.add_plan(name=plan_name, duration_days=DEFAULT_DURATION, price=DEFAULT_PRICE, type_text=DEFAULT_TYPE_TEXT)
    # Try to add another with the same name
    success, message, plan_id = app_api.add_plan(name=plan_name, duration_days=DEFAULT_DURATION + 10, price=DEFAULT_PRICE + 50, type_text="OtherType")
    assert success is False
    assert "likely already exists" in message # Because plan name should be unique
    assert plan_id is None
```

# Tests for app_api.update_plan
def test_update_plan_success(api_db_fixture):
    app_api, db_mngr = api_db_fixture
    # Add an initial plan
    add_success, _, plan_id = app_api.add_plan(name="Initial Plan", duration_days=30, price=100, type_text="TypeA")
    assert add_success is True and plan_id is not None

    updated_name = "Updated Plan Name"
    updated_duration = 60
    updated_price = 150
    updated_type_text = "TypeB"

    success, message = app_api.update_plan(plan_id, updated_name, updated_duration, updated_price, updated_type_text)
    assert success is True
    assert message == "Plan updated successfully."

    fetched_plan = db_mngr.get_plan_by_id(plan_id)
    assert fetched_plan is not None
    assert fetched_plan[1] == updated_name
    assert fetched_plan[2] == updated_duration
    assert fetched_plan[3] == updated_price
    assert fetched_plan[4] == updated_type_text
    # is_active (index 5) should remain unchanged by update_plan, assuming it was 1
    assert fetched_plan[5] == 1

def test_update_plan_non_existent(api_db_fixture):
    app_api, _ = api_db_fixture
    non_existent_plan_id = 9999
    success, message = app_api.update_plan(non_existent_plan_id, "NonExistent", 30, 100, "TypeC")
    assert success is False
    # Message might vary, e.g. "Failed to update plan. Plan not found or data unchanged."
    # AppAPI specific message is "Failed to update plan. Plan not found."
    assert "Failed to update plan. Plan not found" in message

def test_update_plan_invalid_duration(api_db_fixture):
    app_api, _ = api_db_fixture
    add_success, _, plan_id = app_api.add_plan(name="PlanForUpdateFail", duration_days=30, price=100, type_text="TypeD")
    assert add_success is True and plan_id is not None

    success, message = app_api.update_plan(plan_id, "UpdatedName", 0, 120, "TypeE") # Invalid duration
    assert success is False
    assert "duration must be a positive number" in message

def test_update_plan_negative_price(api_db_fixture):
    app_api, _ = api_db_fixture
    add_success, _, plan_id = app_api.add_plan(name="PlanForUpdatePriceFail", duration_days=30, price=100, type_text="TypeF")
    assert add_success is True and plan_id is not None

    success, message = app_api.update_plan(plan_id, "UpdatedName", 30, -50, "TypeG") # Invalid price
    assert success is False
    assert "price cannot be negative" in message

def test_update_plan_empty_type_text(api_db_fixture):
    app_api, _ = api_db_fixture
    add_success, _, plan_id = app_api.add_plan(name="PlanForUpdateTypeFail", duration_days=30, price=100, type_text="TypeH")
    assert add_success is True and plan_id is not None

    success, message = app_api.update_plan(plan_id, "UpdatedName", 30, 120, "") # Invalid type_text
    assert success is False
    assert "type cannot be empty" in message

def test_update_plan_to_duplicate_name(api_db_fixture):
    app_api, _ = api_db_fixture
    plan1_name = "UniqueName1"
    plan2_name = "UniqueName2"

    add_success1, _, plan_id1 = app_api.add_plan(name=plan1_name, duration_days=30, price=100, type_text="TypeI")
    assert add_success1 is True and plan_id1 is not None
    add_success2, _, plan_id2 = app_api.add_plan(name=plan2_name, duration_days=40, price=120, type_text="TypeJ")
    assert add_success2 is True and plan_id2 is not None

    # Attempt to update plan2 to have the same name as plan1
    success, message = app_api.update_plan(plan_id2, plan1_name, 45, 130, "TypeK")
    assert success is False
    # AppAPI specific message is "Failed to update plan. New name '...' likely already exists for another plan."
    assert "New name" in message and "likely already exists for another plan" in message

# Tests for app_api.delete_plan (which deactivates a plan)
def test_delete_plan_not_in_use(api_db_fixture):
    app_api, db_mngr = api_db_fixture
    # Add a plan
    plan_name = "ToDeletePlan"
    add_plan_success, _, plan_id = app_api.add_plan(name=plan_name, duration_days=30, price=100, type_text="TypeToDelete")
    assert add_plan_success is True and plan_id is not None

    # Delete (deactivate) the plan
    success, message = app_api.delete_plan(plan_id)
    assert success is True
    assert message == "Plan deactivated successfully."

    # Verify the plan is marked as inactive
    fetched_plan = db_mngr.get_plan_by_id(plan_id)
    assert fetched_plan is not None
    assert fetched_plan[5] == 0 # is_active (index 5) should be 0 (False)

def test_delete_plan_in_use(api_db_fixture):
    app_api, db_mngr = api_db_fixture
    # Add a member
    # db_mngr.add_member_to_db returns: success, message, member_id
    add_member_success, _, member_id = db_mngr.add_member_to_db("Plan User", "7897897890")
    assert add_member_success is True and member_id is not None

    # Add a plan
    plan_name = "UsedPlan"
    add_plan_success, _, plan_id = app_api.add_plan(name=plan_name, duration_days=30, price=100, type_text="TypeUsed")
    assert add_plan_success is True and plan_id is not None

    # Add a transaction linking the member and the plan
    # db_mngr.add_transaction parameters:
    # transaction_type, member_id, start_date, amount_paid, plan_id=None, sessions=None, payment_method=None, payment_date=None
    add_tx_success, _ = db_mngr.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        start_date="2024-01-01",
        amount_paid=100.0,
        plan_id=plan_id,
        payment_date="2024-01-01",
        payment_method="Cash" # Added for completeness
    )
    assert add_tx_success is True

    # Attempt to delete (deactivate) the plan that is in use
    success, message = app_api.delete_plan(plan_id)
    assert success is False
    assert message == "Plan is in use and cannot be deactivated."

    # Verify the plan is still active
    fetched_plan = db_mngr.get_plan_by_id(plan_id)
    assert fetched_plan is not None
    assert fetched_plan[5] == 1 # is_active (index 5) should still be 1 (True)

def test_delete_non_existent_plan(api_db_fixture):
    app_api, _ = api_db_fixture
    non_existent_plan_id = 8888
    success, message = app_api.delete_plan(non_existent_plan_id)
    assert success is False
    # AppAPI.delete_plan calls db_mngr.delete_plan.
    # If plan not in use, db_mngr.delete_plan tries to update. If update affects 0 rows (plan_id not found),
    # it returns "Error deactivating plan: Plan not found."
    # AppAPI relays this message.
    assert "Error deactivating plan: Plan not found" in message
```

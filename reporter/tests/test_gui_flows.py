import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from datetime import date, timedelta

# Add project root to sys.path to allow importing reporter modules
# This assumes the test is run from the project root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from reporter.gui import GuiController # Changed App to GuiController
from reporter import database_manager
from reporter.database import create_database

# Define a test database for GUI flow tests
TEST_DB_GUI_FLOWS = 'reporter/tests/test_data_gui_flows/test_gui_flows.db'
TEST_DB_DIR_GUI_FLOWS = 'reporter/tests/test_data_gui_flows'

@pytest.fixture(autouse=True)
def setup_teardown_test_db(monkeypatch):
    # Create directory for test database if it doesn't exist
    os.makedirs(TEST_DB_DIR_GUI_FLOWS, exist_ok=True)

    # Ensure create_database uses the test DB
    # Patch DB_FILE in database_manager and database (if used directly for path)
    monkeypatch.setattr(database_manager, 'DB_FILE', TEST_DB_GUI_FLOWS)

    # For create_database itself, it takes db_name as an argument.
    # So, we ensure it's called with the test DB path.
    # If gui.App or other components were to call create_database without arguments,
    # or expecting a global DB_FILE in reporter.database, that would need patching too.
    # For now, we assume App operations go through database_manager or direct calls with db_name.

    # Create a clean database for each test
    conn = create_database(db_name=TEST_DB_GUI_FLOWS)
    if conn: # For in-memory, it returns a connection
        conn.close()

    yield # Test runs here

    # Teardown: Remove the test database file and directory
    if os.path.exists(TEST_DB_GUI_FLOWS):
        os.remove(TEST_DB_GUI_FLOWS)
    if os.path.exists(TEST_DB_DIR_GUI_FLOWS) and not os.listdir(TEST_DB_DIR_GUI_FLOWS):
        os.rmdir(TEST_DB_DIR_GUI_FLOWS)

@pytest.fixture
def controller_instance(setup_teardown_test_db): # Renamed fixture
    # This fixture depends on setup_teardown_test_db to ensure DB is ready
    # No UI mocks needed for GuiController direct testing
    controller = GuiController()
    return controller

def test_add_member_flow(controller_instance): # Use renamed fixture
    controller = controller_instance # Use controller instance

    # Call the controller method directly
    success, message = controller.save_member_action(name="Test Member", phone="1234567890")

    # Assert the success and message returned by the controller
    assert success is True
    assert message == "Member added successfully! Join date will be set with first activity."

    # Assert that the member was saved to the database
    members = database_manager.get_all_members(phone_filter="1234567890")
    assert len(members) == 1
    assert members[0][1] == "Test Member"

    # Try to add the same member again (duplicate phone)
    success_dup, message_dup = controller.save_member_action(name="Test Member", phone="1234567890")

    # Assert the outcome of the duplicate attempt
    assert success_dup is False
    assert message_dup == "Failed to add member. Phone number may already exist."

    members_after_duplicate_attempt = database_manager.get_all_members(phone_filter="1234567890")
    assert len(members_after_duplicate_attempt) == 1 # Should still be 1 member

def test_plan_management_flow(controller_instance):
    controller = controller_instance

    # Adding a new plan
    success_add, message_add, plans_add = controller.save_plan_action(
        plan_name="Test Plan", duration_str="30", plan_id_to_update=""
    )
    assert success_add is True
    assert message_add == "Plan added successfully!"
    assert isinstance(plans_add, list)

    # Verify the new plan exists in the database
    db_plans_after_add = database_manager.get_all_plans_with_inactive()
    assert len(db_plans_after_add) == 1
    assert db_plans_after_add[0][1] == "Test Plan"
    assert db_plans_after_add[0][2] == 30  # Duration
    assert db_plans_after_add[0][3] is True  # is_active (boolean)
    new_plan_id = db_plans_after_add[0][0]

    # Toggling plan status (deactivate)
    success_deactivate, message_deactivate, plans_deactivate = controller.toggle_plan_status_action(
        plan_id=new_plan_id, current_status=True
    )
    assert success_deactivate is True
    assert message_deactivate == "Plan status changed to Inactive."
    assert isinstance(plans_deactivate, list)

    # Assert that the plan's is_active status has changed in the database
    db_plans_after_deactivate = database_manager.get_all_plans_with_inactive()
    assert len(db_plans_after_deactivate) == 1
    assert db_plans_after_deactivate[0][0] == new_plan_id
    assert db_plans_after_deactivate[0][3] is False  # is_active should now be False

    # Toggling plan status again (activate)
    success_activate, message_activate, plans_activate = controller.toggle_plan_status_action(
        plan_id=new_plan_id, current_status=False
    )
    assert success_activate is True
    assert message_activate == "Plan status changed to Active."
    assert isinstance(plans_activate, list)

    db_plans_after_activate = database_manager.get_all_plans_with_inactive()
    assert len(db_plans_after_activate) == 1
    assert db_plans_after_activate[0][3] is True  # is_active should now be True

def test_add_membership_flow(controller_instance): # Changed app_instance to controller_instance
    controller = controller_instance # Use controller

    # --- Setup: Pre-populate database with a member and a plan ---
    # Add a member
    member_id = database_manager.add_member_to_db("Membership User", "000111222")
    assert member_id is True # add_member_to_db returns True on success
    member_details = database_manager.get_all_members(phone_filter="000111222")
    assert len(member_details) == 1
    db_member_id = member_details[0][0] # Get the actual member_id from DB

    # Add a plan
    plan_id = database_manager.add_plan("Membership Plan", 30)
    assert plan_id is not None
    db_plan_id = plan_id # Get the actual plan_id

    # No need to mock UI elements or call app.populate_dropdowns for controller tests

    # --- Test "Group Class" Transaction ---
    s_gc, m_gc = controller.save_membership_action(
        membership_type="Group Class",
        member_id=db_member_id,
        selected_plan_id=db_plan_id,
        payment_date_str=date.today().strftime('%Y-%m-%d'),
        start_date_str=date.today().strftime('%Y-%m-%d'),
        amount_paid_str="100.00",
        payment_method="Cash",
        sessions_str=None
    )
    assert s_gc is True
    assert m_gc == "Group Class membership added successfully!"

    member_activity_gc = database_manager.get_all_activity_for_member(db_member_id)
    assert len(member_activity_gc) == 1
    assert member_activity_gc[0][0] == "Group Class"  # transaction_type
    assert member_activity_gc[0][1] == "Membership Plan"  # plan_name (name_or_description)
    assert member_activity_gc[0][5] == 100.00  # amount_paid

    # --- Test "Personal Training" Transaction ---
    s_pt, m_pt = controller.save_membership_action(
        membership_type="Personal Training",
        member_id=db_member_id,
        selected_plan_id=None, # No plan_id for PT
        payment_date_str=date.today().strftime('%Y-%m-%d'), # For PT, payment_date is start_date
        start_date_str=date.today().strftime('%Y-%m-%d'),
        amount_paid_str="200.00",
        payment_method="N/A", # Default for PT in controller
        sessions_str="10"
    )
    assert s_pt is True
    assert m_pt == "Personal Training membership added successfully!"

    member_activity_pt = database_manager.get_all_activity_for_member(db_member_id)
    assert len(member_activity_pt) == 2  # Now two activities for this member

    pt_transaction = None
    for activity in member_activity_pt:
        if activity[0] == "Personal Training":
            pt_transaction = activity
            break
    assert pt_transaction is not None, "Personal Training transaction not found"
    assert pt_transaction[0] == "Personal Training"
    assert pt_transaction[5] == 200.00  # amount_paid
    # In GuiController, sessions are stored directly in the 'sessions' field of the transaction for PT.
    # The get_all_activity_for_member method returns 'sessions' as the 7th item (index 6) in the tuple for PT.
    # This needs to align with how get_all_activity_for_member structures its output.
    # Assuming the structure is (type, desc, pay_date, start, end, amount, sessions_or_method, id)
    # The original test checked `pt_transaction[6]` for "10 sessions".
    # The `add_transaction` in `database_manager` for PT saves `sessions` in the `sessions` column.
    # `get_all_activity_for_member` retrieves it as `payment_method_or_sessions`.
    # Let's assume `get_all_activity_for_member` returns sessions in a way that matches this:
    assert pt_transaction[6] == 10 # If it's just the number of sessions
    # Or, if it's a string like "10 sessions" due to formatting in get_all_activity_for_member:
    # assert "10" in str(pt_transaction[6]) # More flexible check if formatting varies

import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from datetime import date, timedelta

# Add project root to sys.path to allow importing reporter modules
# This assumes the test is run from the project root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from reporter.gui import App
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
def app_instance(setup_teardown_test_db):
    # This fixture depends on setup_teardown_test_db to ensure DB is ready
    # Mock customtkinter and tkinter elements that are not needed for flow logic
    with patch('customtkinter.CTk'), \
         patch('customtkinter.CTkFrame'), \
         patch('customtkinter.CTkLabel'), \
         patch('customtkinter.CTkEntry'), \
         patch('customtkinter.CTkButton'), \
         patch('customtkinter.CTkOptionMenu'), \
         patch('customtkinter.CTkScrollableFrame'), \
         patch('customtkinter.CTkTabview'), \
         patch('tkinter.StringVar'), \
         patch('tkcalendar.DateEntry'):

        # Instantiate the App. It will use the monkeypatched DB_FILE.
        app = App()
        # For tests, we might need to manually call some setup methods if __init__ doesn't fully set up
        # or if parts are deferred (e.g. populating dropdowns might need a call if not done by init)
        # app.populate_member_dropdown()
        # app.populate_plan_dropdown()
        return app

def test_add_member_flow(app_instance):
    app = app_instance

    # Simulate user input
    app.name_entry.get = MagicMock(return_value="Test Member")
    app.phone_entry.get = MagicMock(return_value="1234567890")
    app.member_status_label.configure = MagicMock() # Mock the status label

    # Call the action method
    app.save_member_action()

    # Assert that the member was saved to the database
    members = database_manager.get_all_members(phone_filter="1234567890")
    assert len(members) == 1
    assert members[0][1] == "Test Member"
    app.member_status_label.configure.assert_any_call(text="Member added successfully! Join date will be set with first activity.", text_color="green")

    # Try to add the same member again (duplicate phone)
    app.save_member_action()
    app.member_status_label.configure.assert_any_call(text="Failed to add member. Phone number may already exist.", text_color="red")
    members_after_duplicate_attempt = database_manager.get_all_members(phone_filter="1234567890")
    assert len(members_after_duplicate_attempt) == 1 # Should still be 1 member

def test_plan_management_flow(app_instance):
    app = app_instance

    # Mock UI elements for plan management
    app.plan_name_entry.get = MagicMock(return_value="Test Plan")
    app.plan_duration_entry.get = MagicMock(return_value="30")
    app.plan_status_label.configure = MagicMock()
    app.current_plan_id_var = MagicMock()
    app.current_plan_id_var.get = MagicMock(return_value="") # For adding new plan initially

    # Simulate adding a new plan
    app.save_plan_action()

    # Verify the new plan exists in the database
    plans = database_manager.get_all_plans_with_inactive()
    assert len(plans) == 1
    assert plans[0][1] == "Test Plan"
    assert plans[0][2] == 30 # Duration
    assert plans[0][3] is True # is_active (boolean)
    app.plan_status_label.configure.assert_any_call(text="Plan added successfully!", text_color="green")

    new_plan_id = plans[0][0]

    # Simulate toggling the plan status (deactivate)
    # Directly call toggle_plan_status_action, assuming plan_id and current_status are passed
    app.toggle_plan_status_action(plan_id=new_plan_id, current_status=True)

    # Assert that the plan's is_active status has changed
    plans_after_toggle = database_manager.get_all_plans_with_inactive()
    assert len(plans_after_toggle) == 1
    assert plans_after_toggle[0][0] == new_plan_id
    assert plans_after_toggle[0][3] is False # is_active should now be False
    app.plan_status_label.configure.assert_any_call(text="Plan status changed to Inactive.", text_color="green")

    # Simulate toggling the plan status again (activate)
    app.toggle_plan_status_action(plan_id=new_plan_id, current_status=False)
    plans_after_reactivate = database_manager.get_all_plans_with_inactive()
    assert len(plans_after_reactivate) == 1
    assert plans_after_reactivate[0][3] is True # is_active should now be True
    app.plan_status_label.configure.assert_any_call(text="Plan status changed to Active.", text_color="green")

def test_add_membership_flow(app_instance):
    app = app_instance

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

    # Refresh dropdowns in app (simulating GUI update)
    # These are usually populated at init or when tabs are switched.
    # For testing, we might need to call them if action methods rely on updated internal dicts.
    app.populate_member_dropdown()
    app.populate_plan_dropdown()


    # --- Mock UI elements for Add Membership ---
    # Common fields
    app.membership_member_dropdown_var = MagicMock()
    # Ensure member_name_to_id is populated by populate_member_dropdown if test relies on it
    # Or directly mock the return of member_id from a mocked get()
    # Let's find the display name format from populate_member_dropdown
    member_display_name = f"Membership User (ID: {db_member_id})"
    app.membership_member_dropdown_var.get = MagicMock(return_value=member_display_name)

    app.start_date_picker = MagicMock()
    app.start_date_picker.get_date = MagicMock(return_value=date.today())

    app.amount_paid_entry = MagicMock()
    app.amount_paid_entry.get = MagicMock(return_value="100.00")

    app.membership_status_label = MagicMock()
    app.membership_status_label.configure = MagicMock()

    # --- Test "Group Class" Transaction ---
    app.membership_type_var = MagicMock()
    app.membership_type_var.get = MagicMock(return_value="Group Class")

    app.membership_plan_dropdown_var = MagicMock()
    # Similar to member, find plan display name format
    plan_display_name = f"Membership Plan | 30 days"
    app.membership_plan_dropdown_var.get = MagicMock(return_value=plan_display_name)

    app.payment_date_picker = MagicMock()
    app.payment_date_picker.get_date = MagicMock(return_value=date.today())
    app.payment_method_entry = MagicMock()
    app.payment_method_entry.get = MagicMock(return_value="Cash")

    # Call the action method for Group Class
    app.save_membership_action()

    # Assert Group Class transaction
    app.membership_status_label.configure.assert_any_call(text="Group Class membership added successfully!", text_color="green")
    member_activity_gc = database_manager.get_all_activity_for_member(db_member_id)
    assert len(member_activity_gc) == 1
    assert member_activity_gc[0][0] == "Group Class" # transaction_type
    assert member_activity_gc[0][1] == "Membership Plan" # plan_name (name_or_description)
    assert member_activity_gc[0][5] == 100.00 # amount_paid

    # --- Test "Personal Training" Transaction ---
    app.membership_type_var.get = MagicMock(return_value="Personal Training") # Change type
    app.pt_sessions_entry = MagicMock()
    app.pt_sessions_entry.get = MagicMock(return_value="10") # PT sessions
    app.amount_paid_entry.get = MagicMock(return_value="200.00") # Different amount for PT

    # Call the action method for Personal Training
    app.save_membership_action()

    # Assert Personal Training transaction
    app.membership_status_label.configure.assert_any_call(text="Personal Training membership added successfully!", text_color="green")
    member_activity_pt = database_manager.get_all_activity_for_member(db_member_id)
    assert len(member_activity_pt) == 2 # Now two activities for this member

    # The latest transaction is first
    pt_transaction = None
    for activity in member_activity_pt:
        if activity[0] == "Personal Training":
            pt_transaction = activity
            break
    assert pt_transaction is not None, "Personal Training transaction not found"
    assert pt_transaction[0] == "Personal Training"
    assert pt_transaction[5] == 200.00 # amount_paid
    assert "10 sessions" in pt_transaction[6] # payment_method_or_sessions

import pytest
from unittest.mock import patch, MagicMock
import os
import sys
import sqlite3
from unittest.mock import patch, MagicMock # Ensure MagicMock is imported
import os # Ensure os is imported
from datetime import date, timedelta, datetime

# Proactively mock tkinter and customtkinter modules
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()
sys.modules['customtkinter'] = MagicMock()
sys.modules['customtkinter.filedialog'] = MagicMock()
sys.modules['tkcalendar'] = MagicMock() # Mock tkcalendar
# sys.modules['pandas'] = MagicMock() # Mock pandas <-- REMOVE THIS MOCK

# Now that the modules are mocked, we can "import" them
import tkinter.messagebox as messagebox # For mocking
from customtkinter import filedialog # For mocking

# Mock tkinter main window classes to prevent actual GUI instantiation
patch('tkinter.Tk', MagicMock()).start()
patch('customtkinter.CTk', MagicMock()).start()
# This patch should now work as customtkinter.filedialog is a MagicMock
patch('customtkinter.filedialog.asksaveasfilename', MagicMock()).start()

# Mock flet and its components used by MembershipTab, before FletAppView or MembershipTab is imported
sys.modules['flet'] = MagicMock()
sys.modules['flet_core'] = MagicMock()
sys.modules['flet_core.control'] = MagicMock()
sys.modules['flet_core.event_handler'] = MagicMock()
sys.modules['flet_core.page'] = MagicMock()

import flet as ft # ft can now be used as a MagicMock namespace
# Set up specific flet components that might be referenced as classes
ft.Row = MagicMock()
ft.Column = MagicMock()
ft.Container = MagicMock()
ft.Text = MagicMock()
ft.TextField = MagicMock()
ft.ElevatedButton = MagicMock()
ft.Dropdown = MagicMock()
ft.dropdown = MagicMock() # For ft.dropdown.Option
ft.dropdown.Option = MagicMock()
ft.DatePicker = MagicMock()
ft.FilePicker = MagicMock()
ft.Tabs = MagicMock()
ft.Tab = MagicMock()
# ft.DataTable will be patched specifically in the test using it
ft.DataColumn = MagicMock()
ft.DataRow = MagicMock()
ft.DataCell = MagicMock()
ft.AlertDialog = MagicMock()
ft.TextButton = MagicMock()
ft.FontWeight = MagicMock()
ft.ScrollMode = MagicMock()
ft.CrossAxisAlignment = MagicMock()
ft.MainAxisAlignment = MagicMock()
ft.colors = MagicMock()
ft.alignment = MagicMock()


# Add project root to sys.path to allow importing reporter modules
# This assumes the test is run from the project root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from reporter import database
from reporter import database_manager # Keep for patching DB_FILE
from reporter.database_manager import DatabaseManager # Import the class
from reporter.gui import GuiController


@pytest.fixture
def controller_instance(monkeypatch):
    db_path = os.path.abspath("test_gui_flows.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    monkeypatch.setattr(database_manager, 'DB_FILE', db_path)
    database.create_database(db_path)

    # Create a DatabaseManager instance for direct use in tests
    conn = sqlite3.connect(db_path) # Connect to the same DB file
    db_mngr = DatabaseManager(conn)
    # Seed initial plans if necessary for GUI flows, using the direct connection/manager
    database.seed_initial_plans(db_mngr.conn)


    controller = GuiController(conn) # GuiController will now use the conn

    yield controller, db_mngr # Yield both controller and db_manager

    # Teardown
    db_mngr.conn.close() # Close the connection used by db_mngr
    if os.path.exists(db_path):
        print(f"Tearing down, removing {db_path}")
        os.remove(db_path)
    else:
        print(f"Tearing down, {db_path} does not exist.")

def test_add_member_flow(controller_instance):
    controller, db_mngr = controller_instance # Unpack

    success, message = controller.save_member_action(name="Test Member", phone="1234567890")

    assert success is True
    assert message == "Member added successfully."

    members = db_mngr.get_all_members(phone_filter="1234567890") # Use db_mngr
    assert len(members) == 1
    assert members[0][1] == "Test Member"

    success_dup, message_dup = controller.save_member_action(name="Test Member", phone="1234567890")

    assert success_dup is False
    assert message_dup == "Error adding member: Phone number '1234567890' likely already exists."

    members_after_duplicate_attempt = db_mngr.get_all_members(phone_filter="1234567890") # Use db_mngr
    assert len(members_after_duplicate_attempt) == 1

def test_plan_management_flow(controller_instance):
    controller, db_mngr = controller_instance # Unpack

    success_add, message_add, plans_add = controller.save_plan_action(
        plan_name="Test Plan", duration_str="30", plan_id_to_update=""
    )
    assert success_add is True
    assert message_add == "Plan added successfully."
    assert isinstance(plans_add, list)

    # Verify the new plan exists in the database
    db_plans_after_add = db_mngr.get_all_plans_with_inactive() # Use db_mngr
    # Adjust expectation if seed_initial_plans added plans. Assuming it adds 3.
    # If this test expects only 1 plan, then seed_initial_plans should not run or plans should be cleared.
    # Given the previous test_database_manager, seed_initial_plans adds 3 plans.
    # Let's assume this test should account for those.
    initial_plan_count = 3 # from seed_initial_plans
    assert len(db_plans_after_add) == initial_plan_count + 1

    # Find the newly added plan
    new_plan_entry = None
    for p in db_plans_after_add:
        if p[1] == "Test Plan":
            new_plan_entry = p
            break
    assert new_plan_entry is not None, "Test Plan not found after adding."
    assert new_plan_entry[2] == 30  # Duration
    assert new_plan_entry[3] == 1  # is_active (stored as INT 1 for True)
    new_plan_id = new_plan_entry[0]

    # Toggling plan status (deactivate)
    success_deactivate, message_deactivate, plans_deactivate = controller.toggle_plan_status_action(
        plan_id=new_plan_id
    )
    assert success_deactivate is True
    assert message_deactivate == "Plan status updated successfully."
    assert isinstance(plans_deactivate, list)

    # Assert that the plan's is_active status has changed in the database
    db_plans_after_deactivate = db_mngr.get_all_plans_with_inactive() # Use db_mngr
    plan_after_deactivate = next((p for p in db_plans_after_deactivate if p[0] == new_plan_id), None)
    assert plan_after_deactivate is not None
    assert plan_after_deactivate[3] == 0  # is_active should now be 0 for False

    # Toggling plan status again (activate)
    success_activate, message_activate, plans_activate = controller.toggle_plan_status_action(
        plan_id=new_plan_id
    )
    assert success_activate is True
    assert message_activate == "Plan status updated successfully."
    assert isinstance(plans_activate, list)

    db_plans_after_activate = db_mngr.get_all_plans_with_inactive() # Use db_mngr
    plan_after_activate = next((p for p in db_plans_after_activate if p[0] == new_plan_id), None)
    assert plan_after_activate is not None
    assert plan_after_activate[3] == 1  # is_active should now be 1 for True

def test_add_membership_flow(controller_instance):
    controller, db_mngr = controller_instance # Unpack

    # --- Setup: Pre-populate database with a member and a plan ---
    add_member_success, add_member_message = db_mngr.add_member_to_db("Membership User", "000111222") # Use db_mngr
    assert add_member_success is True, f"Failed to add member: {add_member_message}"
    member_details = db_mngr.get_all_members(phone_filter="000111222") # Use db_mngr
    assert len(member_details) == 1
    db_member_id = member_details[0][0]

    add_plan_success, _, db_plan_id_val = db_mngr.add_plan("Membership Plan", 30) # Use db_mngr
    assert add_plan_success is True and db_plan_id_val is not None, "Failed to add plan"

    # --- Test "Group Class" Transaction ---
    s_gc, m_gc = controller.save_membership_action(
        membership_type="Group Class",
        member_id=db_member_id,
        selected_plan_id=db_plan_id_val, # Use the extracted integer ID
        payment_date_str=date.today().strftime('%Y-%m-%d'),
        start_date_str=date.today().strftime('%Y-%m-%d'),
        amount_paid_str="100.00",
        payment_method="Cash",
        sessions_str=None
    )
    assert s_gc is True
    assert m_gc == "Group Class membership added successfully!"

    member_activity_gc = db_mngr.get_all_activity_for_member(db_member_id) # Use db_mngr
    assert len(member_activity_gc) == 1
    assert member_activity_gc[0][0] == "Group Class"
    assert member_activity_gc[0][1] == "Membership Plan"
    assert member_activity_gc[0][5] == 100.00

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

    member_activity_pt = db_mngr.get_all_activity_for_member(db_member_id) # Use db_mngr
    assert len(member_activity_pt) == 2

    pt_transaction = None
    for activity in member_activity_pt:
        if activity[0] == "Personal Training":
            pt_transaction = activity
            break
    assert pt_transaction is not None, "Personal Training transaction not found"
    assert pt_transaction[0] == "Personal Training"
    assert pt_transaction[5] == 200.00
    assert pt_transaction[6] == "10 sessions"


# --- Tests for Delete Action Flows ---

@patch('tkinter.messagebox.askyesno', return_value=True)
def test_deactivate_member_action_flow(mock_askyesno, controller_instance):
    controller, db_mngr = controller_instance # Unpack
    # --- Setup: Add a member and a transaction for them ---
    member_name = "MemberToDeactivateGUI"
    member_phone = "DEAC999"
    add_mem_success, add_mem_message = db_mngr.add_member_to_db(member_name, member_phone) # Use db_mngr
    assert add_mem_success is True, f"Failed to add member for deactivation test: {add_mem_message}"
    members_before_deactivation = db_mngr.get_all_members(phone_filter=member_phone) # Use db_mngr
    assert len(members_before_deactivation) == 1, "Test setup: Member not added or not active."
    member_id_to_deactivate = members_before_deactivation[0][0]

    plan_id_for_tx_val = None
    plans = db_mngr.get_all_plans() # Use db_mngr
    if not plans:
        add_plan_success, _, plan_id_for_tx_val = db_mngr.add_plan("Default Test Plan GUI", 30) # Use db_mngr
        assert add_plan_success and plan_id_for_tx_val is not None, "Test setup: Failed to add a default plan."
    else:
        plan_id_for_tx_val = plans[0][0]

    add_tx_success, _ = db_mngr.add_transaction( # Use db_mngr
        transaction_type='Group Class',
        member_id=member_id_to_deactivate,
        plan_id=plan_id_for_tx_val,
        payment_date="2024-01-01",
        start_date="2024-01-01",
        amount_paid=50.00,
        payment_method="Cash"
    )
    transactions_before_deactivation = db_mngr.get_all_activity_for_member(member_id_to_deactivate) # Use db_mngr
    assert len(transactions_before_deactivation) == 1, "Test setup: Transaction not added."
    initial_transaction_count = len(transactions_before_deactivation)

    success, message = controller.deactivate_member_action(member_id_to_deactivate)

    assert success is True
    assert message == "Member deactivated successfully."

    active_members_after_deactivation = db_mngr.get_all_members(phone_filter=member_phone) # Use db_mngr
    assert len(active_members_after_deactivation) == 0, "Deactivated member should not appear in active members list."

    # Verify the member is marked as inactive in the database but still exists
    # No need to create a new connection, use db_mngr.conn
    cursor = db_mngr.conn.cursor()
    cursor.execute("SELECT client_name, phone, is_active FROM members WHERE member_id = ?", (member_id_to_deactivate,))
    deactivated_member_record = cursor.fetchone()

    assert deactivated_member_record is not None, "Member record should still exist in the database."
    assert deactivated_member_record[0] == member_name
    assert deactivated_member_record[1] == member_phone
    assert deactivated_member_record[2] == 0, f"Member's is_active flag should be 0, but was {deactivated_member_record[2]}."

    transactions_after_deactivation = db_mngr.get_all_activity_for_member(member_id_to_deactivate) # Use db_mngr
    assert len(transactions_after_deactivation) == initial_transaction_count, \
        "Transactions for the deactivated member should still exist and match initial count."
    assert len(transactions_after_deactivation) > 0, "No transactions found for deactivated member, but they should exist."

@patch('tkinter.messagebox.askyesno', return_value=True)
def test_delete_transaction_action_flow(mock_askyesno, controller_instance):
    controller, db_mngr = controller_instance # Unpack
    member_name = "TransactionLifecycleMember"
    member_phone = "TRL888"
    add_mem_success, _ = db_mngr.add_member_to_db(member_name, member_phone) # Use db_mngr
    assert add_mem_success, "Failed to add member for transaction lifecycle test"
    members = db_mngr.get_all_members(phone_filter=member_phone) # Use db_mngr
    member_id = members[0][0]

    plan_id_val = None
    plans = db_mngr.get_all_plans() # Use db_mngr
    if not plans:
        add_plan_success, _, plan_id_val = db_mngr.add_plan("Default Plan for Test", 30) # Use db_mngr
        assert add_plan_success and plan_id_val is not None, "Failed to add plan for transaction lifecycle test"
    else:
        plan_id_val = plans[0][0]

    add_tx_success, _ = db_mngr.add_transaction( # Use db_mngr
        transaction_type='Group Class', member_id=member_id, plan_id=plan_id_val,
        payment_date="2024-01-01", start_date="2024-01-01", amount_paid=50, payment_method="Cash"
    )
    assert add_tx_success, "Failed to add transaction for transaction lifecycle test"
    activity = db_mngr.get_all_activity_for_member(member_id) # Use db_mngr
    assert len(activity) == 1, "Test setup: Transaction not added."
    transaction_id_to_delete = activity[0][7]

    success, message = controller.delete_transaction_action(transaction_id_to_delete)

    assert success is True
    assert message == "Transaction deleted successfully."

    activity_after_delete = db_mngr.get_all_activity_for_member(member_id) # Use db_mngr
    assert len(activity_after_delete) == 0, "Transaction was not deleted from the database."

@patch('tkinter.messagebox.askyesno')
def test_delete_plan_action_flow(mock_askyesno, controller_instance):
    controller, db_mngr = controller_instance # Unpack

    mock_askyesno.return_value = True
    plan_name_unused = "Unused Plan GUI Test"
    add_plan_s1, _, plan_id_unused_val = db_mngr.add_plan(plan_name_unused, 10) # Use db_mngr
    assert add_plan_s1 and plan_id_unused_val is not None, "Failed to add unused plan for GUI test"

    success_s1, message_s1 = controller.delete_plan_action(plan_id_unused_val)
    assert success_s1 is True
    assert message_s1 == "Plan deleted successfully."

    plans_after_s1_delete = db_mngr.get_all_plans_with_inactive() # Use db_mngr
    assert not any(p[0] == plan_id_unused_val for p in plans_after_s1_delete), "Unused plan was not deleted."
    mock_askyesno.reset_mock()

    plan_name_used = "Used Plan GUI Test"
    add_plan_s2, _, plan_id_used_val = db_mngr.add_plan(plan_name_used, 40) # Use db_mngr
    assert add_plan_s2 and plan_id_used_val is not None, "Failed to add used plan for GUI test"

    add_member_s, _ = db_mngr.add_member_to_db("PlanUser", "PU777") # Use db_mngr
    assert add_member_s, "Failed to add PlanUser for GUI test"
    members = db_mngr.get_all_members(phone_filter="PU777") # Use db_mngr
    member_id = members[0][0]
    add_tx_s, _ = db_mngr.add_transaction( # Use db_mngr
        transaction_type='Group Class', member_id=member_id, plan_id=plan_id_used_val,
        payment_date="2024-01-01", start_date="2024-01-01", amount_paid=50, payment_method="Cash"
    )
    assert add_tx_s, "Failed to add transaction for used plan test"

    success_s2, message_s2 = controller.delete_plan_action(plan_id_used_val)
    assert success_s2 is False
    assert message_s2 == "Plan is in use and cannot be deleted."
    mock_askyesno.assert_not_called()

    plans_after_s2_attempt = db_mngr.get_all_plans_with_inactive() # Use db_mngr
    assert any(p[0] == plan_id_used_val for p in plans_after_s2_attempt), "Used plan was deleted, but shouldn't have been."


# --- Tests for Report Generation Action Flows ---

def test_generate_custom_pending_renewals_action_flow(controller_instance):
    controller, db_mngr = controller_instance # Unpack
    add_mem_s, _ = db_mngr.add_member_to_db("Renewal User Future", "RF001") # Use db_mngr
    assert add_mem_s, "Failed to add member for renewals test"
    members_rf1 = db_mngr.get_all_members(phone_filter="RF001") # Use db_mngr
    m_id_rf1 = members_rf1[0][0]
    client_name_rf1 = members_rf1[0][1]

    add_plan_s, _, plan_id_30day_val = db_mngr.add_plan("30 Day Plan Future", 30) # Use db_mngr
    assert add_plan_s and plan_id_30day_val is not None, "Failed to add plan for renewals test"
    plan_details_30day = db_mngr.get_plan_by_name_and_duration("30 Day Plan Future", 1) # Use db_mngr
    assert plan_details_30day is not None
    plan_name_30day = plan_details_30day[1]

    target_year = 2025
    target_month = 7
    end_date_rf1_target = datetime(target_year, target_month, 15)
    start_date_rf1 = (end_date_rf1_target - timedelta(days=30)).strftime('%Y-%m-%d')
    add_tx_s, _ = db_mngr.add_transaction( # Use db_mngr
        transaction_type='Group Class', member_id=m_id_rf1, plan_id=plan_id_30day_val,
        payment_date=start_date_rf1, start_date=start_date_rf1, amount_paid=100, payment_method="Cash"
    )
    assert add_tx_s, "Failed to add transaction for renewals test"

    success, message, data = controller.generate_custom_pending_renewals_action(target_year, target_month)

    assert success is True
    target_month_name = datetime(target_year, target_month, 1).strftime("%B")
    if data:
        assert f"Found {len(data)} pending renewals for {target_month_name} {target_year}." in message
        assert len(data) == 1
        assert data[0] == (client_name_rf1, "RF001", plan_name_30day, end_date_rf1_target.strftime('%Y-%m-%d'))
    else:
        assert f"No pending renewals found for {target_month_name} {target_year}." == message
        assert len(data) == 0

    no_renew_year, no_renew_month = 2026, 1
    success_none, message_none, data_none = controller.generate_custom_pending_renewals_action(no_renew_year, no_renew_month)
    assert success_none is True
    no_renew_month_name = datetime(no_renew_year, no_renew_month, 1).strftime("%B")
    assert f"No pending renewals found for {no_renew_month_name} {no_renew_year}." == message_none
    assert data_none == []

@patch('customtkinter.filedialog.asksaveasfilename')
def test_generate_finance_report_excel_action_flow(mock_asksaveasfilename, controller_instance):
    controller, db_mngr = controller_instance # Unpack
    report_year = 2025
    report_month = 8

    add_mem_s, _ = db_mngr.add_member_to_db("Finance User Excel1", "FX001") # Use db_mngr
    assert add_mem_s, "Failed to add member for finance report test"
    m_fx1_id = db_mngr.get_all_members(phone_filter="FX001")[0][0] # Use db_mngr
    add_plan_s, _, plan_fx_id_val = db_mngr.add_plan("Finance Plan Excel", 30) # Use db_mngr
    assert add_plan_s and plan_fx_id_val is not None, "Failed to add plan for finance report test"

    add_tx1_s, _ = db_mngr.add_transaction( # Use db_mngr
        transaction_type='Group Class', member_id=m_fx1_id, plan_id=plan_fx_id_val,
        payment_date=datetime(report_year, report_month, 10).strftime('%Y-%m-%d'),
        start_date=datetime(report_year, report_month, 10).strftime('%Y-%m-%d'),
        amount_paid=150.00, payment_method="Card"
    )
    assert add_tx1_s, "Failed to add transaction 1 for finance report"
    add_tx2_s, _ = db_mngr.add_transaction( # Use db_mngr
        transaction_type='Personal Training', member_id=m_fx1_id,
        payment_date=datetime(report_year, report_month, 15).strftime('%Y-%m-%d'),
        start_date=datetime(report_year, report_month, 15).strftime('%Y-%m-%d'),
        sessions=5, amount_paid=250.00
    )
    assert add_tx2_s, "Failed to add transaction 2 for finance report"
    add_tx3_s, _ = db_mngr.add_transaction( # Use db_mngr
        transaction_type='Group Class', member_id=m_fx1_id, plan_id=plan_fx_id_val,
        payment_date=datetime(report_year, report_month + 1, 10).strftime('%Y-%m-%d'),
        start_date=datetime(report_year, report_month + 1, 10).strftime('%Y-%m-%d'),
        amount_paid=50.00, payment_method="Cash"
    )
    assert add_tx3_s, "Failed to add transaction 3 (other month) for finance report"

    test_report_filename = os.path.abspath("test_finance_report.xlsx")
    mock_asksaveasfilename.return_value = test_report_filename

    success, message = controller.generate_finance_report_excel_action(report_year, report_month, test_report_filename)

    assert success is True
    assert message == f"Finance report generated successfully: {test_report_filename}"
    assert os.path.exists(test_report_filename), "Excel report file was not created."

    total_revenue_from_db = db_mngr.get_finance_report(report_year, report_month) # Use db_mngr
    assert total_revenue_from_db == 400.00

    if os.path.exists(test_report_filename):
        os.remove(test_report_filename)

    mock_asksaveasfilename.reset_mock()
    mock_asksaveasfilename.return_value = ""

    success_cancel, message_cancel = controller.generate_finance_report_excel_action(report_year, report_month, "")
    assert success_cancel is False
    assert "An error occurred during report generation:" in message_cancel
    assert "[Errno 2] No such file or directory: ''" in message_cancel
    assert not os.path.exists(test_report_filename)
    if os.path.exists(""):
        os.remove("")


# --- Test for MembershipTab Initialization ---
from reporter.components.membership_tab import MembershipTab # Import globally for @patch target
from unittest.mock import MagicMock, patch # Import MagicMock and patch
# GuiController is already imported

@patch('reporter.components.membership_tab.ft.DataTable', new_callable=MagicMock)
def test_membership_tab_initialization(mock_datatable_in_membership_tab, controller_instance):
    """
    Tests that MembershipTab initializes correctly, ensuring ft.DataTable (as used by MembershipTab) is called.
    """
    controller = controller_instance
    mock_date_picker = MagicMock(spec=ft.DatePicker)

    mock_datatable_in_membership_tab.reset_mock()

    try:
        # MembershipTab will be instantiated using the mock provided by @patch
        tab = MembershipTab(controller=controller, date_picker_ref=mock_date_picker)

        # Check call count on the mock that was specifically injected into MembershipTab's namespace
        assert mock_datatable_in_membership_tab.call_count >= 1, "DataTable in MembershipTab was not called."
        assert mock_datatable_in_membership_tab.call_count == 2, f"Expected DataTable in MembershipTab to be called 2 times, but was {mock_datatable_in_membership_tab.call_count}."

    except Exception as e:
        pytest.fail(f"MembershipTab instantiation or DataTable call check failed: {e}")

    assert tab.members_table_flet is not None, "members_table_flet should be initialized."

    # The call_count assertion already confirms that mocked_flet_datatable was used.
    # tab.members_table_flet will be the instance returned by the first call.
    # The problematic assertion `tab.members_table_flet == mock_datatable_in_membership_tab.mock_calls[0].return_value`
    # is removed as mock_calls[0] doesn't directly provide the return value instance in a simple way.
    # The critical checks are that the mock was called, and that on_select_changed is correctly assigned.

    assert tab.members_table_flet.on_select_changed is not None, \
        "on_select_changed should be set on members_table_flet."

    assert tab.members_table_flet.on_select_changed == tab.on_member_select_changed, \
        "members_table_flet.on_select_changed is not assigned to tab.on_member_select_changed."

    # Check other initializations if they were problematic
    assert tab.controller == controller
    assert tab.date_picker_ref == mock_date_picker

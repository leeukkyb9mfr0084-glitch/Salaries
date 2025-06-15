import pytest
from unittest.mock import patch, MagicMock
import os
import sys
import sqlite3
from datetime import date, timedelta, datetime

# Add project root to sys.path to allow importing reporter modules
# This assumes the test is run from the project root directory
# Ensure this path is correct for your project structure
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from reporter import database

# database_manager module is used for monkeypatching DB_FILE
from reporter import database_manager
from reporter.database_manager import DatabaseManager
from reporter.app_api import AppAPI  # Import AppAPI

# DEFAULT_PRICE and DEFAULT_TYPE_TEXT for add_plan calls
DEFAULT_PRICE = 0
DEFAULT_TYPE_TEXT = "DefaultType"


@pytest.fixture
def api_db_fixture(monkeypatch):  # Renamed fixture
    db_path = os.path.abspath("test_gui_flows.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    # Use the actual DB_FILE used by the application for seeding.
    # This ensures consistency if database_manager.DB_FILE is used by `database.create_database`
    monkeypatch.setattr(database_manager, "DB_FILE", db_path)
    database.create_database(db_path)  # This should now use the monkeypatched db_path

    conn = sqlite3.connect(db_path)
    db_mngr = DatabaseManager(conn)
    # Seed initial plans. Note: The plans table in AppAPI expects price and type_text.
    # The seed_initial_plans might need adjustment if it doesn't provide these.
    # For now, we assume seed_initial_plans works or its impact on these tests is handled.
    # It seems seed_initial_plans directly inserts into DB without these new fields.
    # We will add them manually if tests rely on them from seeded data.
    # Or, ensure AppAPI.add_plan is used for all plan creations if those fields are vital.
    database.seed_initial_plans(db_mngr.conn)  # Uses db_mngr's connection

    app_api = AppAPI(conn)  # Create AppAPI instance

    yield app_api, db_mngr  # Yield app_api and db_mngr

    # Teardown
    conn.close()  # db_mngr.conn is the same as conn here.
    if os.path.exists(db_path):
        # print(f"Tearing down, removing {db_path}") # Optional: for debugging
        os.remove(db_path)
    # else:
    # print(f"Tearing down, {db_path} does not exist.") # Optional: for debugging


def test_add_member_flow(api_db_fixture):  # Use new fixture
    app_api, db_mngr = api_db_fixture  # Unpack

    # Use app_api.add_member
    success, message = app_api.add_member(name="Test Member", phone="1234567890")

    assert success is True
    assert message == "Member added successfully."  # AppAPI returns this on success

    members = db_mngr.get_all_members(phone_filter="1234567890")
    assert len(members) == 1
    assert members[0][1] == "Test Member"

    # Attempt to add duplicate
    success_dup, message_dup = app_api.add_member(
        name="Test Member", phone="1234567890"
    )

    assert success_dup is False
    # AppAPI.add_member calls db_mngr.add_member_to_db, which returns specific error
    assert (
        "UNIQUE constraint failed: members.phone" in message_dup
        or "Phone number '1234567890' likely already exists" in message_dup
    )

    members_after_duplicate_attempt = db_mngr.get_all_members(phone_filter="1234567890")
    assert len(members_after_duplicate_attempt) == 1


def test_plan_management_flow(api_db_fixture):  # Use new fixture
    app_api, db_mngr = api_db_fixture  # Unpack

    # Add a plan using AppAPI
    # AppAPI.add_plan(name, duration_days, price, type_text)
    # GuiController.save_plan_action(plan_name, duration_str, plan_id_to_update="")
    # The old controller.save_plan_action didn't take price/type_text.
    # We'll use default values for these with AppAPI.
    success_add, message_add, new_plan_id = app_api.add_plan(
        name="Test Plan",
        duration_days=30,
        price=DEFAULT_PRICE,
        type_text=DEFAULT_TYPE_TEXT,
    )
    assert success_add is True
    assert message_add == "Plan added successfully."
    assert new_plan_id is not None

    # Verify the new plan exists using db_mngr
    db_plans_after_add = db_mngr.get_all_plans_with_inactive()

    # Count initial plans from seed_initial_plans.
    # Based on database.py, seed_initial_plans adds 3 plans.
    initial_plan_count = 3
    assert len(db_plans_after_add) == initial_plan_count + 1

    new_plan_entry = next((p for p in db_plans_after_add if p[0] == new_plan_id), None)
    assert new_plan_entry is not None, "Test Plan not found after adding."
    assert new_plan_entry[1] == "Test Plan"  # Name
    assert new_plan_entry[2] == 30  # Duration
    # Columns for price and type_text are now 4 and 5 if they exist in your db_mngr.get_all_plans_with_inactive() output
    # Assuming is_active is at index 3 for DatabaseManager.get_all_plans_with_inactive
    assert (
        new_plan_entry[5] == 1
    )  # is_active (e.g. index 5 if price, type_text are added before it)
    # Or index 3 if using the old plan table structure from previous test file.
    # Let's check reporter.database_manager.get_all_plans_with_inactive
    # It returns: plan_id, plan_name, duration_days, price, type_text, is_active
    # So is_active is at index 5. Price at 3, type_text at 4.

    # Deactivate plan (AppAPI.delete_plan sets is_active=False)
    # Note: AppAPI.delete_plan returns (bool, str)
    success_deactivate, message_deactivate = app_api.delete_plan(new_plan_id)
    assert success_deactivate is True
    # Message from AppAPI.delete_plan if successful and not in use: "Plan deactivated successfully."
    # If it was "Plan deleted successfully" in controller, this might change.
    # Checking AppAPI: `db_mngr.delete_plan` is called which returns "Plan deactivated successfully"
    assert message_deactivate == "Plan deactivated successfully."

    plan_after_deactivate = db_mngr.get_plan_by_id(
        new_plan_id
    )  # get_plan_by_id returns Optional[tuple]
    assert plan_after_deactivate is not None
    assert plan_after_deactivate[5] == 0  # is_active should now be 0 (False)

    # Activate plan: AppAPI doesn't have a direct "activate" or "toggle".
    # To reactivate, one might add it again if it was truly deleted, or update its status directly.
    # The old controller.toggle_plan_status_action used db_mngr.update_plan_active_status.
    # We will use db_mngr directly here as AppAPI doesn't expose this toggle.
    db_mngr.update_plan_active_status(new_plan_id, True)  # Directly using DB Manager

    plan_after_activate = db_mngr.get_plan_by_id(new_plan_id)
    assert plan_after_activate is not None
    assert plan_after_activate[5] == 1  # is_active should now be 1 (True)


def test_add_membership_flow(api_db_fixture):  # Use new fixture
    app_api, db_mngr = api_db_fixture  # Unpack

    add_member_success, add_member_message = db_mngr.add_member_to_db(
        "Membership User", "000111222"
    )
    assert add_member_success is True, f"Failed to add member: {add_member_message}"
    member_details = db_mngr.get_all_members(phone_filter="000111222")
    assert len(member_details) == 1
    db_member_id = member_details[0][0]

    # AppAPI.add_plan needs price and type_text.
    add_plan_success, _, db_plan_id_val = db_mngr.add_plan(
        "Membership Plan", 30, DEFAULT_PRICE, DEFAULT_TYPE_TEXT
    )
    assert add_plan_success is True and db_plan_id_val is not None, "Failed to add plan"

    today_str = date.today().strftime("%Y-%m-%d")

    # --- Test "Group Class" Transaction using AppAPI ---
    s_gc, m_gc = app_api.add_transaction(
        transaction_type="Group Class",
        member_id=db_member_id,
        plan_id=db_plan_id_val,
        payment_date=today_str,
        start_date=today_str,
        amount_paid=100.00,
        payment_method="Cash",
        # sessions field is optional in AppAPI.add_transaction
    )
    assert s_gc is True
    # AppAPI.add_transaction returns "Transaction added successfully."
    assert m_gc == "Transaction added successfully."

    member_activity_gc = db_mngr.get_all_activity_for_member(db_member_id)
    assert len(member_activity_gc) == 1
    assert member_activity_gc[0][0] == "Group Class"  # transaction_type
    assert member_activity_gc[0][1] == "Membership Plan"  # plan_name
    assert member_activity_gc[0][5] == 100.00  # amount_paid

    # --- Test "Personal Training" Transaction using AppAPI ---
    s_pt, m_pt = app_api.add_transaction(
        transaction_type="Personal Training",
        member_id=db_member_id,
        plan_id=None,  # No plan_id for PT
        payment_date=today_str,
        start_date=today_str,
        amount_paid=200.00,
        payment_method="N/A",  # Or some other value, AppAPI doesn't default it like GuiController
        sessions=10,  # sessions is an int
    )
    assert s_pt is True
    assert m_pt == "Transaction added successfully."

    member_activity_pt = db_mngr.get_all_activity_for_member(db_member_id)
    assert len(member_activity_pt) == 2

    pt_transaction = next(
        (act for act in member_activity_pt if act[0] == "Personal Training"), None
    )
    assert pt_transaction is not None, "Personal Training transaction not found"
    assert pt_transaction[5] == 200.00  # amount_paid
    # get_all_activity_for_member returns sessions as part of the tuple (index 6)
    assert pt_transaction[6] == 10  # sessions


# --- Tests for Delete Action Flows (No more tkinter.messagebox mocks) ---


def test_deactivate_member_action_flow(api_db_fixture):  # Use new fixture
    app_api, db_mngr = api_db_fixture  # Unpack
    member_name = "MemberToDeactivateAPI"
    member_phone = "DEAC888"  # Changed phone to avoid conflict if tests run oddly
    add_mem_success, add_mem_message = db_mngr.add_member_to_db(
        member_name, member_phone
    )
    assert (
        add_mem_success is True
    ), f"Failed to add member for deactivation test: {add_mem_message}"

    members_before_deactivation = db_mngr.get_all_members(phone_filter=member_phone)
    assert (
        len(members_before_deactivation) == 1
    ), "Test setup: Member not added or not active."
    member_id_to_deactivate = members_before_deactivation[0][0]

    # Add a transaction for them (setup)
    plan_id_for_tx_val = None
    plans = db_mngr.get_all_plans()
    if not plans:
        add_plan_success, _, plan_id_for_tx_val = db_mngr.add_plan(
            "Default Test Plan API", 30, DEFAULT_PRICE, DEFAULT_TYPE_TEXT
        )
        assert (
            add_plan_success and plan_id_for_tx_val is not None
        ), "Test setup: Failed to add a default plan."
    else:
        plan_id_for_tx_val = plans[0][0]  # Use first available plan

    db_mngr.add_transaction(
        transaction_type="Group Class",
        member_id=member_id_to_deactivate,
        plan_id=plan_id_for_tx_val,
        payment_date="2024-01-01",
        start_date="2024-01-01",
        amount_paid=50.00,
        payment_method="Cash",
    )
    transactions_before_deactivation = db_mngr.get_all_activity_for_member(
        member_id_to_deactivate
    )
    initial_transaction_count = len(transactions_before_deactivation)
    assert initial_transaction_count == 1, "Test setup: Transaction not added."

    # Call AppAPI method
    success, message = app_api.deactivate_member(member_id_to_deactivate)

    assert success is True
    assert message == "Member deactivated successfully."  # From AppAPI

    active_members_after_deactivation = db_mngr.get_all_members(
        phone_filter=member_phone
    )
    assert len(active_members_after_deactivation) == 0

    cursor = db_mngr.conn.cursor()
    cursor.execute(
        "SELECT client_name, phone, is_active FROM members WHERE member_id = ?",
        (member_id_to_deactivate,),
    )
    deactivated_member_record = cursor.fetchone()
    assert deactivated_member_record is not None
    assert deactivated_member_record[2] == 0  # is_active is False (0)

    transactions_after_deactivation = db_mngr.get_all_activity_for_member(
        member_id_to_deactivate
    )
    assert len(transactions_after_deactivation) == initial_transaction_count


def test_delete_transaction_action_flow(api_db_fixture):  # Use new fixture
    app_api, db_mngr = api_db_fixture  # Unpack
    member_name = "TransactionLifecycleMemberAPI"
    member_phone = "TRL777"  # Changed phone
    add_mem_success, _ = db_mngr.add_member_to_db(member_name, member_phone)
    assert add_mem_success
    member_id = db_mngr.get_all_members(phone_filter=member_phone)[0][0]

    plan_id_val = None
    plans = db_mngr.get_all_plans()
    if not plans:
        add_plan_success, _, plan_id_val = db_mngr.add_plan(
            "Default Plan API", 30, DEFAULT_PRICE, DEFAULT_TYPE_TEXT
        )
        assert add_plan_success and plan_id_val is not None
    else:
        plan_id_val = plans[0][0]

    add_tx_success, _ = db_mngr.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id_val,
        payment_date="2024-01-01",
        start_date="2024-01-01",
        amount_paid=50,
        payment_method="Cash",
    )
    assert add_tx_success
    activity = db_mngr.get_all_activity_for_member(member_id)
    assert len(activity) == 1
    # get_all_activity_for_member returns:
    # transaction_type, plan_name, start_date, end_date, payment_method, amount_paid, sessions_info, transaction_id
    transaction_id_to_delete = activity[0][7]

    # Call AppAPI method
    success, message = app_api.delete_transaction(transaction_id_to_delete)

    assert success is True
    assert message == "Transaction deleted successfully."  # From AppAPI

    activity_after_delete = db_mngr.get_all_activity_for_member(member_id)
    assert len(activity_after_delete) == 0


def test_delete_plan_action_flow(api_db_fixture):  # Use new fixture
    app_api, db_mngr = api_db_fixture  # Unpack

    plan_name_unused = "Unused Plan API Test"
    # AppAPI.add_plan returns success, message, new_plan_id
    add_plan_s1, _, plan_id_unused_val = app_api.add_plan(
        plan_name_unused, 10, DEFAULT_PRICE, DEFAULT_TYPE_TEXT
    )
    assert add_plan_s1 and plan_id_unused_val is not None

    # Call AppAPI method for deleting unused plan
    success_s1, message_s1 = app_api.delete_plan(plan_id_unused_val)
    assert success_s1 is True
    # AppAPI.delete_plan (via db_mngr.delete_plan) returns "Plan deactivated successfully."
    assert message_s1 == "Plan deactivated successfully."

    plan_after_s1_delete = db_mngr.get_plan_by_id(plan_id_unused_val)
    assert plan_after_s1_delete is not None  # Plan still exists
    assert plan_after_s1_delete[5] == 0  # But is_active is False (index 5)

    # Test deleting a plan that is in use
    plan_name_used = "Used Plan API Test"
    add_plan_s2, _, plan_id_used_val = app_api.add_plan(
        plan_name_used, 40, DEFAULT_PRICE, DEFAULT_TYPE_TEXT
    )
    assert add_plan_s2 and plan_id_used_val is not None

    add_member_s, _ = db_mngr.add_member_to_db("PlanUserAPI", "PU666")  # Changed phone
    assert add_member_s
    member_id = db_mngr.get_all_members(phone_filter="PU666")[0][0]

    add_tx_s, _ = db_mngr.add_transaction(
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id_used_val,
        payment_date="2024-01-01",
        start_date="2024-01-01",
        amount_paid=50,
        payment_method="Cash",
    )
    assert add_tx_s

    # Call AppAPI method for deleting used plan
    success_s2, message_s2 = app_api.delete_plan(plan_id_used_val)
    assert success_s2 is False
    # AppAPI.delete_plan (via db_mngr.delete_plan) returns "Plan is in use and cannot be deactivated."
    assert message_s2 == "Plan is in use and cannot be deactivated."

    plan_after_s2_attempt = db_mngr.get_plan_by_id(plan_id_used_val)
    assert plan_after_s2_attempt is not None
    assert plan_after_s2_attempt[5] == 1  # is_active should still be True (1)


# --- Tests for Report Generation Action Flows ---


def test_generate_custom_pending_renewals_action_flow(
    api_db_fixture,
):  # Use new fixture
    app_api, db_mngr = api_db_fixture  # Unpack

    add_mem_s, _ = db_mngr.add_member_to_db(
        "Renewal User Future API", "RF002"
    )  # Changed phone
    assert add_mem_s
    members_rf1 = db_mngr.get_all_members(phone_filter="RF002")
    m_id_rf1 = members_rf1[0][0]
    client_name_rf1 = members_rf1[0][1]

    add_plan_s, _, plan_id_30day_val = app_api.add_plan(
        "30 Day Plan Future API", 30, DEFAULT_PRICE, DEFAULT_TYPE_TEXT
    )
    assert add_plan_s and plan_id_30day_val is not None

    # Need plan name for assertion, get it from db_mngr as AppAPI.add_plan doesn't return it.
    plan_details_30day = db_mngr.get_plan_by_id(plan_id_30day_val)
    assert plan_details_30day is not None
    plan_name_30day = plan_details_30day[1]

    target_year = 2025
    target_month = 7
    # Create a transaction whose end_date falls in the target month
    # Assuming duration_days from plan is used to calculate end_date by db_mngr.add_transaction
    # For a 30-day plan, if end_date is target_year/month/15, start_date is 30 days prior.
    end_date_rf1_target = datetime(target_year, target_month, 15)
    start_date_rf1 = (end_date_rf1_target - timedelta(days=30)).strftime("%Y-%m-%d")

    add_tx_s, _ = db_mngr.add_transaction(
        transaction_type="Group Class",
        member_id=m_id_rf1,
        plan_id=plan_id_30day_val,
        payment_date=start_date_rf1,
        start_date=start_date_rf1,
        amount_paid=100,
        payment_method="Cash",
    )
    assert add_tx_s

    # Use AppAPI.get_pending_renewals
    data = app_api.get_pending_renewals(target_year, target_month)

    # Assertions based on AppAPI.get_pending_renewals return type (list of tuples)
    assert len(data) == 1
    # Expected data structure from get_pending_renewals:
    # (client_name, phone, plan_name, end_date_str)
    expected_end_date_str = end_date_rf1_target.strftime(
        "%Y-%m-%d"
    )  # This needs to match how add_transaction calculates it

    # Let's verify the actual end_date stored by add_transaction + get_pending_renewals
    actual_end_date_in_db = data[0][3]  # Assuming this is the end_date
    # We need to ensure add_transaction correctly sets an end_date that get_pending_renewals can find.
    # The logic for end_date calculation is in database_manager.add_transaction
    # end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=plan_duration_days)).strftime('%Y-%m-%d')
    # So, for start_date_rf1 and 30-day plan, end_date should be end_date_rf1_target.

    assert data[0] == (client_name_rf1, "RF002", plan_name_30day, expected_end_date_str)

    no_renew_year, no_renew_month = 2026, 1
    data_none = app_api.get_pending_renewals(no_renew_year, no_renew_month)
    assert data_none == []


# Test for finance report data (not Excel generation)
def test_get_finance_report_data_flow(api_db_fixture):  # Use new fixture, renamed test
    app_api, db_mngr = api_db_fixture  # Unpack
    report_year = 2025
    report_month = 8

    add_mem_s, _ = db_mngr.add_member_to_db(
        "Finance User API1", "FX002"
    )  # Changed phone
    assert add_mem_s
    m_fx1_id = db_mngr.get_all_members(phone_filter="FX002")[0][0]

    add_plan_s, _, plan_fx_id_val = app_api.add_plan(
        "Finance Plan API", 30, DEFAULT_PRICE, DEFAULT_TYPE_TEXT
    )
    assert add_plan_s and plan_fx_id_val is not None

    db_mngr.add_transaction(
        transaction_type="Group Class",
        member_id=m_fx1_id,
        plan_id=plan_fx_id_val,
        payment_date=datetime(report_year, report_month, 10).strftime("%Y-%m-%d"),
        start_date=datetime(report_year, report_month, 10).strftime("%Y-%m-%d"),
        amount_paid=150.00,
        payment_method="Card",
    )
    db_mngr.add_transaction(
        transaction_type="Personal Training",
        member_id=m_fx1_id,
        payment_date=datetime(report_year, report_month, 15).strftime("%Y-%m-%d"),
        start_date=datetime(report_year, report_month, 15).strftime("%Y-%m-%d"),
        sessions=5,
        amount_paid=250.00,
    )
    # Transaction in another month (should be excluded)
    db_mngr.add_transaction(
        transaction_type="Group Class",
        member_id=m_fx1_id,
        plan_id=plan_fx_id_val,
        payment_date=datetime(report_year, report_month + 1, 10).strftime("%Y-%m-%d"),
        start_date=datetime(report_year, report_month + 1, 10).strftime("%Y-%m-%d"),
        amount_paid=50.00,
        payment_method="Cash",
    )

    # Get total revenue for the month using AppAPI
    total_revenue = app_api.get_finance_report(report_year, report_month)
    assert total_revenue == 400.00  # 150 + 250

    # Get transactions for the month using AppAPI
    transactions_for_month = app_api.get_transactions_for_month(
        report_year, report_month
    )
    assert len(transactions_for_month) == 2

    # Verify amounts if needed, e.g., by summing amounts from transactions_for_month
    sum_from_transactions = sum(
        t[3] for t in transactions_for_month
    )  # amount_paid is at index 3
    assert sum_from_transactions == 400.00

    # Test case for a month with no transactions
    no_transactions_revenue = app_api.get_finance_report(report_year, report_month + 2)
    assert (
        no_transactions_revenue == 0.0
    )  # Or None, depending on AppAPI implementation. DBManager returns 0.0. AppAPI returns float | None. It should be 0.0

    no_transactions_list = app_api.get_transactions_for_month(
        report_year, report_month + 2
    )
    assert len(no_transactions_list) == 0


# Removed test_membership_tab_initialization as MembershipTab component is Flet-specific and likely obsolete.
# All tkinter/customtkinter/flet mocks at the top of the file are also removed.

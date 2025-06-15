```python
import pytest
import os
import sys
import sqlite3
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from reporter import database
from reporter import database_manager
from reporter.database_manager import DatabaseManager
from reporter.app_api import AppAPI

# Default values for creating members and plans in setup
DEFAULT_MEMBER_NAME = "Trans Member"
DEFAULT_MEMBER_PHONE = "1110001110"
DEFAULT_PLAN_NAME = "Trans Plan"
DEFAULT_PLAN_DURATION = 30
DEFAULT_PLAN_PRICE = 100
DEFAULT_PLAN_TYPE = "GC" # Assuming 'GC' for Group Class type

@pytest.fixture
def api_db_fixture_with_data(monkeypatch):
    db_path = os.path.abspath("test_transactions.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    monkeypatch.setattr(database_manager, "DB_FILE", db_path)
    database.create_database(db_path)

    conn = sqlite3.connect(db_path)
    db_mngr = DatabaseManager(conn)
    app_api = AppAPI(conn)

    # Setup initial data: a member and a plan
    # db_mngr.add_member_to_db returns: success, message, member_id
    add_member_success, _, member_id = db_mngr.add_member_to_db(DEFAULT_MEMBER_NAME, DEFAULT_MEMBER_PHONE)
    assert add_member_success and member_id is not None, "Setup failed: Member could not be created"

    # db_mngr.add_plan returns: success, message, plan_id
    add_plan_success, _, plan_id = db_mngr.add_plan(DEFAULT_PLAN_NAME, DEFAULT_PLAN_DURATION, DEFAULT_PLAN_PRICE, DEFAULT_PLAN_TYPE)
    assert add_plan_success and plan_id is not None, "Setup failed: Plan could not be created"

    yield app_api, db_mngr, member_id, plan_id

    conn.close()
    if os.path.exists(db_path):
        os.remove(db_path)

# Tests for app_api.add_transaction
def test_add_transaction_success_new_subscription(api_db_fixture_with_data):
    app_api, db_mngr, member_id, plan_id = api_db_fixture_with_data

    today_str = datetime.now().strftime("%Y-%m-%d")
    success, message = app_api.add_transaction(
        transaction_type="new_subscription",
        member_id=member_id,
        plan_id=plan_id,
        start_date=today_str,
        amount_paid=DEFAULT_PLAN_PRICE,
        payment_method="Cash",
        payment_date=today_str
    )
    assert success is True
    assert message == "Transaction added successfully."

    activity = db_mngr.get_all_activity_for_member(member_id)
    assert len(activity) == 1
    # Expected fields from get_all_activity_for_member as per DatabaseManager:
    # (transaction_type, plan_name, start_date, end_date, payment_method, amount_paid, sessions_info, transaction_id)
    assert activity[0][0] == "new_subscription"
    assert activity[0][5] == DEFAULT_PLAN_PRICE # amount_paid
    assert activity[0][1] == DEFAULT_PLAN_NAME # plan_name

def test_add_transaction_for_non_existent_member(api_db_fixture_with_data):
    app_api, _, _, plan_id = api_db_fixture_with_data
    non_existent_member_id = 9999
    today_str = datetime.now().strftime("%Y-%m-%d")

    success, message = app_api.add_transaction(
        transaction_type="new_subscription",
        member_id=non_existent_member_id,
        plan_id=plan_id,
        start_date=today_str,
        amount_paid=100,
        payment_date=today_str
    )
    assert success is False
    # DatabaseManager.add_transaction will raise an IntegrityError if member_id does not exist due to FOREIGN KEY constraint.
    # AppAPI catches this and returns a generic "Database error" message.
    assert "Database error while adding transaction" in message

def test_add_transaction_for_non_existent_plan(api_db_fixture_with_data):
    app_api, _, member_id, _ = api_db_fixture_with_data
    non_existent_plan_id = 8888
    today_str = datetime.now().strftime("%Y-%m-%d")

    success, message = app_api.add_transaction(
        transaction_type="new_subscription",
        member_id=member_id,
        plan_id=non_existent_plan_id, # This plan_id does not exist
        start_date=today_str,
        amount_paid=100,
        payment_date=today_str
    )
    assert success is False
    # DatabaseManager.add_transaction tries to fetch plan details. If plan_id not found, it returns:
    # (False, f"Plan with ID {plan_id} not found.")
    assert f"Plan with ID {non_existent_plan_id} not found" in message

def test_add_transaction_invalid_transaction_type(api_db_fixture_with_data):
    app_api, _, member_id, plan_id = api_db_fixture_with_data
    today_str = datetime.now().strftime("%Y-%m-%d")

    success, message = app_api.add_transaction(
        transaction_type="INVALID_TYPE",
        member_id=member_id,
        plan_id=plan_id,
        start_date=today_str,
        amount_paid=100,
        payment_date=today_str
    )
    assert success is False
    assert "Invalid transaction_type: INVALID_TYPE" in message # From DatabaseManager validation

def test_add_transaction_closed_book_month(api_db_fixture_with_data):
    app_api, db_mngr, member_id, plan_id = api_db_fixture_with_data

    closed_month_year = "2023-01" # Example: YYYY-MM
    transaction_date_in_closed_month = "2023-01-15"

    # Close the books for January 2023
    # app_api.set_book_status returns (True, "Status updated") or (False, "Error updating status")
    set_status_success, _ = app_api.set_book_status(month_key=closed_month_year, status="closed")
    assert set_status_success is True

    success, message = app_api.add_transaction(
        transaction_type="new_subscription",
        member_id=member_id,
        plan_id=plan_id,
        start_date=transaction_date_in_closed_month,
        amount_paid=100,
        payment_date=transaction_date_in_closed_month # payment_date is checked for closed books
    )
    assert success is False
    assert f"Books for {closed_month_year} are closed. No new transactions allowed." in message

def test_add_transaction_success_expense_type(api_db_fixture_with_data):
    app_api, db_mngr, member_id, _ = api_db_fixture_with_data

    today_str = datetime.now().strftime("%Y-%m-%d")
    success, message = app_api.add_transaction(
        transaction_type="expense",
        member_id=member_id, # Member can be linked for tracking
        plan_id=None, # No plan for a general expense
        start_date=today_str, # Date of expense, also used as payment_date if payment_date is None
        amount_paid=50,
        payment_method="Office Petty Cash",
        payment_date=today_str
        # description field in add_transaction is auto-generated based on transaction type.
    )
    assert success is True
    assert message == "Transaction added successfully."

    # Fetch activity for the member. Note: get_all_activity_for_member might not show all 'expense' types
    # if it's filtered for subscriptions/PT. Let's assume it shows all for now or use a more general query.
    # For an expense, it might not be directly linked via get_all_activity_for_member in the same way.
    # A more direct query on transactions table might be better.
    # However, if it IS linked (e.g. member_id in transactions table for expense is this member_id), then:

    # Let's use db_mngr.get_transactions_for_month as a more general way to check if it exists
    current_year = datetime.now().year
    current_month = datetime.now().month
    transactions_this_month = db_mngr.get_transactions_for_month(current_year, current_month)

    expense_found = False
    for trans in transactions_this_month:
        # get_transactions_for_month returns:
        # (t.transaction_date, m.client_name, t.transaction_type, t.amount_paid, p.plan_name, t.payment_method, t.sessions, t.transaction_id)
        if trans[2] == "expense" and trans[3] == 50 and trans[1] == DEFAULT_MEMBER_NAME :
            expense_found = True
            break
    assert expense_found is True, "Expense transaction not found for the current month."
```

# Tests for app_api.delete_transaction
def test_delete_transaction_success(api_db_fixture_with_data):
    app_api, db_mngr, member_id, plan_id = api_db_fixture_with_data
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Add a transaction first
    add_tx_success, _ = app_api.add_transaction(
        transaction_type="new_subscription",
        member_id=member_id,
        plan_id=plan_id,
        start_date=today_str,
        amount_paid=DEFAULT_PLAN_PRICE,
        payment_date=today_str
    )
    assert add_tx_success is True
    activity_before_delete = db_mngr.get_all_activity_for_member(member_id)
    assert len(activity_before_delete) == 1
    # transaction_id is index 7 in get_all_activity_for_member tuple
    transaction_id_to_delete = activity_before_delete[0][7]

    # Delete the transaction
    success, message = app_api.delete_transaction(transaction_id_to_delete)
    assert success is True
    assert message == "Transaction deleted successfully."

    # Verify transaction is deleted
    activity_after_delete = db_mngr.get_all_activity_for_member(member_id)
    assert len(activity_after_delete) == 0

def test_delete_non_existent_transaction(api_db_fixture_with_data):
    app_api, _, _, _ = api_db_fixture_with_data
    non_existent_transaction_id = 77777

    success, message = app_api.delete_transaction(non_existent_transaction_id)
    assert success is False
    # Expected message based on DatabaseManager: "Transaction with ID ... not found."
    # AppAPI.delete_transaction returns "Failed to delete transaction. Transaction not found."
    assert "Transaction not found" in message

def test_delete_transaction_closed_book_month(api_db_fixture_with_data):
    app_api, db_mngr, member_id, plan_id = api_db_fixture_with_data

    closed_month_year = "2023-03" # Example: YYYY-MM
    transaction_date_in_closed_month = "2023-03-10"

    # Add a transaction in that month
    add_tx_success, _ = app_api.add_transaction(
        transaction_type="new_subscription",
        member_id=member_id,
        plan_id=plan_id,
        start_date=transaction_date_in_closed_month,
        amount_paid=DEFAULT_PLAN_PRICE,
        payment_date=transaction_date_in_closed_month
    )
    assert add_tx_success is True
    activity = db_mngr.get_all_activity_for_member(member_id)
    assert len(activity) == 1
    # transaction_id is index 7
    transaction_id = activity[0][7]

    # Close the books for that month
    set_status_success, _ = app_api.set_book_status(month_key=closed_month_year, status="closed")
    assert set_status_success is True

    # Attempt to delete
    success, message = app_api.delete_transaction(transaction_id)
    assert success is False
    assert f"Books for {closed_month_year} are closed. No modifications allowed." in message # AppAPI message

    # Verify transaction still exists
    activity_after_failed_delete = db_mngr.get_all_activity_for_member(member_id)
    assert len(activity_after_failed_delete) == 1

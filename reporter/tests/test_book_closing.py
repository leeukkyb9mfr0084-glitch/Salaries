import pytest
import sqlite3
import os
from datetime import datetime
from reporter.gui import GuiController
from reporter import database_manager # Keep for patching globals
from reporter.database_manager import DatabaseManager # Import the class

# Fixture for setting up an in-memory database for each test
@pytest.fixture
def book_closing_fixture(): # Renamed fixture
    conn = sqlite3.connect(":memory:")

    # Create tables manually as in the original fixture
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        phone TEXT UNIQUE,
        join_date TEXT,
        is_active INTEGER NOT NULL DEFAULT 1
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_name TEXT NOT NULL UNIQUE,
        duration_days INTEGER NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        transaction_type TEXT NOT NULL,
        plan_id INTEGER,
        payment_date TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT,
        amount_paid REAL NOT NULL,
        payment_method TEXT,
        sessions INTEGER,
        FOREIGN KEY (member_id) REFERENCES members (member_id),
        FOREIGN KEY (plan_id) REFERENCES plans (plan_id)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monthly_book_status (
        month_key TEXT PRIMARY KEY, -- e.g., "2025-06"
        status TEXT NOT NULL CHECK(status IN ('open', 'closed')),
        closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()

    # This is the DatabaseManager instance tests will use for direct calls
    db_mngr_instance = DatabaseManager(conn)

    # Patch database_manager globals so GuiController picks up the same in-memory DB
    original_db_file = database_manager.DB_FILE
    original_test_conn = getattr(database_manager, '_TEST_IN_MEMORY_CONNECTION', None) # Use getattr for safety

    database_manager.DB_FILE = ":memory:"
    database_manager._TEST_IN_MEMORY_CONNECTION = conn

    controller = GuiController() # Controller will now use the in-memory db via patched globals

    yield controller, db_mngr_instance # Tests can use both controller and direct db_manager

    # Teardown
    conn.close()
    database_manager.DB_FILE = original_db_file # Restore original globals
    database_manager._TEST_IN_MEMORY_CONNECTION = original_test_conn


def test_close_and_reopen_flow(book_closing_fixture): # Use new fixture
    controller, db_mngr = book_closing_fixture # Unpack controller and db_manager
    test_year = 2025
    test_month = 7
    month_key = f"{test_year:04d}-{test_month:02d}"

    # Close books
    close_success, close_message = controller.close_books_action(test_year, test_month)
    assert close_success is True
    assert f"Books for {month_key} closed successfully." in close_message

    # Check status: CLOSED
    status_message_closed = controller.get_book_status_action(test_year, test_month)
    assert f"Status for {month_key}: CLOSED" in status_message_closed

    # Re-open books
    open_success, open_message = controller.open_books_action(test_year, test_month)
    assert open_success is True
    assert f"Books for {month_key} re-opened successfully." in open_message

    # Check status: OPEN
    status_message_open = controller.get_book_status_action(test_year, test_month)
    assert f"Status for {month_key}: OPEN" in status_message_open

def test_add_transaction_to_closed_month(book_closing_fixture): # Use new fixture
    controller, db_mngr = book_closing_fixture # Unpack
    test_year = 2026
    test_month = 3
    payment_date_str = f"{test_year:04d}-{test_month:02d}-15" # A date within the test month
    month_key = f"{test_year:04d}-{test_month:02d}"

    # 1. Add a dummy member and plan for the transaction to pass initial validations
    member_name = "Test Member for Closed Month"
    member_phone = "123000999"
    db_mngr.add_member_to_db(member_name, member_phone) # Use db_mngr

    # Retrieve the added member to get their ID
    cursor = db_mngr.conn.cursor() # Use db_mngr.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone,))
    member_result = cursor.fetchone()
    assert member_result is not None, "Test member setup failed"
    member_id = member_result[0]

    plan_name = "Test Plan for Closed Month"
    plan_duration = 30
    success_add_plan, message_add_plan, plan_id = db_mngr.add_plan(plan_name, plan_duration) # Use db_mngr
    assert success_add_plan is True, f"Failed to add plan during test setup: {message_add_plan}"
    assert plan_id is not None, "Test plan setup failed to return a valid plan_id"

    # 2. Close the books for the test month
    close_success, _ = controller.close_books_action(test_year, test_month)
    assert close_success is True

    # 3. Attempt to add a transaction to the closed month
    # Using controller.save_membership_action as it internally calls database_manager.add_transaction
    # which contains the book closing check.
    # This is more of an integration test for the GUI action.
    add_success, add_message = controller.save_membership_action(
        membership_type="Group Class",
        member_id=member_id, # Use the ID of the dummy member
        start_date_str="2026-03-01", # Can be any valid date for the transaction itself
        amount_paid_str="100.00",
        selected_plan_id=plan_id, # Use the ID of the dummy plan
        payment_date_str=payment_date_str, # CRITICAL: Date within the closed month
        payment_method="Cash"
    )

    assert add_success is False
    # The exact error message from gui.py's save_membership_action, which gets it from database_manager.add_transaction
    expected_error_part = f"Cannot add transaction. Books for {month_key} are closed"
    assert expected_error_part in add_message

    # 4. Verify book is still closed
    status_message_closed = controller.get_book_status_action(test_year, test_month)
    assert f"Status for {month_key}: CLOSED" in status_message_closed

    # 5. (Optional) Re-open books and try adding again - should succeed
    controller.open_books_action(test_year, test_month)

    add_success_reopened, add_message_reopened = controller.save_membership_action(
        membership_type="Group Class",
        member_id=member_id,
        start_date_str="2026-03-01",
        amount_paid_str="100.00",
        selected_plan_id=plan_id,
        payment_date_str=payment_date_str,
        payment_method="Cash"
    )
    assert add_success_reopened is True
    assert "membership added successfully" in add_message_reopened.lower()

def test_delete_transaction_from_closed_month(book_closing_fixture): # Use new fixture
    controller, db_mngr = book_closing_fixture # Unpack
    test_year = 2027
    test_month = 5
    payment_date_str = f"{test_year:04d}-{test_month:02d}-10"
    month_key = f"{test_year:04d}-{test_month:02d}"

    # 1. Add a dummy member and plan
    member_name_del = "Delete Test Member"
    member_phone_del = "789012345"
    success_add_member_del, _ = db_mngr.add_member_to_db(member_name_del, member_phone_del) # Use db_mngr
    assert success_add_member_del is True, "Failed to add member for delete test setup"

    cursor = db_mngr.conn.cursor() # Use db_mngr.conn
    cursor.execute("SELECT member_id FROM members WHERE phone = ?", (member_phone_del,))
    member_id_row = cursor.fetchone()
    assert member_id_row is not None, "Failed to retrieve member_id for delete test setup"
    member_id = member_id_row[0]

    success_add_plan_del, message_add_plan_del, plan_id_del = db_mngr.add_plan("Delete Test Plan", 30) # Use db_mngr
    assert success_add_plan_del is True, f"Failed to add plan for delete test setup: {message_add_plan_del}"
    assert plan_id_del is not None, "Test plan setup for delete test failed to return a valid plan_id"

    # 2. Add a transaction in an open month first
    add_tx_success, _ = db_mngr.add_transaction( # Use db_mngr
        transaction_type="Group Class",
        member_id=member_id,
        plan_id=plan_id_del,
        payment_date=payment_date_str,
        start_date=payment_date_str,
        amount_paid=50.0,
        payment_method="Card"
    )
    assert add_tx_success is True, "Failed to add initial transaction for deletion test."

    cursor.execute("SELECT transaction_id FROM transactions WHERE member_id = ? AND payment_date = ?", (member_id, payment_date_str))
    tx_result = cursor.fetchone()
    assert tx_result is not None, "Could not retrieve transaction_id for test."
    transaction_id = tx_result[0]

    # 3. Close the books for the test month
    close_success, _ = controller.close_books_action(test_year, test_month)
    assert close_success is True

    # 4. Attempt to delete the transaction from the closed month using GuiController action
    # The GuiController's delete_transaction_action calls database_manager.delete_transaction
    # which should have the check.
    delete_success, delete_message = controller.delete_transaction_action(transaction_id)

    assert delete_success is False # This depends on delete_transaction_action propagating the False from DB layer
    expected_error_part = f"Cannot delete transaction. Books for {month_key} are closed"

    # The actual message might come from delete_transaction in database_manager,
    # which is then wrapped by delete_transaction_action in GuiController.
    # Let's check if delete_transaction_action correctly returns the error.
    # The current GuiController.delete_transaction_action returns a generic "Failed to delete transaction"
    # if database_manager.delete_transaction returns (False, "Specific error").
    # This test might reveal a need to improve error propagation in GuiController.
    # For now, let's assume direct error message or a part of it.
    # Based on current gui.py:
    # controller.delete_transaction_action returns (False, "Failed to delete transaction...")
    # database_manager.delete_transaction returns (False, "Cannot delete transaction. Books for {month_key} are closed.")
    # So, the test for `delete_message` needs to align with what `controller.delete_transaction_action` returns.
    # This test will be more robust if GuiController.delete_transaction_action returns the specific message.
    # Let's assume for now that the subtask is to test the *current* behavior.
    # If database_manager.delete_transaction returns (False, specific_msg), and GuiController.delete_transaction_action
    # returns (False, generic_msg), then we test for generic_msg.
    # However, the prompt implies testing the underlying book closing logic's effect.
    # Let's adjust the GuiController.delete_transaction_action in a prior step if necessary,
    # or directly test database_manager.delete_transaction here.
    # Given the task asks to test via GuiController, we test its output.
    # The current GuiController.delete_transaction_action(transaction_id) returns:
    #   success, message = database_manager.delete_transaction(transaction_id) -> this is (bool, str)
    #   if success: return True, "Transaction deleted successfully."
    #   else: return False, "Failed to delete transaction. It might have already been deleted or does not exist."
    # This means the specific error message from database_manager IS NOT propagated by the controller.
    # This test should reflect that, or the controller should be changed first.
    # For this task, I will assume the controller is as-is.
    # THEREFORE, the detailed error message won't be available from controller.delete_transaction_action.
    # The test should check that the transaction was indeed *not* deleted.

    # Re-evaluating: The task is to test "book closing logic". The check is in database_manager.
    # If GuiController obscures the specific error, the test for the *specific message* should target database_manager.
    # However, the prompt asks to use `controller.save_membership_action` and implies testing controller actions.
    # Let's assume the intent is that GuiController *should* propagate errors correctly.
    # If it doesn't, this test would fail on the message part, highlighting an issue.

    # Let's check the current database_manager.delete_transaction
    # It returns (False, f"Cannot delete transaction. Books for {transaction_month_key} are closed.")
    # And GuiController.delete_transaction_action:
    # success, message = database_manager.delete_transaction(transaction_id)
    # if success: return True, "Transaction deleted successfully."
    # else: return False, message <--- IT DOES PROPAGATE THE MESSAGE! My previous analysis was wrong.

    assert expected_error_part in delete_message, f"Error message mismatch: {delete_message}"


    # 5. Verify transaction still exists
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE transaction_id = ?", (transaction_id,))
    assert cursor.fetchone()[0] == 1, "Transaction should still exist as books are closed."

    # 6. Re-open books and try deleting again - should succeed
    controller.open_books_action(test_year, test_month)
    delete_success_reopened, delete_message_reopened = controller.delete_transaction_action(transaction_id)
    assert delete_success_reopened is True
    assert "Transaction deleted successfully." in delete_message_reopened

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE transaction_id = ?", (transaction_id,))
    assert cursor.fetchone()[0] == 0, "Transaction should have been deleted after re-opening books."

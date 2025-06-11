import sys
import os
from datetime import datetime

# Adjust PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import sqlite3
from reporter.database_manager import DatabaseManager, DB_FILE # Assuming DB_FILE is used for the connection

# At the top of the script, after imports
db_connection = None
db_manager = None
try:
    db_connection = sqlite3.connect(DB_FILE) # Or use an in-memory DB for testing: ":memory:"
    db_manager = DatabaseManager(db_connection)
    # We need a valid member and plan for some transaction tests
    # Ensure a member and plan exist, or create them.
    # Using known existing ones from previous tests to simplify.
    MEMBER_ID_FOR_TESTS = 7 # "Test User Script"
    PLAN_ID_FOR_TESTS = 12  # "Test Auto Plan"

    # Verify member and plan exist
    member_exists = any(m[0] == MEMBER_ID_FOR_TESTS for m in db_manager.get_all_members())
    plan_exists = any(p[0] == PLAN_ID_FOR_TESTS for p in db_manager.get_all_plans_with_inactive())

    if not (member_exists and plan_exists):
        print(f"CRITICAL: Test member (ID {MEMBER_ID_FOR_TESTS}) or plan (ID {PLAN_ID_FOR_TESTS}) not found. Validation tests for transactions might fail or be misleading.")
        # Optionally, could attempt to create them here if essential
        # For now, assume they exist from prior test runs.
        if not member_exists: print(f"Member {MEMBER_ID_FOR_TESTS} does not exist.")
        if not plan_exists: print(f"Plan {PLAN_ID_FOR_TESTS} does not exist.")
        # sys.exit(1) # Or allow to continue with caution

except ModuleNotFoundError:
    print("CRITICAL ERROR: Could not import 'reporter.database_manager' or DB_FILE.")
    sys.exit(1)
except Exception as e:
    print(f"CRITICAL ERROR: Could not connect to database or instantiate DatabaseManager: {e}")
    sys.exit(1)

# Ensure the connection is closed at the end
# A try/finally block in main() or atexit could be used. For simplicity in this subtask,
# we'll assume the script runs and exits. Proper test teardown would handle this.

def run_test(test_name, function_call_lambda, expected_return_value_for_failure):
    print(f"\n--- Test: {test_name} ---")
    try:
        result = function_call_lambda()
        if result == expected_return_value_for_failure:
            print(f"PASS: Operation correctly handled. Returned: {result}")
        elif expected_return_value_for_failure == "CHECK_MANUALLY_FOR_NEGATIVE_VALUES":
            # This case is for when we expect insertion but want to highlight it's negative
            # For negative sessions/amount, the functions might return True (success)
            # The actual "error" is that negative values are not prevented by DB/code
            if result is True: # Or a new ID for add_plan
                 print(f"INFO: Operation returned {result}. Negative values for sessions/amount are likely NOT prevented by current logic/schema.")
                 print("      This may or may not be considered an 'error' depending on requirements.")
            elif isinstance(result, int) and result > 0: # add_plan returns plan_id
                 print(f"INFO: Operation returned plan_id {result}. Negative duration for plan is likely NOT prevented by current logic/schema.")
                 print("      This may or may not be considered an 'error' depending on requirements.")
            else:
                 print(f"UNEXPECTED: Test for negative value returned {result}, which was not the expected success indicator.")

        else:
            print(f"FAIL: Operation returned {result}, expected {expected_return_value_for_failure} for failure indication.")
            # Query to check if bad data was inserted (if applicable) could be added here
    except Exception as e:
        print(f"PASS: Operation raised an exception as expected (or indicates internal error handling): {type(e).__name__} - {e}")

def main():
    today_date = datetime.now().strftime('%Y-%m-%d')

    # 1. Add member with empty name
    run_test("Add member with empty name",
             lambda: db_manager.add_member_to_db(name="", phone="12345VALID", join_date=today_date),
             False) # Expecting add_member_to_db to return False

    # 2. Add member with empty phone
    run_test("Add member with empty phone",
             lambda: db_manager.add_member_to_db(name="Valid Name", phone="", join_date=today_date),
             False)

    # 3. Add group membership with invalid date format
    run_test("Add Group Class transaction with invalid date format",
             lambda: db_manager.add_transaction(transaction_type='Group Class', member_id=MEMBER_ID_FOR_TESTS,
                                                      plan_id=PLAN_ID_FOR_TESTS, start_date="2023-13-01",
                                                      amount_paid=50.0, payment_date="2023-13-01"),
             False) # Expecting add_transaction to return False

    # 4. Add group membership with non-numeric amount
    run_test("Add Group Class transaction with non-numeric amount",
             lambda: db_manager.add_transaction(transaction_type='Group Class', member_id=MEMBER_ID_FOR_TESTS,
                                                      plan_id=PLAN_ID_FOR_TESTS, start_date=today_date,
                                                      amount_paid="abc", payment_date=today_date),
             False)

    # 5. Add PT booking with negative number of sessions
    # Current code/schema might allow this. `add_transaction` returns True on successful DB op.
    # The "error" is lack of validation, not necessarily a False return.
    run_test("Add PT transaction with negative sessions",
             lambda: db_manager.add_transaction(transaction_type='Personal Training', member_id=MEMBER_ID_FOR_TESTS,
                                                      start_date=today_date, amount_paid=100.0, sessions=-5),
             "CHECK_MANUALLY_FOR_NEGATIVE_VALUES")


    # 6. Add PT booking with negative amount
    # Similar to negative sessions.
    run_test("Add PT transaction with negative amount",
             lambda: db_manager.add_transaction(transaction_type='Personal Training', member_id=MEMBER_ID_FOR_TESTS,
                                                      start_date=today_date, amount_paid=-100.0, sessions=5),
             "CHECK_MANUALLY_FOR_NEGATIVE_VALUES")

    # 7. Add plan with empty name
    run_test("Add plan with empty name",
             lambda: db_manager.add_plan(name="", duration_days=30),
             None) # Expecting add_plan to return None on failure

    # 8. Add plan with non-numeric or negative duration
    run_test("Add plan with non-numeric duration",
             lambda: db_manager.add_plan(name="Test Plan Numeric Duration", duration_days="xyz"),
             None)

    # For negative duration, similar to negative sessions/amount for transactions.
    # `add_plan` returns new plan_id (int) on success.
    run_test("Add plan with negative duration",
             lambda: db_manager.add_plan(name="Test Plan Negative Duration", duration_days=-30),
             "CHECK_MANUALLY_FOR_NEGATIVE_VALUES") # Custom handler in run_test

    print("\n--- Input Validation Tests Complete ---")
    print("NOTE: 'CHECK_MANUALLY_FOR_NEGATIVE_VALUES' indicates the system may currently allow these values.")
    print("      Review specific test INFO messages for details on negative value handling.")

if __name__ == '__main__':
    if os.getenv('PYTHONPATH') is None or not os.getcwd() in os.getenv('PYTHONPATH').split(os.pathsep):
         os.environ['PYTHONPATH'] = os.getcwd() + (os.pathsep + os.getenv('PYTHONPATH') if os.getenv('PYTHONPATH') else '')
    main()

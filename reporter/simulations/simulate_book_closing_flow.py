# reporter/simulations/simulate_book_closing_flow.py

import os
import sys
from datetime import datetime

# Correctly adjust sys.path to enable imports from the 'reporter' package and its parent
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import sqlite3 # Import sqlite3
from reporter.database import create_database
from reporter.gui import GuiController
from reporter import database_manager # Import the module itself for monkeypatching

# --- Simulation Config ---
# Place sim_data inside reporter/simulations/
SIM_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_data")
SIM_DB_FILE = os.path.join(SIM_DB_DIR, "simulation_kranos_data_book_closing.db")

TEST_MEMBER_NAME = "Sim Member BookClose"
TEST_MEMBER_PHONE = "74622001" # Changed to be digits only
TEST_YEAR = 2030
TEST_MONTH = 8 # August
TEST_MONTH_KEY = f"{TEST_YEAR:04d}-{TEST_MONTH:02d}"
PAYMENT_DATE_1 = f"{TEST_YEAR:04d}-{TEST_MONTH:02d}-10"
PAYMENT_DATE_2 = f"{TEST_YEAR:04d}-{TEST_MONTH:02d}-15"
AMOUNT_PAID_STR = "100.00"
PAYMENT_METHOD_GC = "SimPayGC"

original_db_file_path = None

def setup_simulation_environment():
    """Sets up a clean database for the simulation."""
    global original_db_file_path
    print(f"--- Setting up simulation environment ---")
    print(f"Simulation Database: {SIM_DB_FILE}")
    os.makedirs(SIM_DB_DIR, exist_ok=True)
    if os.path.exists(SIM_DB_FILE):
        os.remove(SIM_DB_FILE)

    original_db_file_path = database_manager.DB_FILE
    database_manager.DB_FILE = SIM_DB_FILE

    create_database(SIM_DB_FILE) # This should create tables
    # Seed initial plans as the simulation might depend on them
    temp_sim_conn = sqlite3.connect(SIM_DB_FILE) # Create connection directly
    try:
        from reporter.database import seed_initial_plans # Keep this import for now
        seed_initial_plans(temp_sim_conn)
        temp_sim_conn.commit() # Ensure commit if seed_initial_plans doesn't
        print(f"Seeded initial plans into {SIM_DB_FILE}")
    except Exception as e_seed:
        print(f"Error seeding plans into {SIM_DB_FILE}: {e_seed}", file=sys.stderr)
    finally:
        if temp_sim_conn:
            temp_sim_conn.close()

    print(f"Simulation database created, initialized, and seeded at {SIM_DB_FILE}")
    print(f"Database manager is now using: {database_manager.DB_FILE}")

def run_simulation(controller: GuiController): # Accept controller as argument
    """Runs the book closing UI flow simulation."""
    print(f"\n--- Starting Book Closing Flow Simulation ---")
    # controller = GuiController() # Controller is now passed in

    print(f"\nStep 1: Adding test member and fetching plan...")
    success, msg = controller.save_member_action(TEST_MEMBER_NAME, TEST_MEMBER_PHONE)
    assert success, f"Failed to add test member '{TEST_MEMBER_NAME}': {msg}"
    print(f"Test member '{TEST_MEMBER_NAME}' added: {msg}")

    member_details = controller.db_manager.get_member_by_phone(TEST_MEMBER_PHONE)
    assert member_details, f"Could not retrieve test member '{TEST_MEMBER_PHONE}' after adding."
    member_id, _ = member_details
    print(f"Test member ID: {member_id}")

    active_plans = controller.get_active_plans() # This uses controller's db_manager implicitly
    assert active_plans, "No active plans found. Cannot proceed with simulation."
    plan_id = active_plans[0][0]
    print(f"Using plan ID: {plan_id}")

    print(f"\nStep 2: Adding initial transaction to month {TEST_MONTH_KEY}...")
    db_setup_success = controller.db_manager.set_book_status(TEST_MONTH_KEY, "open")
    assert db_setup_success, f"Failed to ensure book status is 'open' for {TEST_MONTH_KEY} at setup."
    print(f"Ensured book status for {TEST_MONTH_KEY} is 'open' before first transaction.")

    success, msg = controller.save_membership_action(
        membership_type="Group Class",
        member_id=member_id,
        start_date_str=PAYMENT_DATE_1,
        amount_paid_str=AMOUNT_PAID_STR,
        selected_plan_id=plan_id,
        payment_date_str=PAYMENT_DATE_1,
        payment_method=PAYMENT_METHOD_GC
    )
    assert success, f"Failed to add initial transaction: {msg}"
    print(f"Initial transaction added: {msg}")

    print(f"\nStep 3: Closing books for month {TEST_MONTH_KEY}...")
    success, msg = controller.close_books_action(TEST_YEAR, TEST_MONTH)
    assert success, f"Failed to close books: {msg}"
    print(f"Books closed action: {msg}")

    status_msg = controller.get_book_status_action(TEST_YEAR, TEST_MONTH)
    print(f"Status check: {status_msg}")
    assert "closed" in status_msg.lower(), f"Books for {TEST_MONTH_KEY} should be 'closed', but status is: {status_msg}"

    print(f"\nStep 4: Attempting to add transaction to {TEST_MONTH_KEY} (now closed)...")
    success, msg = controller.save_membership_action(
        membership_type="Group Class",
        member_id=member_id,
        start_date_str=PAYMENT_DATE_2,
        amount_paid_str=AMOUNT_PAID_STR,
        selected_plan_id=plan_id,
        payment_date_str=PAYMENT_DATE_2,
        payment_method=PAYMENT_METHOD_GC
    )
    print(f"Attempt to add to closed month - Success: {success}, Message: {msg}") # More detailed print
    assert success is False, f"Test: Should fail to add transaction to closed month. Success was {success}, Message: {msg}"
    expected_fail_msg_part = f"books for {TEST_MONTH_KEY} are closed"
    assert expected_fail_msg_part in msg.lower(), f"Failure message '{msg}' did not contain expected part '{expected_fail_msg_part}'"

    print(f"\nStep 5: Re-opening books for month {TEST_MONTH_KEY}...")
    success, msg = controller.open_books_action(TEST_YEAR, TEST_MONTH)
    assert success, f"Failed to re-open books: {msg}"
    print(f"Books re-opened action: {msg}")

    status_msg = controller.get_book_status_action(TEST_YEAR, TEST_MONTH)
    print(f"Status check: {status_msg}")
    assert "open" in status_msg.lower(), f"Books for {TEST_MONTH_KEY} should be 'open', but status is: {status_msg}"

    print(f"\nStep 6: Attempting to add transaction to {TEST_MONTH_KEY} (now open)...")
    success, msg = controller.save_membership_action(
        membership_type="Group Class",
        member_id=member_id,
        start_date_str=PAYMENT_DATE_2,
        amount_paid_str=AMOUNT_PAID_STR,
        selected_plan_id=plan_id,
        payment_date_str=PAYMENT_DATE_2,
        payment_method=PAYMENT_METHOD_GC
    )
    assert success, f"Failed to add transaction to re-opened month: {msg}"
    print(f"Transaction added to re-opened month: {msg}")

    print(f"\n--- Book Closing Flow Simulation Completed Successfully ---")

def cleanup_simulation_environment():
    """Cleans up by restoring DB_FILE path."""
    global original_db_file_path
    print(f"\n--- Simulation cleanup ---")
    if original_db_file_path:
        database_manager.DB_FILE = original_db_file_path
        print(f"Restored database_manager.DB_FILE to: {database_manager.DB_FILE}")

if __name__ == "__main__":
    db_connection = None # Initialize db_connection
    try:
        setup_simulation_environment()

        # Create the main DB connection for the controller
        db_connection = sqlite3.connect(SIM_DB_FILE, check_same_thread=False)
        controller = GuiController(db_connection) # Pass connection to controller

        run_simulation(controller) # Pass controller
    except AssertionError as e:
        print(f"\n--- SIMULATION FAILED: {e} ---", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n--- SIMULATION ERRORED UNEXPECTEDLY: {e} ---", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)
    finally:
        if db_connection: # Close the main connection
            db_connection.close()
            print(f"Closed main DB connection to {SIM_DB_FILE}")
        cleanup_simulation_environment()
        print(f"--- Simulation script finished ---")

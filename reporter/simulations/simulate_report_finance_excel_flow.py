import os
import sys
from datetime import datetime, timedelta
import time

# --- Setup Project Path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from reporter.gui import GuiController
from reporter import database_manager
from reporter.database import create_database, seed_initial_plans

# --- Simulation Database Setup ---
SIMULATION_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
# Using a specific DB file for this simulation
SIMULATION_DB_FILE = os.path.join(
    SIMULATION_DB_DIR, "simulation_kranos_data_finance.db"
)
SIMULATION_OUTPUT_DIR = os.path.join(project_root, "reporter", "simulations", "output")

# original_db_file is captured in __main__ block

# Define SIM_DB_DIR and SIM_DB_FILE at global scope
SIM_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
SIM_DB_FILE = os.path.join(SIM_DB_DIR, "simulation_kranos_data_finance.db")
# SIMULATION_OUTPUT_DIR is already global


def main_simulation_logic(controller: GuiController):  # Renamed and controller passed
    print("\n--- Starting Simulation: Finance Report Excel Flow ---")

    # 1. Add transaction data for a specific month/year
    report_year = datetime.now().year
    report_month = datetime.now().month  # Use current month for simplicity

    # If current month is January, use December of last year to avoid issues with timedelta(days=30) for previous month
    if report_month == 1:
        report_month = 12
        report_year -= 1
        target_payment_date_obj = datetime(report_year, report_month, 15)
        other_payment_date_obj = (
            datetime(report_year, report_month - 1, 15)
            if report_month > 1
            else datetime(report_year - 1, 12, 15)
        )

    else:
        target_payment_date_obj = datetime(report_year, report_month, 15)
        other_payment_date_obj = datetime(report_year, report_month - 1, 15)

    target_payment_date = target_payment_date_obj.strftime("%Y-%m-%d")
    other_payment_date = other_payment_date_obj.strftime("%Y-%m-%d")

    print(f"\nStep 1: Adding transaction data for {report_month}/{report_year}...")

    # Member 1
    member_name1 = f"SimFinUser1_{int(time.time())%1000}"
    member_phone1 = f"SFU1{int(time.time())%100000}"
    controller.db_manager.add_member_to_db(member_name1, member_phone1)
    m1_id = controller.db_manager.get_all_members(phone_filter=member_phone1)[0][0]

    # Member 2
    member_name2 = f"SimFinUser2_{int(time.time())%1000}"
    member_phone2 = f"SFU2{int(time.time())%100000}"
    controller.db_manager.add_member_to_db(member_name2, member_phone2)
    m2_id = controller.db_manager.get_all_members(phone_filter=member_phone2)[0][0]

    plans = controller.db_manager.get_all_plans()
    if not plans:
        print("CRITICAL FAILURE: No plans available. Exiting.")
        # cleanup_simulation_environment() # Cleanup is in __main__
        return
    plan_id = plans[0][0]

    # Transaction 1 (in target month)
    controller.db_manager.add_transaction(
        transaction_type="Group Class",
        member_id=m1_id,
        plan_id=plan_id,
        start_date=target_payment_date,
        payment_date=target_payment_date,
        amount_paid=150.75,
        payment_method="SimFinance_Card",
    )
    # Transaction 2 (in target month - PT)
    controller.db_manager.add_transaction(
        transaction_type="Personal Training",
        member_id=m2_id,
        start_date=target_payment_date,
        payment_date=target_payment_date,
        amount_paid=200.50,
        sessions=5,
        payment_method="SimFinance_CashPT",
    )
    # Transaction 3 (different month - should not be in this report)
    controller.db_manager.add_transaction(
        transaction_type="Group Class",
        member_id=m1_id,
        plan_id=plan_id,
        start_date=other_payment_date,
        payment_date=other_payment_date,
        amount_paid=99.00,
        payment_method="SimFinance_OtherMonth",
    )

    print("Transaction data added.")
    expected_total_revenue = 150.75 + 200.50
    print(
        f"Expected total revenue for {report_month}/{report_year} should be: {expected_total_revenue:.2f}"
    )

    # 2. Define save_path
    excel_file_name = f"sim_finance_report_{report_year}_{report_month}.xlsx"
    save_path = os.path.join(SIMULATION_OUTPUT_DIR, excel_file_name)
    print(f"\nStep 2: Report will be saved to: {save_path}")

    # 3. Call controller.generate_finance_report_excel_action
    # This method requires save_path as an argument as discovered in test_gui_flows.py
    print(
        f"\nStep 3: Calling controller.generate_finance_report_excel_action for {report_month}/{report_year}..."
    )
    success, message = controller.generate_finance_report_excel_action(
        report_year, report_month, save_path
    )
    print(f"Controller action message: '{message}' (Success: {success})")

    # 4. Check if Excel file was created
    print("\nStep 4: Verifying Excel file creation...")
    if success and os.path.exists(save_path):
        print(f"SUCCESS: Excel report file created at '{save_path}'.")
        # You could add a step here to open and read the file if openpyxl is available
        # and you want to verify content, e.g., the total revenue cell.
        # For this simulation, existence is the primary check.
    elif success and not os.path.exists(save_path):
        print(
            f"FAILURE: Controller reported success, but Excel file not found at '{save_path}'."
        )
    elif not success and os.path.exists(save_path):
        print(
            f"WARNING: Controller reported failure, but Excel file WAS created at '{save_path}'. Message: {message}"
        )
    else:  # not success and not os.path.exists
        print(
            f"INFO: Excel file not created, as controller reported failure. Message: {message}"
        )
        if (
            "[Errno 2] No such file or directory" in message and save_path == ""
        ):  # Specific check for empty path issue
            print(
                "This failure might be due to an empty save_path being passed and handled as an error."
            )

    # Scenario: User cancels save dialog (simulated by empty save_path to controller)
    print("\nStep 5: Simulating user cancelling save dialog...")
    # The controller's generate_finance_report_excel_action takes save_path.
    # If an empty path is given, it should result in an error as seen in tests.
    # The actual asksaveasfilename dialog is mocked in tests, not directly called here
    # unless the controller itself calls it when save_path is empty (which tests showed it doesn't).

    # This call will try to write to a file named "" if the controller doesn't prevent it.
    # Based on test_gui_flows.py, this leads to an OSError within the report generation logic.
    success_cancel, message_cancel = controller.generate_finance_report_excel_action(
        report_year, report_month, ""
    )
    print(
        f"Controller action message (cancel scenario): '{message_cancel}' (Success: {success_cancel})"
    )
    if (
        not success_cancel
        and "An error occurred" in message_cancel
        and "No such file or directory: ''" in message_cancel
    ):
        print(
            "SUCCESS (Cancel Scenario): Correctly handled empty save path as an error."
        )
    else:
        print(
            "FAILURE (Cancel Scenario): Did not correctly handle empty save path as an error or message mismatch."
        )

    print("\n--- Simulation: Finance Report Excel Flow Complete ---")
    # Cleanup is handled in the __main__ block's finally clause, Excel file left for inspection.


if __name__ == "__main__":
    original_db_manager_db_file = database_manager.DB_FILE  # Store original
    db_connection = None  # Initialize db_connection

    try:
        print(f"--- Main: Setting up simulation DB: {SIM_DB_FILE} ---")
        os.makedirs(SIMULATION_DB_DIR, exist_ok=True)
        os.makedirs(SIMULATION_OUTPUT_DIR, exist_ok=True)  # Ensure output dir exists
        print(f"Simulation output directory: {SIMULATION_OUTPUT_DIR}")

        if os.path.exists(SIM_DB_FILE):
            os.remove(SIM_DB_FILE)
            print(f"Deleted existing simulation DB: {SIM_DB_FILE}")

        database_manager.DB_FILE = SIM_DB_FILE  # Monkeypatch

        create_database(db_name=SIM_DB_FILE)

        import sqlite3  # Ensure sqlite3 is imported

        seed_conn = None
        try:
            seed_conn = sqlite3.connect(SIM_DB_FILE)  # Connection for seeding
            # Clear any previous sim-specific data if necessary, then seed
            cursor = seed_conn.cursor()
            cursor.execute(
                "DELETE FROM transactions WHERE payment_method LIKE 'SimFinance_%'"
            )
            seed_conn.commit()
            print("Cleared previous SimFinance transactions.")

            seed_initial_plans(seed_conn)
            seed_conn.commit()
            print(f"Recreated and seeded simulation DB: {SIM_DB_FILE}")
        except Exception as e_seed:
            print(
                f"Error during DB setup/seed for {SIM_DB_FILE}: {e_seed}",
                file=sys.stderr,
            )
            raise
        finally:
            if seed_conn:
                seed_conn.close()

        # Create the main DB connection for the controller
        db_connection = sqlite3.connect(SIM_DB_FILE, check_same_thread=False)
        controller = GuiController(db_connection)  # Pass connection to controller

        main_simulation_logic(controller)  # Pass controller

    except Exception as e_outer:
        print(f"--- SIMULATION SCRIPT ERROR: {e_outer} ---", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        if db_connection:  # Close the main connection
            db_connection.close()
            print(f"Closed main DB connection to {SIM_DB_FILE}")
        database_manager.DB_FILE = (
            original_db_manager_db_file  # Restore global if it was used
        )
        print(
            f"--- Main: Restored database_manager.DB_FILE to: {original_db_manager_db_file} ---"
        )

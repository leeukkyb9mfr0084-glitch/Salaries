import os
import sys
from datetime import datetime, timedelta
import time

# --- Setup Project Path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from reporter.gui import GuiController
from reporter import database_manager
from reporter.database import create_database, seed_initial_plans

# --- Simulation Database Setup ---
SIMULATION_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
SIMULATION_DB_FILE = os.path.join(SIMULATION_DB_DIR, "simulation_kranos_data.db")
SIMULATION_OUTPUT_DIR = os.path.join(project_root, "reporter", "simulations", "output")


original_db_file = database_manager.DB_FILE

def setup_simulation_environment():
    print(f"--- Setting up Simulation Environment ---")
    print(f"Using simulation database: {SIMULATION_DB_FILE}")
    os.makedirs(SIMULATION_DB_DIR, exist_ok=True)
    os.makedirs(SIMULATION_OUTPUT_DIR, exist_ok=True) # Ensure output directory exists
    print(f"Simulation output directory: {SIMULATION_OUTPUT_DIR}")

    database_manager.DB_FILE = SIMULATION_DB_FILE
    conn = create_database(db_name=SIMULATION_DB_FILE)
    if conn:
        try:
            # Clear relevant data for this simulation if needed
            cursor = conn.cursor()
            # Example: Clear transactions that might interfere if script is re-run
            # For finance report, it's usually fine as it aggregates, but good practice:
            # cursor.execute("DELETE FROM transactions WHERE payment_method LIKE 'SimFinance_%'")
            # conn.commit()

            seed_initial_plans(conn)
            conn.commit()
            print("Simulation database created/ensured and initial plans seeded.")
        except Exception as e:
            print(f"Error during DB setup: {e}")
        finally:
            conn.close()
    else:
        print("Simulation database ensured (may have existed).")
    print("--- Simulation Environment Setup Complete ---")

def cleanup_simulation_environment():
    database_manager.DB_FILE = original_db_file
    print(f"--- Simulation Environment Cleaned Up (DB_FILE restored to {original_db_file}) ---")
    # Optionally, clean up created Excel file - for now, we'll leave it for inspection.
    # excel_file_path = os.path.join(SIMULATION_OUTPUT_DIR, "sim_finance_report.xlsx")
    # if os.path.exists(excel_file_path):
    #     os.remove(excel_file_path)
    #     print(f"Cleaned up: {excel_file_path}")


def main():
    setup_simulation_environment()
    controller = GuiController()
    print("\n--- Starting Simulation: Finance Report Excel Flow ---")

    # 1. Add transaction data for a specific month/year
    report_year = datetime.now().year
    report_month = datetime.now().month # Use current month for simplicity

    # If current month is January, use December of last year to avoid issues with timedelta(days=30) for previous month
    if report_month == 1:
        report_month = 12
        report_year -=1
        target_payment_date_obj = datetime(report_year, report_month, 15)
        other_payment_date_obj = datetime(report_year, report_month -1, 15) if report_month > 1 else datetime(report_year -1, 12, 15)

    else:
        target_payment_date_obj = datetime(report_year, report_month, 15)
        other_payment_date_obj = datetime(report_year, report_month - 1, 15)


    target_payment_date = target_payment_date_obj.strftime('%Y-%m-%d')
    other_payment_date = other_payment_date_obj.strftime('%Y-%m-%d')


    print(f"\nStep 1: Adding transaction data for {report_month}/{report_year}...")

    # Member 1
    member_name1 = f"SimFinUser1_{int(time.time())%1000}"
    member_phone1 = f"SFU1{int(time.time())%100000}"
    database_manager.add_member_to_db(member_name1, member_phone1)
    m1_id = database_manager.get_all_members(phone_filter=member_phone1)[0][0]

    # Member 2
    member_name2 = f"SimFinUser2_{int(time.time())%1000}"
    member_phone2 = f"SFU2{int(time.time())%100000}"
    database_manager.add_member_to_db(member_name2, member_phone2)
    m2_id = database_manager.get_all_members(phone_filter=member_phone2)[0][0]

    plans = database_manager.get_all_plans()
    if not plans:
        print("CRITICAL FAILURE: No plans available. Exiting.")
        cleanup_simulation_environment()
        return
    plan_id = plans[0][0]

    # Transaction 1 (in target month)
    database_manager.add_transaction('Group Class', m1_id, plan_id, target_payment_date, target_payment_date, 150.75, "SimFinance_Card")
    # Transaction 2 (in target month - PT)
    database_manager.add_transaction('Personal Training', m2_id, None, target_payment_date, target_payment_date, 200.50, "SimFinance_CashPT", sessions=5)
    # Transaction 3 (different month - should not be in this report)
    database_manager.add_transaction('Group Class', m1_id, plan_id, other_payment_date, other_payment_date, 99.00, "SimFinance_OtherMonth")

    print("Transaction data added.")
    expected_total_revenue = 150.75 + 200.50
    print(f"Expected total revenue for {report_month}/{report_year} should be: {expected_total_revenue:.2f}")

    # 2. Define save_path
    excel_file_name = f"sim_finance_report_{report_year}_{report_month}.xlsx"
    save_path = os.path.join(SIMULATION_OUTPUT_DIR, excel_file_name)
    print(f"\nStep 2: Report will be saved to: {save_path}")

    # 3. Call controller.generate_finance_report_excel_action
    # This method requires save_path as an argument as discovered in test_gui_flows.py
    print(f"\nStep 3: Calling controller.generate_finance_report_excel_action for {report_month}/{report_year}...")
    success, message = controller.generate_finance_report_excel_action(report_year, report_month, save_path)
    print(f"Controller action message: '{message}' (Success: {success})")

    # 4. Check if Excel file was created
    print("\nStep 4: Verifying Excel file creation...")
    if success and os.path.exists(save_path):
        print(f"SUCCESS: Excel report file created at '{save_path}'.")
        # You could add a step here to open and read the file if openpyxl is available
        # and you want to verify content, e.g., the total revenue cell.
        # For this simulation, existence is the primary check.
    elif success and not os.path.exists(save_path):
        print(f"FAILURE: Controller reported success, but Excel file not found at '{save_path}'.")
    elif not success and os.path.exists(save_path):
        print(f"WARNING: Controller reported failure, but Excel file WAS created at '{save_path}'. Message: {message}")
    else: # not success and not os.path.exists
        print(f"INFO: Excel file not created, as controller reported failure. Message: {message}")
        if "[Errno 2] No such file or directory" in message and save_path == "": # Specific check for empty path issue
             print("This failure might be due to an empty save_path being passed and handled as an error.")


    # Scenario: User cancels save dialog (simulated by empty save_path to controller)
    print("\nStep 5: Simulating user cancelling save dialog...")
    # The controller's generate_finance_report_excel_action takes save_path.
    # If an empty path is given, it should result in an error as seen in tests.
    # The actual asksaveasfilename dialog is mocked in tests, not directly called here
    # unless the controller itself calls it when save_path is empty (which tests showed it doesn't).

    # This call will try to write to a file named "" if the controller doesn't prevent it.
    # Based on test_gui_flows.py, this leads to an OSError within the report generation logic.
    success_cancel, message_cancel = controller.generate_finance_report_excel_action(report_year, report_month, "")
    print(f"Controller action message (cancel scenario): '{message_cancel}' (Success: {success_cancel})")
    if not success_cancel and "An error occurred" in message_cancel and "No such file or directory: ''" in message_cancel :
        print("SUCCESS (Cancel Scenario): Correctly handled empty save path as an error.")
    else:
        print("FAILURE (Cancel Scenario): Did not correctly handle empty save path as an error or message mismatch.")


    print("\n--- Simulation: Finance Report Excel Flow Complete ---")
    cleanup_simulation_environment() # Leaves the generated file in output/ for inspection

if __name__ == "__main__":
    main()

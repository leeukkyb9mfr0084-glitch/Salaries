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
    SIMULATION_DB_DIR, "simulation_kranos_data_renewals.db"
)

# original_db_file is captured in __main__ block

# Define SIM_DB_DIR and SIM_DB_FILE at global scope
SIM_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
SIM_DB_FILE = os.path.join(SIM_DB_DIR, "simulation_kranos_data_renewals.db")


def main_simulation_logic(controller: GuiController):  # Renamed and controller passed
    print("\n--- Starting Simulation: Custom Pending Renewals Report Flow ---")

    # 1. Add member and transaction data for future renewals
    print("\nStep 1: Setting up data for future renewals...")
    member_name_renew = f"SimRenewUser_{int(time.time())%1000}"
    member_phone_renew = f"SRU{int(time.time())%100000}"

    plan_name_renew = f"SimRenewPlan_30Day_{int(time.time())%1000}"
    plan_duration_days = 30

    # Add plan and member
    add_member_success, _ = controller.db_manager.add_member_to_db(
        member_name_renew, member_phone_renew
    )
    if not add_member_success:
        print(f"FAILURE: Could not add member '{member_name_renew}'.")
        return
    member_id_renew = controller.db_manager.get_all_members(
        phone_filter=member_phone_renew
    )[0][0]

    add_plan_success, _, plan_id_renew_val = controller.db_manager.add_plan(
        plan_name_renew, plan_duration_days, is_active=True
    )
    if not add_plan_success or plan_id_renew_val is None:
        print(f"FAILURE: Could not add plan '{plan_name_renew}'.")
        return

    print(
        f"Added member '{member_name_renew}' (ID: {member_id_renew}) and plan '{plan_name_renew}' (ID: {plan_id_renew_val})."
    )

    # Calculate dates for renewal ~2 months from now
    today = datetime.now()
    renewal_month_date = today + timedelta(days=60)  # Target roughly 2 months ahead
    target_year = renewal_month_date.year
    target_month = renewal_month_date.month

    # Make the membership end in that target month
    # Example: if target is July, make it end July 15th.
    end_date_target = datetime(target_year, target_month, 15)
    start_date_for_tx = end_date_target - timedelta(days=plan_duration_days)
    payment_date_for_tx = start_date_for_tx - timedelta(
        days=1
    )  # Payment a day before start

    tx_details_renew = {
        "transaction_type": "Group Class",
        "member_id": member_id_renew,
        "plan_id": plan_id_renew_val,  # Use integer ID
        "payment_date": payment_date_for_tx.strftime("%Y-%m-%d"),
        "start_date": start_date_for_tx.strftime("%Y-%m-%d"),
        "amount_paid": 120.00,
        "payment_method": "SimRenewCash",
    }
    add_tx_success, _ = controller.db_manager.add_transaction(**tx_details_renew)
    if not add_tx_success:
        print(
            f"FAILURE: Could not add transaction for member ID {member_id_renew} to set up renewal."
        )
        return
    print(
        f"Added transaction for member {member_name_renew} with end date {end_date_target.strftime('%Y-%m-%d')}."
    )

    # 2. Call controller.generate_custom_pending_renewals_action
    print(
        f"\nStep 2: Generating custom pending renewals report for {target_month}/{target_year}..."
    )
    success_report, message_report, renewals_data = (
        controller.generate_custom_pending_renewals_action(target_year, target_month)
    )

    print(f"Controller action message: '{message_report}' (Success: {success_report})")

    if success_report and renewals_data:
        print("Renewals Data Found:")
        for item in renewals_data:
            print(f"  - {item}")  # (client_name, phone, plan_name, end_date_str)
        # Verification
        found_expected_member = any(
            item[0] == member_name_renew and item[1] == member_phone_renew
            for item in renewals_data
        )
        if found_expected_member:
            print(
                f"SUCCESS: Expected member '{member_name_renew}' found in renewals report for {target_month}/{target_year}."
            )
        else:
            print(
                f"FAILURE: Expected member '{member_name_renew}' NOT found in renewals report for {target_month}/{target_year}."
            )
    elif success_report and not renewals_data:
        print(
            f"INFO: Controller reported success but no renewals data returned for {target_month}/{target_year}, though data was set up."
        )
    else:
        print(
            f"FAILURE: Report generation failed or returned no data unexpectedly for {target_month}/{target_year}."
        )

    # 3. Test with a date range that should yield no results
    print("\nStep 3: Generating report for a date range with no expected renewals...")
    far_future_year = today.year + 5  # 5 years in the future
    far_future_month = 1

    success_none, message_none, renewals_none = (
        controller.generate_custom_pending_renewals_action(
            far_future_year, far_future_month
        )
    )
    print(
        f"Controller action message (no renewals): '{message_none}' (Success: {success_none})"
    )

    if success_none and not renewals_none:
        print(
            f"SUCCESS: Correctly found no renewals for {far_future_month}/{far_future_year} and appropriate message received."
        )
        expected_no_renewal_message_part = f"No pending renewals found for {datetime(far_future_year, far_future_month, 1).strftime('%B')} {far_future_year}"
        if expected_no_renewal_message_part in message_none:
            print("Appropriate 'no renewals' message confirmed.")
        else:
            print(
                f"WARNING: Message for no renewals was '{message_none}', expected something like '{expected_no_renewal_message_part}'."
            )

    elif success_none and renewals_none:
        print(
            f"FAILURE: Report for {far_future_month}/{far_future_year} unexpectedly returned data: {renewals_none}"
        )
    else:
        print(
            f"FAILURE: Report generation for {far_future_month}/{far_future_year} (no renewals) failed."
        )

    print("\n--- Simulation: Custom Pending Renewals Report Flow Complete ---")
    # Cleanup is handled in the __main__ block's finally clause


if __name__ == "__main__":
    original_db_manager_db_file = database_manager.DB_FILE  # Store original
    db_connection = None  # Initialize db_connection

    try:
        print(f"--- Main: Setting up simulation DB: {SIM_DB_FILE} ---")
        os.makedirs(SIMULATION_DB_DIR, exist_ok=True)
        if os.path.exists(SIMULATION_DB_FILE):
            os.remove(SIM_DB_FILE)
            print(f"Deleted existing simulation DB: {SIM_DB_FILE}")

        database_manager.DB_FILE = SIM_DB_FILE  # Monkeypatch

        create_database(db_name=SIM_DB_FILE)

        import sqlite3  # Ensure sqlite3 is imported

        seed_conn = None
        try:
            seed_conn = sqlite3.connect(SIM_DB_FILE)  # Connection for seeding
            # Clear specific data for this simulation if needed, AFTER seeding
            # This simulation's logic for adding members/plans with unique names might be sufficient.
            # For safety, let's clear any potentially conflicting data from previous runs.
            cursor = seed_conn.cursor()
            cursor.execute("DELETE FROM transactions")
            cursor.execute(
                "DELETE FROM members WHERE client_name LIKE 'SimRenewUser_%'"
            )
            cursor.execute("DELETE FROM plans WHERE plan_name LIKE 'SimRenewPlan_%'")
            seed_conn.commit()
            print(
                "Cleared previous simulation-specific data (transactions, relevant members, plans)."
            )

            seed_initial_plans(seed_conn)  # Seed default plans
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

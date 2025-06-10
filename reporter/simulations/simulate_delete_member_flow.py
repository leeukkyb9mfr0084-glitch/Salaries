import os
import sys
from datetime import datetime, timedelta
import time # For unique identifiers

# --- Setup Project Path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from reporter.gui import GuiController
from reporter import database_manager
from reporter.database import create_database, seed_initial_plans

# --- Simulation Database Setup ---
SIMULATION_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
# Using a specific DB file for this simulation
SIMULATION_DB_FILE = os.path.join(SIMULATION_DB_DIR, "simulation_kranos_data_del_member.db")

# original_db_file is captured in __main__ block

# Define SIM_DB_DIR and SIM_DB_FILE at global scope if they depend on project_root
SIM_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
SIM_DB_FILE = os.path.join(SIM_DB_DIR, "simulation_kranos_data_del_member.db")

def main_simulation_logic(controller: GuiController): # Renamed and controller passed
    print("\n--- Starting Simulation: Delete Member Flow ---")

    # 1. Add a test member
    member_name = f"MemberToDelete_{int(time.time())%1000}"
    member_phone = f"DEL{int(time.time())%100000}"
    print(f"\nStep 1: Adding test member: Name='{member_name}', Phone='{member_phone}'")
    # Use database_manager directly as per test requirements
    # Note: controller.save_member_action would also work but this matches spec
    success_add = database_manager.add_member_to_db(member_name, member_phone)
    if not success_add:
        print(f"FAILURE: Could not add member '{member_name}' via database_manager.")
        cleanup_simulation_environment()
        return

    members_before = database_manager.get_all_members(phone_filter=member_phone)
    if not members_before or members_before[0][1] != member_name:
        print(f"FAILURE: Member '{member_name}' not found in DB after add operation or details mismatch.")
        cleanup_simulation_environment()
        return
    member_id_to_delete = members_before[0][0]
    print(f"Member added successfully. ID: {member_id_to_delete}")

    # 2. Add a transaction for this member
    print(f"\nStep 2: Adding a transaction for member ID {member_id_to_delete}")
    plans = database_manager.get_all_plans()
    if not plans:
        print("FAILURE: No plans found in the database to create a transaction. Seeding might have failed.")
        # Attempt to seed again if needed, or add a default plan
        conn = database_manager.get_db_connection()
        seed_initial_plans(conn) # Try seeding again
        conn.commit()
        conn.close()
        plans = database_manager.get_all_plans()
        if not plans:
             print("CRITICAL FAILURE: Still no plans after re-seed attempt. Exiting.")
             cleanup_simulation_environment()
             return
    plan_id_for_tx = plans[0][0] # Use the first available plan

    tx_success = database_manager.add_transaction(
        transaction_type='Group Class',
        member_id=member_id_to_delete,
        plan_id=plan_id_for_tx,
        payment_date=datetime.now().strftime('%Y-%m-%d'),
        start_date=datetime.now().strftime('%Y-%m-%d'),
        amount_paid=50.00,
        payment_method="SimCash"
    )
    if not tx_success:
        print(f"FAILURE: Could not add transaction for member ID {member_id_to_delete}.")
        cleanup_simulation_environment()
        return
    print(f"Transaction added for member ID {member_id_to_delete}.")

    # Verify transaction was added
    conn_setup_check = database_manager.get_db_connection()
    cursor_setup_check = conn_setup_check.cursor()
    cursor_setup_check.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ?", (member_id_to_delete,))
    transactions_count_before = cursor_setup_check.fetchone()[0]
    conn_setup_check.close()

    if transactions_count_before == 0:
        print(f"FAILURE: Transaction for member ID {member_id_to_delete} not found before delete attempt.")
        # cleanup_simulation_environment() # Handled by finally in __main__
        return
    print(f"Found {transactions_count_before} transaction(s) for the member before deletion.")


    # 3. Call controller.delete_member_action
    print(f"\nStep 3: Calling controller.delete_member_action for member ID {member_id_to_delete}")
    # Note: GuiController.delete_member_action in the actual app might involve a messagebox.askyesno.
    # Here, we are testing the action method directly. If it's hardcoded to use messagebox,
    # this simulation would require mocking or it might fail if tkinter is not fully available.
    # Based on test_gui_flows.py, the controller's deactivate_member_action does NOT use askyesno.
    delete_success, delete_message = controller.deactivate_member_action(member_id_to_delete)
    print(f"Controller action message: '{delete_message}' (Success: {delete_success})")

    if not delete_success:
        print(f"FAILURE: controller.deactivate_member_action reported failure for member ID {member_id_to_delete}.")
        # cleanup_simulation_environment() # Keep env for inspection if needed on failure
        # return # Continue to verification to see state

    # 4. Verify member is deleted
    print("\nStep 4: Verifying member deletion...")
    members_after = database_manager.get_all_members(phone_filter=member_phone)
    if not members_after:
        print(f"SUCCESS: Member '{member_name}' (ID: {member_id_to_delete}) correctly deleted from members table.")
    else:
        print(f"FAILURE: Member '{member_name}' (ID: {member_id_to_delete}) still found in members table.")

    # 5. Verify member's transactions are also deleted
    print("\nStep 5: Verifying member's transactions deletion...")
    # Use get_transactions_with_member_details, filtering by member_id if possible,
    # or check all transactions if member_id is used in the details.
    # The function get_transactions_with_member_details itself joins with members table.
    # If the member is deleted, this function might not return their transactions anyway
    # because the join condition on member_id would fail.
    # A more direct check on the transactions table is better.
    conn_check = database_manager.get_db_connection()
    cursor_check = conn_check.cursor()
    cursor_check.execute("SELECT * FROM transactions WHERE member_id = ?", (member_id_to_delete,))
    transactions_after = cursor_check.fetchall()
    conn_check.close()

    if len(transactions_after) == transactions_count_before:
        print(f"SUCCESS: Transactions for member ID {member_id_to_delete} correctly persisted ({len(transactions_after)} found).")
    else:
        print(f"FAILURE: Expected {transactions_count_before} transaction(s) for member ID {member_id_to_delete}, but found {len(transactions_after)}.")

    print("\n--- Simulation: Delete Member Flow Complete ---")
    # Cleanup is handled in the __main__ block's finally clause

if __name__ == "__main__":
    original_db_manager_db_file = database_manager.DB_FILE # Store original

    try:
        print(f"--- Main: Setting up simulation DB: {SIM_DB_FILE} ---")
        os.makedirs(SIMULATION_DB_DIR, exist_ok=True)
        if os.path.exists(SIM_DB_FILE):
            os.remove(SIM_DB_FILE)
            print(f"Deleted existing simulation DB: {SIM_DB_FILE}")

        database_manager.DB_FILE = SIM_DB_FILE # Monkeypatch

        create_database(db_name=SIM_DB_FILE)

        import sqlite3 # Ensure sqlite3 is imported
        seed_conn = None
        try:
            seed_conn = sqlite3.connect(SIM_DB_FILE)
            seed_initial_plans(seed_conn)
            seed_conn.commit()
            print(f"Recreated and seeded simulation DB: {SIM_DB_FILE}")
        except Exception as e_seed:
            print(f"Error seeding simulation DB {SIM_DB_FILE}: {e_seed}", file=sys.stderr)
            raise
        finally:
            if seed_conn:
                seed_conn.close()

        controller = GuiController()
        main_simulation_logic(controller)

    except Exception as e_outer:
        print(f"--- SIMULATION SCRIPT ERROR: {e_outer} ---", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        database_manager.DB_FILE = original_db_manager_db_file
        print(f"--- Main: Restored database_manager.DB_FILE to: {original_db_manager_db_file} ---")

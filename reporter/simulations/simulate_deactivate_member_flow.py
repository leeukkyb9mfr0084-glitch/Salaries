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
# Using a specific DB file for this deactivation simulation
SIMULATION_DB_FILE = os.path.join(SIMULATION_DB_DIR, "simulation_kranos_data_del_member.db")

# original_db_file is captured in __main__ block

# Define SIM_DB_DIR and SIM_DB_FILE at global scope if they depend on project_root
SIM_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
SIM_DB_FILE = os.path.join(SIM_DB_DIR, "simulation_kranos_data_del_member.db")

def main_simulation_logic(controller: GuiController): # Renamed and controller passed
    print("\n--- Starting Simulation: Deactivate Member Flow ---")

    # 1. Add a test member
    member_name = f"MemberToDelete_{int(time.time())%1000}"
    member_phone = f"DEL{int(time.time())%100000}"
    print(f"\nStep 1: Adding test member: Name='{member_name}', Phone='{member_phone}'")
    # Use database_manager directly as per test requirements
    # Note: controller.save_member_action would also work but this matches spec
    success_add, _ = controller.db_manager.add_member_to_db(member_name, member_phone) # Use controller.db_manager
    if not success_add:
        print(f"FAILURE: Could not add member '{member_name}' via controller.db_manager.")
        # cleanup_simulation_environment() # Cleanup is in __main__
        return

    members_before = controller.db_manager.get_all_members(phone_filter=member_phone) # Use controller.db_manager
    if not members_before or members_before[0][1] != member_name:
        print(f"FAILURE: Member '{member_name}' not found in DB after add operation or details mismatch.")
        # cleanup_simulation_environment() # Cleanup is in __main__
        return
    member_id_to_delete = members_before[0][0]
    print(f"Member added successfully. ID: {member_id_to_delete}")

    # 2. Add a transaction for this member
    print(f"\nStep 2: Adding a transaction for member ID {member_id_to_delete}")
    plans = controller.db_manager.get_all_plans() # Use controller.db_manager
    if not plans:
        print("FAILURE: No plans found in the database to create a transaction. Seeding might have failed.")
        # Attempt to seed again if needed, or add a default plan
        # Using controller.db_manager.conn directly for re-seeding if necessary.
        # This is a bit of a direct access but limited to this recovery scenario.
        print("Attempting to re-seed plans directly via controller's connection...")
        seed_initial_plans(controller.db_manager.conn) # Try seeding again
        controller.db_manager.conn.commit()
        # No close here as it's the controller's main connection.
        plans = controller.db_manager.get_all_plans() # Use controller.db_manager
        if not plans:
             print("CRITICAL FAILURE: Still no plans after re-seed attempt. Exiting.")
             # cleanup_simulation_environment() # Cleanup is in __main__
             return
    plan_id_for_tx = plans[0][0] # Use the first available plan

    tx_success, _ = controller.db_manager.add_transaction( # Use controller.db_manager
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
        # cleanup_simulation_environment() # Cleanup is in __main__
        return
    print(f"Transaction added for member ID {member_id_to_delete}.")

    # Verify transaction was added
    # Using controller's connection for this check
    cursor_setup_check = controller.db_manager.conn.cursor()
    cursor_setup_check.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ?", (member_id_to_delete,))
    transactions_count_before = cursor_setup_check.fetchone()[0]
    # No close for controller.db_manager.conn here

    if transactions_count_before == 0:
        print(f"FAILURE: Transaction for member ID {member_id_to_delete} not found before deactivation attempt.")
        # cleanup_simulation_environment() # Cleanup is in __main__
        return
    print(f"Found {transactions_count_before} transaction(s) for the member before deactivation.")


    # 3. Call controller.deactivate_member_action
    print(f"\nStep 3: Calling controller.deactivate_member_action for member ID {member_id_to_delete}")
    # Note: GuiController.deactivate_member_action in the actual app might involve a messagebox.askyesno.
    # Here, we are testing the action method directly. If it's hardcoded to use messagebox,
    # this simulation would require mocking or it might fail if tkinter is not fully available.
    # Based on test_gui_flows.py, the controller's deactivate_member_action does NOT use askyesno.
    deactivate_success, deactivate_message = controller.deactivate_member_action(member_id_to_delete)
    print(f"Controller action message: '{deactivate_message}' (Success: {deactivate_success})")

    if not deactivate_success:
        print(f"FAILURE: controller.deactivate_member_action reported failure for member ID {member_id_to_delete}.")
        # cleanup_simulation_environment() # Keep env for inspection if needed on failure
        # return # Continue to verification to see state

    # 4. Verify member is deactivated
    print("\nStep 4: Verifying member deactivation...")
    members_after = controller.db_manager.get_all_members(phone_filter=member_phone) # Use controller.db_manager
    if not members_after:
        print(f"SUCCESS: Member '{member_name}' (ID: {member_id_to_delete}) correctly marked as inactive (not found by get_all_members).")
    else:
        print(f"FAILURE: Member '{member_name}' (ID: {member_id_to_delete}) still found by get_all_members after deactivation attempt.")

    # 5. Verify member's transactions are preserved after deactivation
    print("\nStep 5: Verifying member's transactions are preserved after deactivation...")
    # Use get_transactions_with_member_details, filtering by member_id if possible,
    # or check all transactions if member_id is used in the details.
    # The function get_transactions_with_member_details itself joins with members table.
    # If the member is deleted, this function might not return their transactions anyway
    # because the join condition on member_id would fail.
    # A more direct check on the transactions table is better.
    # Using controller's connection for this check
    cursor_check = controller.db_manager.conn.cursor()
    cursor_check.execute("SELECT * FROM transactions WHERE member_id = ?", (member_id_to_delete,))
    transactions_after = cursor_check.fetchall()
    # No close for controller.db_manager.conn here

    if len(transactions_after) == transactions_count_before:
        print(f"SUCCESS: Transactions for member ID {member_id_to_delete} correctly persisted after deactivation ({len(transactions_after)} found).")
    else:
        print(f"FAILURE: Expected {transactions_count_before} transaction(s) for member ID {member_id_to_delete} to be preserved, but found {len(transactions_after)}.")

    print("\n--- Simulation: Deactivate Member Flow Complete ---")
    # Cleanup is handled in the __main__ block's finally clause

if __name__ == "__main__":
    original_db_manager_db_file = database_manager.DB_FILE # Store original
    db_connection = None # Initialize db_connection

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
            seed_conn = sqlite3.connect(SIM_DB_FILE) # Connection for seeding
            seed_initial_plans(seed_conn)
            seed_conn.commit()
            print(f"Recreated and seeded simulation DB: {SIM_DB_FILE}")
        except Exception as e_seed:
            print(f"Error seeding simulation DB {SIM_DB_FILE}: {e_seed}", file=sys.stderr)
            raise
        finally:
            if seed_conn:
                seed_conn.close()

        # Create the main DB connection for the controller
        db_connection = sqlite3.connect(SIM_DB_FILE, check_same_thread=False)
        controller = GuiController(db_connection) # Pass connection to controller

        main_simulation_logic(controller) # Pass controller

    except Exception as e_outer:
        print(f"--- SIMULATION SCRIPT ERROR: {e_outer} ---", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if db_connection: # Close the main connection
            db_connection.close()
            print(f"Closed main DB connection to {SIM_DB_FILE}")
        database_manager.DB_FILE = original_db_manager_db_file # Restore global if it was used
        print(f"--- Main: Restored database_manager.DB_FILE to: {original_db_manager_db_file} ---")

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
SIMULATION_DB_FILE = os.path.join(SIMULATION_DB_DIR, "simulation_kranos_data.db")

original_db_file = database_manager.DB_FILE # Store original DB_FILE

def setup_simulation_environment():
    """Prepares the simulation environment (database and paths)."""
    print(f"--- Setting up Simulation Environment ---")
    print(f"Using simulation database: {SIMULATION_DB_FILE}")
    os.makedirs(SIMULATION_DB_DIR, exist_ok=True)

    database_manager.DB_FILE = SIMULATION_DB_FILE

    conn = create_database(db_name=SIMULATION_DB_FILE)
    if conn:
        try:
            seed_initial_plans(conn)
            conn.commit()
            print("Simulation database created and initial plans seeded.")
        except Exception as e:
            print(f"Error seeding plans: {e}")
        finally:
            conn.close()
    else:
        # If create_database returns None, it means the DB file was already there.
        # We might need to connect manually to seed if seed_initial_plans is not idempotent
        # or if we want to ensure it's always fresh.
        # For this simulation, let's assume it's okay or seed_initial_plans handles it.
        print("Simulation database ensured (may have existed).")
    print("--- Simulation Environment Setup Complete ---")

def cleanup_simulation_environment():
    """Restores the original DB_FILE setting."""
    database_manager.DB_FILE = original_db_file
    print(f"--- Simulation Environment Cleaned Up (DB_FILE restored to {original_db_file}) ---")

def main():
    setup_simulation_environment()
    controller = GuiController()
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
    transactions_before_delete = database_manager.get_transactions_with_member_details(member_id_filter=member_id_to_delete)
    if not transactions_before_delete:
        print(f"FAILURE: Transaction for member ID {member_id_to_delete} not found before delete attempt.")
        cleanup_simulation_environment()
        return
    print(f"Found {len(transactions_before_delete)} transaction(s) for the member before deletion.")


    # 3. Call controller.delete_member_action
    print(f"\nStep 3: Calling controller.delete_member_action for member ID {member_id_to_delete}")
    # Note: GuiController.delete_member_action in the actual app might involve a messagebox.askyesno.
    # Here, we are testing the action method directly. If it's hardcoded to use messagebox,
    # this simulation would require mocking or it might fail if tkinter is not fully available.
    # Based on test_gui_flows.py, the controller's delete_member_action does NOT use askyesno.
    delete_success, delete_message = controller.delete_member_action(member_id_to_delete)
    print(f"Controller action message: '{delete_message}' (Success: {delete_success})")

    if not delete_success:
        print(f"FAILURE: controller.delete_member_action reported failure for member ID {member_id_to_delete}.")
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

    if not transactions_after:
        print(f"SUCCESS: Transactions for member ID {member_id_to_delete} correctly deleted from transactions table.")
    else:
        print(f"FAILURE: {len(transactions_after)} transaction(s) for member ID {member_id_to_delete} still found in transactions table.")

    print("\n--- Simulation: Delete Member Flow Complete ---")
    cleanup_simulation_environment()

if __name__ == "__main__":
    main()

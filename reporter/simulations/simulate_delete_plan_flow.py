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

original_db_file = database_manager.DB_FILE

def setup_simulation_environment():
    print(f"--- Setting up Simulation Environment ---")
    print(f"Using simulation database: {SIMULATION_DB_FILE}")
    os.makedirs(SIMULATION_DB_DIR, exist_ok=True)
    database_manager.DB_FILE = SIMULATION_DB_FILE
    conn = create_database(db_name=SIMULATION_DB_FILE)
    if conn:
        try:
            # Clear existing plans to avoid conflicts if re-running, except for seeded ones
            # This is tricky; seed_initial_plans might add duplicates if not careful.
            # For simulation, let's assume a relatively clean start or that add_plan handles names.
            # We will rely on unique names for simulation-added plans.
            cursor = conn.cursor()
            cursor.execute("DELETE FROM plans WHERE plan_name LIKE 'SimDelPlan_%'") # Clear previous sim plans
            conn.commit()
            print("Cleared previous simulation-specific plans.")

            seed_initial_plans(conn) # Ensure default plans are there
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

def main():
    setup_simulation_environment()
    controller = GuiController()
    print("\n--- Starting Simulation: Delete Plan Flow ---")

    # --- Scenario 1: Delete unused plan ---
    print("\n--- Scenario 1: Delete Unused Plan ---")
    plan_name_unused = f"SimDelPlan_Unused_{int(time.time())%1000}"
    print(f"Step 1.1: Adding an unused plan: Name='{plan_name_unused}', Duration=10 days")

    # Add plan using database_manager directly for more control in simulation script
    # controller.save_plan_action might be interactive or return different things.
    # For simulation, direct db calls for setup are often clearer.
    unused_plan_id = database_manager.add_plan(plan_name_unused, 10, is_active=True)
    if unused_plan_id is None:
        print(f"FAILURE (S1): Could not add unused plan '{plan_name_unused}'.")
        cleanup_simulation_environment()
        return
    print(f"Unused plan added successfully. ID: {unused_plan_id}")

    print(f"\nStep 1.2: Calling controller.delete_plan_action for unused plan ID {unused_plan_id}")
    # Based on test_gui_flows.py, controller.delete_plan_action for an unused plan
    # (which calls database_manager.delete_plan) does not use askyesno.
    delete_success_s1, delete_message_s1 = controller.delete_plan_action(unused_plan_id)
    print(f"Controller action message (S1): '{delete_message_s1}' (Success: {delete_success_s1})")

    print("\nStep 1.3: Verifying unused plan is deleted...")
    plans_after_delete_s1 = database_manager.get_all_plans_with_inactive()
    plan_found_s1 = any(p[0] == unused_plan_id for p in plans_after_delete_s1)
    if not plan_found_s1 and delete_success_s1:
        print(f"SUCCESS (S1): Unused plan ID {unused_plan_id} correctly deleted.")
    elif not plan_found_s1 and not delete_success_s1:
        print(f"INFO (S1): Unused plan ID {unused_plan_id} not found, but controller reported failure: {delete_message_s1}")
    else:
        print(f"FAILURE (S1): Unused plan ID {unused_plan_id} still found after deletion attempt.")

    # --- Scenario 2: Attempt to delete used plan ---
    print("\n--- Scenario 2: Attempt to Delete Used Plan ---")
    plan_name_used = f"SimDelPlan_Used_{int(time.time())%1000}"
    print(f"Step 2.1: Adding a plan to be used: Name='{plan_name_used}', Duration=30 days")
    used_plan_id = database_manager.add_plan(plan_name_used, 30, is_active=True)
    if used_plan_id is None:
        print(f"FAILURE (S2): Could not add plan '{plan_name_used}' for use.")
        cleanup_simulation_environment()
        return
    print(f"Plan to be used added successfully. ID: {used_plan_id}")

    # Add a member and a transaction that uses this plan
    member_name = f"PlanUser_{int(time.time())%1000}"
    member_phone = f"PU{int(time.time())%100000}"
    print(f"\nStep 2.2: Adding member '{member_name}' and transaction using plan ID {used_plan_id}")
    if not database_manager.add_member_to_db(member_name, member_phone):
        print(f"FAILURE (S2): Could not add member '{member_name}'.")
        cleanup_simulation_environment()
        return
    member_id_s2 = database_manager.get_all_members(phone_filter=member_phone)[0][0]

    tx_details_s2 = {
        'transaction_type': 'Group Class', 'member_id': member_id_s2, 'plan_id': used_plan_id,
        'payment_date': datetime.now().strftime('%Y-%m-%d'),
        'start_date': datetime.now().strftime('%Y-%m-%d'),
        'amount_paid': 70.00, 'payment_method': "SimUsedPlan"
    }
    if not database_manager.add_transaction(**tx_details_s2):
        print(f"FAILURE (S2): Could not add transaction using plan ID {used_plan_id}.")
        cleanup_simulation_environment()
        return
    print(f"Member and transaction using plan ID {used_plan_id} added.")

    print(f"\nStep 2.3: Calling controller.delete_plan_action for used plan ID {used_plan_id}")
    delete_success_s2, delete_message_s2 = controller.delete_plan_action(used_plan_id)
    print(f"Controller action message (S2): '{delete_message_s2}' (Success: {delete_success_s2})")

    print("\nStep 2.4: Verifying used plan is NOT deleted...")
    plans_after_delete_s2 = database_manager.get_all_plans_with_inactive()
    plan_found_s2 = any(p[0] == used_plan_id for p in plans_after_delete_s2)

    expected_message_s2 = "Plan is in use and cannot be deleted." # From database_manager
    if plan_found_s2 and not delete_success_s2 and delete_message_s2 == expected_message_s2:
        print(f"SUCCESS (S2): Used plan ID {used_plan_id} was NOT deleted, and correct message received.")
    elif not plan_found_s2:
        print(f"FAILURE (S2): Used plan ID {used_plan_id} WAS DELETED, but it shouldn't have been.")
    elif delete_success_s2:
        print(f"FAILURE (S2): Controller reported success deleting a used plan ID {used_plan_id}.")
    elif delete_message_s2 != expected_message_s2:
        print(f"FAILURE (S2): Incorrect message for used plan. Expected '{expected_message_s2}', got '{delete_message_s2}'.")
    else:
        print(f"INFO (S2): Used plan ID {used_plan_id} status check inconclusive.")


    print("\n--- Simulation: Delete Plan Flow Complete ---")
    cleanup_simulation_environment()

if __name__ == "__main__":
    main()

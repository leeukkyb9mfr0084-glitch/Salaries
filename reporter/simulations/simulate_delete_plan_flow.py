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
# Standard sim data directory
SIM_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
# Using a specific DB file for this simulation to avoid conflicts if run in parallel or if one fails.
SIM_DB_FILE = os.path.join(SIM_DB_DIR, "simulation_kranos_data_delete_plan.db")

# original_db_file is captured in __main__ block

def main_simulation_logic(): # Renamed main to main_simulation_logic
    controller = GuiController()
    print("\n--- Starting Simulation: Delete Plan Flow ---")

    # --- Scenario 1: Delete unused plan ---
    print("\n--- Scenario 1: Delete Unused Plan ---")
    plan_name_unused = f"SimDelPlan_Unused_{int(time.time())%1000}"
    print(f"Step 1.1: Adding an unused plan: Name='{plan_name_unused}', Duration=10 days")

    # Add plan using database_manager directly for more control in simulation script
    # controller.save_plan_action might be interactive or return different things.
    # For simulation, direct db calls for setup are often clearer.
    add_unused_success, _, unused_plan_id_val = database_manager.add_plan(plan_name_unused, 10, is_active=True)
    if not add_unused_success or unused_plan_id_val is None:
        print(f"FAILURE (S1): Could not add unused plan '{plan_name_unused}'.")
        # cleanup_simulation_environment() # cleanup is in finally block of main
        return
    print(f"Unused plan added successfully. ID: {unused_plan_id_val}")

    print(f"\nStep 1.2: Calling controller.delete_plan_action for unused plan ID {unused_plan_id_val}")
    # Based on test_gui_flows.py, controller.delete_plan_action for an unused plan
    # (which calls database_manager.delete_plan) does not use askyesno.
    delete_success_s1, delete_message_s1 = controller.delete_plan_action(unused_plan_id_val)
    print(f"Controller action message (S1): '{delete_message_s1}' (Success: {delete_success_s1})")

    print("\nStep 1.3: Verifying unused plan is deleted...")
    plans_after_delete_s1 = database_manager.get_all_plans_with_inactive()
    plan_found_s1 = any(p[0] == unused_plan_id_val for p in plans_after_delete_s1)
    if not plan_found_s1 and delete_success_s1:
        print(f"SUCCESS (S1): Unused plan ID {unused_plan_id_val} correctly deleted.")
    elif not plan_found_s1 and not delete_success_s1:
        print(f"INFO (S1): Unused plan ID {unused_plan_id_val} not found, but controller reported failure: {delete_message_s1}")
    else:
        print(f"FAILURE (S1): Unused plan ID {unused_plan_id_val} still found after deletion attempt.")

    # --- Scenario 2: Attempt to delete used plan ---
    print("\n--- Scenario 2: Attempt to Delete Used Plan ---")
    plan_name_used = f"SimDelPlan_Used_{int(time.time())%1000}"
    print(f"Step 2.1: Adding a plan to be used: Name='{plan_name_used}', Duration=30 days")
    add_used_success, _, used_plan_id_val = database_manager.add_plan(plan_name_used, 30, is_active=True)
    if not add_used_success or used_plan_id_val is None:
        print(f"FAILURE (S2): Could not add plan '{plan_name_used}' for use.")
        # cleanup_simulation_environment()
        return
    print(f"Plan to be used added successfully. ID: {used_plan_id_val}")

    # Add a member and a transaction that uses this plan
    member_name = f"PlanUser_{int(time.time())%1000}"
    member_phone = f"PU{int(time.time())%100000}"
    print(f"\nStep 2.2: Adding member '{member_name}' and transaction using plan ID {used_plan_id_val}")
    add_member_success, _ = database_manager.add_member_to_db(member_name, member_phone)
    if not add_member_success:
        print(f"FAILURE (S2): Could not add member '{member_name}'.")
        # cleanup_simulation_environment()
        return
    member_id_s2 = database_manager.get_all_members(phone_filter=member_phone)[0][0]

    tx_details_s2 = {
        'transaction_type': 'Group Class', 'member_id': member_id_s2, 'plan_id': used_plan_id_val,
        'payment_date': datetime.now().strftime('%Y-%m-%d'),
        'start_date': datetime.now().strftime('%Y-%m-%d'),
        'amount_paid': 70.00, 'payment_method': "SimUsedPlan"
    }
    add_tx_success, _ = database_manager.add_transaction(**tx_details_s2)
    if not add_tx_success:
        print(f"FAILURE (S2): Could not add transaction using plan ID {used_plan_id_val}.")
        # cleanup_simulation_environment()
        return
    print(f"Member and transaction using plan ID {used_plan_id_val} added.")

    print(f"\nStep 2.3: Calling controller.delete_plan_action for used plan ID {used_plan_id_val}")
    delete_success_s2, delete_message_s2 = controller.delete_plan_action(used_plan_id_val)
    print(f"Controller action message (S2): '{delete_message_s2}' (Success: {delete_success_s2})")

    print("\nStep 2.4: Verifying used plan is NOT deleted...")
    plans_after_delete_s2 = database_manager.get_all_plans_with_inactive()
    plan_found_s2 = any(p[0] == used_plan_id_val for p in plans_after_delete_s2)

    expected_message_s2 = "Plan is in use and cannot be deleted." # From database_manager
    if plan_found_s2 and not delete_success_s2 and delete_message_s2 == expected_message_s2:
        print(f"SUCCESS (S2): Used plan ID {used_plan_id_val} was NOT deleted, and correct message received.")
    elif not plan_found_s2:
        print(f"FAILURE (S2): Used plan ID {used_plan_id_val} WAS DELETED, but it shouldn't have been.")
    elif delete_success_s2:
        print(f"FAILURE (S2): Controller reported success deleting a used plan ID {used_plan_id_val}.")
    elif delete_message_s2 != expected_message_s2:
        print(f"FAILURE (S2): Incorrect message for used plan. Expected '{expected_message_s2}', got '{delete_message_s2}'.")
    else:
        print(f"INFO (S2): Used plan ID {used_plan_id_val} status check inconclusive.")


    print("\n--- Simulation: Delete Plan Flow Complete ---")
    # Cleanup is handled in the __main__ block's finally clause

def cleanup_simulation_environment():
    # This function is not strictly needed if the main script's finally block handles DB restoration.
    # However, if there were other resources, they could be cleaned here.
    # For now, it's a placeholder or can be removed if main's finally is sufficient.
    pass

if __name__ == "__main__":
    original_db_manager_db_file = database_manager.DB_FILE # Store original

    try:
        print(f"--- Main: Setting up simulation DB: {SIM_DB_FILE} ---")
        os.makedirs(SIM_DB_DIR, exist_ok=True)
        if os.path.exists(SIM_DB_FILE):
            os.remove(SIM_DB_FILE)
            print(f"Deleted existing simulation DB: {SIM_DB_FILE}")

        database_manager.DB_FILE = SIM_DB_FILE # Monkeypatch

        # Create and seed the fresh database
        # create_database handles its own connection opening/closing for file DBs
        create_database(db_name=SIM_DB_FILE)

        # Reopen to seed plans
        import sqlite3 # Ensure sqlite3 is imported for direct connection
        seed_conn = None
        try:
            seed_conn = sqlite3.connect(SIM_DB_FILE)
            seed_initial_plans(seed_conn)
            seed_conn.commit()
            print(f"Recreated and seeded simulation DB: {SIM_DB_FILE}")
        except Exception as e_seed:
            print(f"Error seeding simulation DB {SIM_DB_FILE}: {e_seed}", file=sys.stderr)
            raise # Re-raise if seeding fails, as it's critical for this sim
        finally:
            if seed_conn:
                seed_conn.close()

        # Run the actual simulation logic
        main_simulation_logic()

    except Exception as e_outer:
        print(f"--- SIMULATION SCRIPT ERROR: {e_outer} ---", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1) # Indicate script error
    finally:
        # Restore the original DB_FILE in database_manager
        database_manager.DB_FILE = original_db_manager_db_file
        print(f"--- Main: Restored database_manager.DB_FILE to: {original_db_manager_db_file} ---")

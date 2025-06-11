import sys
import os
from datetime import datetime, timedelta, date # Added date for today()
import time

# Adjust PYTHONPATH to include the project root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from reporter import database_manager
    from reporter.gui import GuiController # Import GuiController
    from reporter.database import create_database, seed_initial_plans # For DB setup
    import sqlite3 # For seeding
except ModuleNotFoundError as e:
    print(f"CRITICAL ERROR: Could not import necessary modules: {e}")
    sys.exit(1)

# --- Simulation Config ---
SIM_DB_DIR = os.path.join(os.path.dirname(__file__), "sim_data")
SIM_DB_FILE = os.path.join(SIM_DB_DIR, "simulation_kranos_data_add_gm.db") # Specific DB for this sim

# --- Helper to find member by name or add ---
def get_member_by_name_or_add(controller: GuiController, name_to_find: str, new_phone_if_adding: str) -> int | None:
    members = controller.db_manager.get_all_members(name_filter=name_to_find)
    if members:
        for member in members:
            if member[1] == name_to_find:
                print(f"Prerequisite: Found existing member '{name_to_find}' with ID {member[0]}.")
                return member[0]

    print(f"Prerequisite: Member '{name_to_find}' not found. Adding new one.")
    success, message = controller.save_member_action(name_to_find, new_phone_if_adding)
    print(f"Prerequisite controller (add member) message: {message}")
    if success:
        members_after_add = controller.db_manager.get_all_members(phone_filter=new_phone_if_adding)
        if members_after_add:
            print(f"Prerequisite: Added and using new member '{name_to_find}' with ID {members_after_add[0][0]}.")
            return members_after_add[0][0]
    print(f"CRITICAL PREREQUISITE FAILURE: Could not find or add member '{name_to_find}'. Controller success: {success}, message: {message}")
    return None # Explicitly return None on failure

# --- Helper to find plan by name or add ---
def get_plan_by_name_or_add(controller: GuiController, name_to_find: str, duration_if_adding: int) -> int | None:
    all_plans = controller.db_manager.get_all_plans_with_inactive()
    for plan_data in all_plans: # Renamed plan to plan_data to avoid conflict with date object
        if plan_data[1] == name_to_find:
            plan_id = plan_data[0]
            print(f"Prerequisite: Found existing plan '{name_to_find}' with ID {plan_id}.")
            if not plan_data[3]: # if not is_active
                print(f"Prerequisite: Plan '{name_to_find}' (ID {plan_id}) is inactive. Activating.")
                # Toggle status action returns (success, message, updated_plans_list)
                toggle_success, toggle_message, _ = controller.toggle_plan_status_action(plan_id=plan_id, current_status=False)
                print(f"Prerequisite controller (activate plan) message: {toggle_message}")
                if not toggle_success:
                    print(f"CRITICAL PREREQUISITE FAILURE: Could not activate plan '{name_to_find}'.")
                    return None
            return plan_id

    print(f"Prerequisite: Plan '{name_to_find}' not found. Adding new one.")
    # save_plan_action returns (success, message, updated_plans_list)
    add_success, add_message, _ = controller.save_plan_action(
        plan_name=name_to_find, duration_str=str(duration_if_adding), plan_id_to_update=""
    )
    print(f"Prerequisite controller (add plan) message: {add_message}")
    if add_success:
        # Query again to get the ID, as save_plan_action doesn't return it directly
        # This assumes the plan name is unique.
        plans_after_add = controller.db_manager.get_all_plans_with_inactive()
        for new_plan_data in plans_after_add:
            if new_plan_data[1] == name_to_find:
                print(f"Prerequisite: Added and using new plan '{name_to_find}' with ID {new_plan_data[0]}.")
                return new_plan_data[0]
    print(f"CRITICAL PREREQUISITE FAILURE: Could not find or add plan '{name_to_find}'. Controller success: {add_success}, message: {add_message}")
    return None


def main_simulation_logic(controller: GuiController): # controller is now passed in
    print("--- Setting up Prerequisites ---")
    gm_test_member_phone = f"112233{int(time.time()) % 10000:04d}"
    member_id_for_test = get_member_by_name_or_add(controller, "UI Test User Valid GM", gm_test_member_phone)
    if not member_id_for_test:
         print("Fallback for member failed. Exiting simulation.")
         sys.exit(1)

    plan_id_for_test = get_plan_by_name_or_add(controller, "Test Auto Plan GM", 30)
    if not plan_id_for_test:
        print("Fallback for plan failed. Exiting simulation.")
        sys.exit(1)

    # Fetch plan duration for end_date calculation
    current_plans = controller.db_manager.get_all_plans_with_inactive()
    plan_duration_days = 30 # default
    for p_data in current_plans: # Renamed p to p_data
        if p_data[0] == plan_id_for_test:
            plan_duration_days = p_data[2]
            break

    today_obj = date.today() # Use date.today()
    today_str = today_obj.strftime('%Y-%m-%d')
    expected_end_date_obj = today_obj + timedelta(days=plan_duration_days)
    expected_end_date_str = expected_end_date_obj.strftime('%Y-%m-%d')

    print("\n--- Part 1: Valid Group Membership Data Simulation ---")
    valid_amount_str = "100.0"
    valid_payment_method = "Cash UI Sim GM"

    print(f"Attempting to add valid GM: MemberID={member_id_for_test}, PlanID={plan_id_for_test}, PayDate='{today_str}', StartDate='{today_str}', Amount='{valid_amount_str}', Method='{valid_payment_method}'")

    try:
        success, message = controller.save_membership_action(
            membership_type="Group Class",
            member_id=member_id_for_test,
            selected_plan_id=plan_id_for_test,
            payment_date_str=today_str,
            start_date_str=today_str,
            amount_paid_str=valid_amount_str,
            payment_method=valid_payment_method,
            sessions_str=None
        )
        print(f"Controller action message: {message}")

        if success:
            print("SUCCESS (Part 1): controller.save_membership_action returned success.")
            activities = controller.db_manager.get_all_activity_for_member(member_id_for_test)
            verified = False
            if activities:
                for activity in activities:
                    if (activity[0] == "Group Class" and
                        activity[2] == today_str and
                        activity[3] == today_str and
                        activity[4] == expected_end_date_str and
                        activity[5] == float(valid_amount_str) and # Compare float
                        activity[6] == valid_payment_method):
                        # Assuming activity[1] (plan name) is correctly populated by get_all_activity_for_member
                        print(f"SUCCESS (Part 1): Verified GM in member activity - TransID: {activity[7]}, Plan Name: {activity[1]}, Details: {activity}")
                        verified = True
                        break
            if not verified:
                print(f"FAILURE (Part 1): GM transaction not found or details mismatch for MemberID {member_id_for_test}.")
                print(f"Expected end date: {expected_end_date_str}. Activities found: {activities}")
        else:
            print(f"FAILURE (Part 1): controller.save_membership_action returned failure.")
    except Exception as e:
        print(f"ERROR (Part 1): An exception occurred: {e}")


    print("\n--- Part 2: Invalid Group Membership Data Simulation (Non-Positive Amount) ---")
    invalid_amount_str = "0.0"
    print(f"Attempting GM with non-positive amount: Amount='{invalid_amount_str}'")

    try:
        success, message = controller.save_membership_action(
            membership_type="Group Class",
            member_id=member_id_for_test,
            selected_plan_id=plan_id_for_test,
            payment_date_str=today_str,
            start_date_str=today_str,
            amount_paid_str=invalid_amount_str,
            payment_method=valid_payment_method,
            sessions_str=None
        )
        print(f"Controller action message: {message}")
        if not success:
            print("SUCCESS (Part 2): controller.save_membership_action correctly prevented GM with non-positive amount.")
            if "cannot be negative" in message or "must be a positive number" in message : # Adjust if controller message is different
                 print("SUCCESS (Part 2): Correct error message received.")
            else:
                 print(f"WARNING (Part 2): Operation failed as expected, but message was: '{message}'")
        else:
            print("FAILURE (Part 2): controller.save_membership_action did NOT prevent GM with non-positive amount.")
    except Exception as e:
        print(f"ERROR (Part 2): An exception occurred: {e}")

if __name__ == '__main__':
    original_db_file_path = database_manager.DB_FILE # Save original DB path
    db_connection = None # Initialize db_connection

    try:
        print(f"--- Main: Setting up simulation DB: {SIM_DB_FILE} ---")
        os.makedirs(SIM_DB_DIR, exist_ok=True)
        if os.path.exists(SIM_DB_FILE):
            os.remove(SIM_DB_FILE)
            print(f"Deleted existing simulation DB: {SIM_DB_FILE}")

        # Patch DB_FILE for the duration of the simulation
        # This might be redundant if GuiController and its components strictly use the passed connection.
        # However, other direct calls to database_manager functions in this script might still rely on it.
        database_manager.DB_FILE = SIM_DB_FILE

        # Create the database tables
        create_database(db_name=SIM_DB_FILE)

        # Seed initial plans using a direct connection for seeding
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

        # Run the actual simulation logic
        main_simulation_logic(controller)

    except Exception as e_outer:
        print(f"--- SIMULATION SCRIPT ERROR: {e_outer} ---", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1) # Indicate script error
    finally:
        if db_connection: # Close the main connection
            db_connection.close()
            print(f"Closed main DB connection to {SIM_DB_FILE}")
        # Restore DB_FILE path (if it was globally patched and still relevant)
        database_manager.DB_FILE = original_db_file_path
        print(f"--- Main: Restored DB_FILE to: {database_manager.DB_FILE} ---")

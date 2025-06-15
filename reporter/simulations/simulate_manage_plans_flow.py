import sys
import os
import time

# Adjust PYTHONPATH to include the project root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

try:
    from reporter import database_manager
    from reporter.gui import GuiController  # Import GuiController
except ModuleNotFoundError as e:
    print(f"CRITICAL ERROR: Could not import necessary modules: {e}")
    sys.exit(1)

# Define project_root globally for use in SIM_DB_DIR
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# --- Simulation Database Setup ---
SIM_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
SIM_DB_FILE = os.path.join(SIM_DB_DIR, "simulation_kranos_data_manage_plans.db")


def find_plan_in_list_by_id(plans_list, plan_id_to_find):
    if plans_list:
        for (
            plan
        ) in plans_list:  # plan format: (plan_id, plan_name, duration_days, is_active)
            if plan[0] == plan_id_to_find:
                return plan
    return None


def find_plan_in_list_by_name(plans_list, plan_name_to_find):
    if plans_list:
        for plan in plans_list:
            if plan[1] == plan_name_to_find:
                return plan
    return None


def main_simulation_logic(controller: GuiController):  # controller is now passed in
    # controller = GuiController() # Instantiate controller
    unique_suffix = f"{int(time.time()) % 10000:04d}"
    test_plan_id = None

    # --- Part 1: Add New Plan (Valid Data) ---
    print("--- Part 1: Add New Plan (Valid Data) ---")
    plan_name_part1 = f"UI Ctrl Gold Plan {unique_suffix}"
    duration_part1_str = "30"
    print(
        f"Attempting to add valid plan: Name='{plan_name_part1}', Duration={duration_part1_str} days"
    )

    try:
        success, message, returned_plans = controller.save_plan_action(
            plan_name=plan_name_part1,
            duration_str=duration_part1_str,
            plan_id_to_update="",
        )
        print(f"Controller action message: {message}")
        if success:
            print(f"SUCCESS (Part 1): controller.save_plan_action returned success.")
            added_plan_from_list = find_plan_in_list_by_name(
                returned_plans, plan_name_part1
            )
            if added_plan_from_list:
                test_plan_id = added_plan_from_list[0]  # Get ID
                print(
                    f"SUCCESS (Part 1): Verified plan in returned list. ID: {test_plan_id}, Details: {added_plan_from_list}"
                )
                if not (
                    added_plan_from_list[2] == int(duration_part1_str)
                    and added_plan_from_list[3] == 1
                ):  # is_active should be True (1)
                    print(
                        f"FAILURE (Part 1): Details mismatch in returned plan. Expected Duration={duration_part1_str}, Active=True."
                    )
            else:
                print(
                    f"FAILURE (Part 1): Added plan '{plan_name_part1}' not found in list returned by controller."
                )
                # As a fallback, query DB directly if needed, though controller should be source of truth
                all_db_plans = controller.db_manager.get_all_plans_with_inactive()
                db_plan = find_plan_in_list_by_name(all_db_plans, plan_name_part1)
                if db_plan:
                    test_plan_id = db_plan[0]
                    print(
                        f"INFO (Part 1): Found plan in DB direct query. ID: {test_plan_id}. This implies inconsistency with controller's return."
                    )
                else:
                    print(f"FAILURE (Part 1): Plan also not found in direct DB query.")
        else:
            print(f"FAILURE (Part 1): controller.save_plan_action returned failure.")
    except Exception as e:
        print(f"ERROR (Part 1): An exception occurred: {e}")
        test_plan_id = None

    # --- Part 2: Edit Plan (Valid Data) ---
    print("\n--- Part 2: Edit Plan (Valid Data) ---")
    if test_plan_id:
        new_name_part2 = f"UI Ctrl Gold Updated {unique_suffix}"
        new_duration_part2_str = "35"
        print(
            f"Attempting to edit Plan ID {test_plan_id}: New Name='{new_name_part2}', New Duration={new_duration_part2_str} days"
        )

        try:
            success, message, returned_plans = controller.save_plan_action(
                plan_name=new_name_part2,
                duration_str=new_duration_part2_str,
                plan_id_to_update=str(test_plan_id),
            )
            print(f"Controller action message: {message}")
            if success:
                print(
                    f"SUCCESS (Part 2): controller.save_plan_action (for update) returned success for Plan ID {test_plan_id}."
                )
                edited_plan = find_plan_in_list_by_id(returned_plans, test_plan_id)
                if (
                    edited_plan
                    and edited_plan[1] == new_name_part2
                    and edited_plan[2] == int(new_duration_part2_str)
                ):
                    print(
                        f"SUCCESS (Part 2): Verified plan update in returned list. Details: {edited_plan}"
                    )
                else:
                    print(
                        f"FAILURE (Part 2): Verification failed for update in returned list. Found: {edited_plan}."
                    )
            else:
                print(
                    f"FAILURE (Part 2): controller.save_plan_action (for update) returned failure for Plan ID {test_plan_id}."
                )
        except Exception as e:
            print(f"ERROR (Part 2): An exception occurred during update: {e}")
    else:
        print(
            "SKIPPED (Part 2): Cannot edit plan because test_plan_id was not set in Part 1."
        )

    # --- Part 3: Deactivate Plan ---
    print("\n--- Part 3: Deactivate Plan ---")
    if test_plan_id:
        print(f"Attempting to deactivate Plan ID {test_plan_id}")
        try:
            # The method now determines current_status internally
            success, message, returned_plans = controller.toggle_plan_status_action(
                plan_id=test_plan_id
            )
            print(f"Controller action message: {message}")
            if success:
                print(
                    f"SUCCESS (Part 3): controller.toggle_plan_status_action returned success for Plan ID {test_plan_id}."
                )
                deactivated_plan = find_plan_in_list_by_id(returned_plans, test_plan_id)
                if (
                    deactivated_plan and deactivated_plan[3] == 0
                ):  # is_active should be False (0)
                    print(
                        f"SUCCESS (Part 3): Verified plan deactivation in returned list. is_active={deactivated_plan[3]}. Details: {deactivated_plan}"
                    )
                else:
                    print(
                        f"FAILURE (Part 3): Verification failed for deactivation in returned list. Found: {deactivated_plan}. Expected is_active=False."
                    )
            else:
                print(
                    f"FAILURE (Part 3): controller.toggle_plan_status_action returned failure for Plan ID {test_plan_id}."
                )
        except Exception as e:
            print(f"ERROR (Part 3): An exception occurred during deactivation: {e}")
    else:
        print(
            "SKIPPED (Part 3): Cannot deactivate plan because test_plan_id was not set."
        )

    # --- Part 4: Add New Plan (Invalid Data - Empty Name) ---
    print("\n--- Part 4: Add New Plan (Invalid Data - Empty Name) ---")
    empty_plan_name = ""
    valid_duration_part4_str = "30"
    print(
        f"Attempting to add plan with empty name: Name='{empty_plan_name}', Duration={valid_duration_part4_str} days"
    )
    try:
        success, message, _ = controller.save_plan_action(
            plan_name=empty_plan_name,
            duration_str=valid_duration_part4_str,
            plan_id_to_update="",
        )
        print(f"Controller action message: {message}")
        if not success:
            print(
                "SUCCESS (Part 4): controller.save_plan_action correctly prevented adding plan with empty name."
            )
            if "cannot be empty" in message:
                print("SUCCESS (Part 4): Correct error message received.")
            else:
                print(
                    f"WARNING (Part 4): Operation failed as expected, but message was: '{message}'"
                )
        else:
            print(
                "FAILURE (Part 4): controller.save_plan_action did NOT prevent adding plan with empty name."
            )
    except Exception as e:
        print(f"ERROR (Part 4): An exception occurred: {e}")

    # --- Part 5: Add New Plan (Invalid Data - Non-positive Duration) ---
    print("\n--- Part 5: Add New Plan (Invalid Data - Non-positive Duration) ---")
    valid_plan_name_part5 = f"UI Ctrl Invalid Duration Plan {unique_suffix}"
    invalid_duration_part5_str = "0"
    print(
        f"Attempting to add plan with non-positive duration: Name='{valid_plan_name_part5}', Duration={invalid_duration_part5_str} days"
    )
    try:
        success, message, _ = controller.save_plan_action(
            plan_name=valid_plan_name_part5,
            duration_str=invalid_duration_part5_str,
            plan_id_to_update="",
        )
        print(f"Controller action message: {message}")
        if not success:
            print(
                "SUCCESS (Part 5): controller.save_plan_action correctly prevented adding plan with non-positive duration."
            )
            if "must be a positive integer" in message:
                print("SUCCESS (Part 5): Correct error message received.")
            else:
                print(
                    f"WARNING (Part 5): Operation failed as expected, but message was: '{message}'"
                )
        else:
            print(
                "FAILURE (Part 5): controller.save_plan_action did NOT prevent adding plan with non-positive duration."
            )
    except Exception as e:
        print(f"ERROR (Part 5): An exception occurred: {e}")


if __name__ == "__main__":
    original_db_manager_db_file = database_manager.DB_FILE
    from reporter.database import create_database, seed_initial_plans
    import sqlite3

    db_connection = None  # Initialize

    try:
        print(f"--- Main: Setting up simulation DB: {SIM_DB_FILE} ---")
        os.makedirs(SIM_DB_DIR, exist_ok=True)
        if os.path.exists(SIM_DB_FILE):
            os.remove(SIM_DB_FILE)
            print(f"Deleted existing simulation DB: {SIM_DB_FILE}")

        database_manager.DB_FILE = SIM_DB_FILE  # Monkeypatch

        create_database(db_name=SIM_DB_FILE)

        seed_conn = None
        try:
            seed_conn = sqlite3.connect(SIM_DB_FILE)
            seed_initial_plans(seed_conn)
            seed_conn.commit()
            print(f"Recreated and seeded simulation DB: {SIM_DB_FILE}")
        except Exception as e_seed:
            print(
                f"Error seeding simulation DB {SIM_DB_FILE}: {e_seed}", file=sys.stderr
            )
            raise
        finally:
            if seed_conn:
                seed_conn.close()

        db_connection = sqlite3.connect(
            SIM_DB_FILE, check_same_thread=False
        )  # Create connection
        controller = GuiController(db_connection)  # Pass connection

        main_simulation_logic(controller)  # Pass controller

    except Exception as e_outer:
        print(f"--- SIMULATION SCRIPT ERROR: {e_outer} ---", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        if db_connection:  # Close connection
            db_connection.close()
            print(f"Closed main DB connection to {SIM_DB_FILE}")
        database_manager.DB_FILE = original_db_manager_db_file
        print(
            f"--- Main: Restored database_manager.DB_FILE to: {original_db_manager_db_file} ---"
        )

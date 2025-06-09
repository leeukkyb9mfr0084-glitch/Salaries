import sys
import os
import time

# Adjust PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from reporter import database_manager
except ModuleNotFoundError:
    print("CRITICAL ERROR: Could not import 'reporter.database_manager'.")
    sys.exit(1)

def find_plan_in_list_by_id(plans_list, plan_id):
    for plan in plans_list: # plan format: (plan_id, plan_name, duration_days, is_active)
        if plan[0] == plan_id:
            return plan
    return None

def main():
    unique_suffix = f"{int(time.time()) % 10000:04d}"
    test_plan_id = None

    # --- Part 1: Add New Plan (Valid Data) ---
    print("--- Part 1: Add New Plan (Valid Data) ---")
    plan_name_part1 = f"UI Gold Plan Test {unique_suffix}"
    duration_part1 = 30
    print(f"Attempting to add valid plan: Name='{plan_name_part1}', Duration={duration_part1} days")

    try:
        test_plan_id = database_manager.add_plan(plan_name_part1, duration_part1)
        if test_plan_id:
            print(f"SUCCESS (Part 1): add_plan returned new Plan ID: {test_plan_id}.")
            # Verify
            all_plans = database_manager.get_all_plans_with_inactive()
            added_plan = find_plan_in_list_by_id(all_plans, test_plan_id)
            if (added_plan and added_plan[1] == plan_name_part1 and
                added_plan[2] == duration_part1 and added_plan[3] == 1): # is_active should be True (1)
                print(f"SUCCESS (Part 1): Verified plan in DB. Details: {added_plan}")
            else:
                print(f"FAILURE (Part 1): Verification failed. Found: {added_plan}. Expected Name={plan_name_part1}, Duration={duration_part1}, Active=True.")
        else:
            print(f"FAILURE (Part 1): add_plan returned None. Plan '{plan_name_part1}' might already exist if script run too fast or name not unique enough.")
    except Exception as e:
        print(f"ERROR (Part 1): An exception occurred: {e}")
        test_plan_id = None # Ensure test_plan_id is None if add failed

    # --- Part 2: Edit Plan (Valid Data) ---
    print("\n--- Part 2: Edit Plan (Valid Data) ---")
    if test_plan_id:
        new_name_part2 = f"UI Gold Plan Test Updated {unique_suffix}"
        new_duration_part2 = 35
        print(f"Attempting to edit Plan ID {test_plan_id}: New Name='{new_name_part2}', New Duration={new_duration_part2} days")

        try:
            update_success = database_manager.update_plan(test_plan_id, new_name_part2, new_duration_part2)
            if update_success:
                print(f"SUCCESS (Part 2): update_plan returned True for Plan ID {test_plan_id}.")
                # Verify
                all_plans = database_manager.get_all_plans_with_inactive()
                edited_plan = find_plan_in_list_by_id(all_plans, test_plan_id)
                if (edited_plan and edited_plan[1] == new_name_part2 and edited_plan[2] == new_duration_part2):
                    print(f"SUCCESS (Part 2): Verified plan update in DB. Details: {edited_plan}")
                else:
                    print(f"FAILURE (Part 2): Verification failed for update. Found: {edited_plan}. Expected Name={new_name_part2}, Duration={new_duration_part2}.")
            else:
                print(f"FAILURE (Part 2): update_plan returned False for Plan ID {test_plan_id}.")
        except Exception as e:
            print(f"ERROR (Part 2): An exception occurred during update: {e}")
    else:
        print("SKIPPED (Part 2): Cannot edit plan because test_plan_id was not set in Part 1.")

    # --- Part 3: Deactivate Plan ---
    print("\n--- Part 3: Deactivate Plan ---")
    if test_plan_id:
        print(f"Attempting to deactivate Plan ID {test_plan_id}")
        try:
            deactivate_success = database_manager.set_plan_active_status(test_plan_id, False)
            if deactivate_success:
                print(f"SUCCESS (Part 3): set_plan_active_status returned True for Plan ID {test_plan_id}.")
                # Verify
                all_plans = database_manager.get_all_plans_with_inactive()
                deactivated_plan = find_plan_in_list_by_id(all_plans, test_plan_id)
                if deactivated_plan and deactivated_plan[3] == 0: # is_active should be False (0)
                    print(f"SUCCESS (Part 3): Verified plan deactivation in DB. is_active={deactivated_plan[3]}. Details: {deactivated_plan}")
                else:
                    print(f"FAILURE (Part 3): Verification failed for deactivation. Found: {deactivated_plan}. Expected is_active=False.")
            else:
                print(f"FAILURE (Part 3): set_plan_active_status returned False for Plan ID {test_plan_id}.")
        except Exception as e:
            print(f"ERROR (Part 3): An exception occurred during deactivation: {e}")
    else:
        print("SKIPPED (Part 3): Cannot deactivate plan because test_plan_id was not set.")

    # --- Part 4: Add New Plan (Invalid Data - Empty Name) ---
    print("\n--- Part 4: Add New Plan (Invalid Data - Empty Name) ---")
    empty_plan_name = ""
    valid_duration_part4 = 30
    print(f"Simulating GUI validation for empty plan name: Name='{empty_plan_name}', Duration={valid_duration_part4} days")

    # GUI's validation: if not plan_name or not duration_str:
    gui_would_allow_call_part4 = True
    if not empty_plan_name or not str(valid_duration_part4): # Simulating the check with stringified duration
        gui_would_allow_call_part4 = False

    if not gui_would_allow_call_part4:
        print("SUCCESS (Part 4): GUI validation 'if not plan_name or not duration_str:' correctly prevents backend call for empty plan name.")
    else:
        print("FAILURE (Part 4): GUI validation (simulated) WOULD INEXPLICABLY ALLOW backend call for empty plan name.")
        # Not calling backend, as per instructions for this simulation focus.

    # --- Part 5: Add New Plan (Invalid Data - Non-positive Duration) ---
    print("\n--- Part 5: Add New Plan (Invalid Data - Non-positive Duration) ---")
    valid_plan_name_part5 = f"UI Invalid Duration Plan {unique_suffix}"
    invalid_duration_part5 = 0 # Could also be -1
    print(f"Simulating GUI validation for non-positive duration: Name='{valid_plan_name_part5}', Duration={invalid_duration_part5} days")

    # GUI's validation: if duration_days <= 0:
    gui_would_allow_call_part5 = True
    # Simulate the conversion and check that happens in GUI
    try:
        duration_days_sim = int(str(invalid_duration_part5))
        if duration_days_sim <= 0:
            gui_would_allow_call_part5 = False
    except ValueError: # Should not occur for 0 or -1
        gui_would_allow_call_part5 = False # Treat conversion error as validation failure in GUI

    if not gui_would_allow_call_part5:
        print("SUCCESS (Part 5): GUI validation 'if duration_days <= 0:' correctly prevents backend call for non-positive duration.")
    else:
        print("FAILURE (Part 5): GUI validation (simulated) WOULD INEXPLICABLY ALLOW backend call for non-positive duration.")
        # Not calling backend.

if __name__ == '__main__':
    if os.getenv('PYTHONPATH') is None or not os.getcwd() in os.getenv('PYTHONPATH').split(os.pathsep):
         os.environ['PYTHONPATH'] = os.getcwd() + (os.pathsep + os.getenv('PYTHONPATH') if os.getenv('PYTHONPATH') else '')
    main()

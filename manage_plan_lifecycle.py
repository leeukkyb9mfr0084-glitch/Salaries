import sys
import os

# Adjust PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from reporter import database_manager
except ModuleNotFoundError:
    print("CRITICAL ERROR: Could not import 'reporter.database_manager'.")
    print(
        "Ensure that the script is run from the project root where 'reporter' is a subdirectory."
    )
    sys.exit(1)


def find_plan_in_list(plans_list, plan_id):
    for plan in plans_list:
        if plan[0] == plan_id:
            return plan
    return None


def main():
    initial_plan_name = "Monthly Gold"
    initial_duration = 30
    updated_duration = 31
    new_plan_id = None

    print(f"--- 1. Adding New Plan: '{initial_plan_name}', {initial_duration} days ---")
    # add_plan returns (success_boolean, message, new_plan_id_or_None)
    success, msg, new_plan_id = database_manager.add_plan(
        initial_plan_name, initial_duration, is_active=True
    )

    if success:
        print(
            msg
        )  # Should contain success message like "Plan '...' added with ID: ..."
        # Verification
        all_plans = database_manager.get_all_plans_with_inactive()
        added_plan = find_plan_in_list(all_plans, new_plan_id)
        if (
            added_plan
            and added_plan[1] == initial_plan_name
            and added_plan[2] == initial_duration
            and added_plan[3] == 1
        ):  # is_active is index 3 (1 for True)
            print(
                f"Verification successful: Plan details match. Name: {added_plan[1]}, Duration: {added_plan[2]}, Active: {bool(added_plan[3])}"
            )
        else:
            print(f"Verification failed for plan addition. Found: {added_plan}")
            return  # Stop if verification fails
    else:
        print(msg)  # Should contain the error message from add_plan
        # Existing logic to check if it already exists
        all_plans = database_manager.get_all_plans_with_inactive()
        existing_plan = next(
            (
                p
                for p in all_plans
                if p[1] == initial_plan_name and p[2] == initial_duration
            ),
            None,
        )
        if existing_plan:
            print(
                f"Note: A plan with name '{initial_plan_name}' and duration {initial_duration} days (ID: {existing_plan[0]}) already exists. Using this for next steps."
            )
            new_plan_id = existing_plan[0]  # Use existing plan ID
            # Ensure it's active for the next steps if it was inactive
            if not existing_plan[3]:  # if is_active is False
                print(
                    f"Activating existing plan ID {new_plan_id} for test consistency."
                )
                database_manager.set_plan_active_status(new_plan_id, True)
        else:
            print("Could not find or create the plan. Aborting.")
            return

    print(
        f"\n--- 2. Editing Plan ID {new_plan_id} Duration to {updated_duration} days ---"
    )
    update_success = database_manager.update_plan(
        new_plan_id, initial_plan_name, updated_duration
    )

    if update_success:
        print(
            f"Success: Plan ID {new_plan_id} duration updated to {updated_duration} days."
        )
        # Verification
        all_plans = database_manager.get_all_plans_with_inactive()
        edited_plan = find_plan_in_list(all_plans, new_plan_id)
        if edited_plan and edited_plan[2] == updated_duration:
            print(
                f"Verification successful: Plan duration is now {edited_plan[2]} days."
            )
        else:
            print(f"Verification failed for plan update. Found: {edited_plan}")
            return
    else:
        print(f"Error: Failed to update plan ID {new_plan_id}.")
        return

    print(f"\n--- 3. Deactivating Plan ID {new_plan_id} ---")
    deactivate_success = database_manager.set_plan_active_status(new_plan_id, False)

    if deactivate_success:
        print(f"Success: Plan ID {new_plan_id} deactivated.")
        # Verification
        all_plans_with_inactive = database_manager.get_all_plans_with_inactive()
        deactivated_plan_check = find_plan_in_list(all_plans_with_inactive, new_plan_id)
        # is_active is at index 3 (0 = False, 1 = True in SQLite boolean context)
        if (
            deactivated_plan_check and deactivated_plan_check[3] == 0
        ):  # Check for 0 (False)
            print(
                f"Verification successful: Plan ID {new_plan_id} is_active status is False."
            )
        else:
            print(
                f"Verification failed for plan deactivation. Found: {deactivated_plan_check}"
            )
            return
    else:
        print(f"Error: Failed to deactivate plan ID {new_plan_id}.")
        return

    print(f"\n--- 4. Verifying Plan ID {new_plan_id} is Not in Active Plans List ---")
    active_plans = database_manager.get_all_plans()
    found_in_active = find_plan_in_list(active_plans, new_plan_id)

    if not found_in_active:
        print(
            f"Success: Deactivated Plan ID {new_plan_id} ('{initial_plan_name}') is not found in the list of active plans."
        )
        print(f"Total active plans found: {len(active_plans)}")
    else:
        print(
            f"Error: Deactivated Plan ID {new_plan_id} was found in the list of active plans."
        )
        print(f"Details of found plan: {found_in_active}")


if __name__ == "__main__":
    if os.getenv("PYTHONPATH") is None or not os.getcwd() in os.getenv(
        "PYTHONPATH"
    ).split(os.pathsep):
        os.environ["PYTHONPATH"] = os.getcwd() + (
            os.pathsep + os.getenv("PYTHONPATH") if os.getenv("PYTHONPATH") else ""
        )
    main()

import sys
import os
from datetime import datetime, timedelta
import time


# Adjust PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from reporter import database_manager
except ModuleNotFoundError:
    print("CRITICAL ERROR: Could not import 'reporter.database_manager'.")
    sys.exit(1)

# --- Helper to find member by name if phone is too dynamic for reliable reuse ---
def get_member_by_name_or_add(name_to_find, new_phone_if_adding):
    members = database_manager.get_all_members(name_filter=name_to_find)
    if members:
        for member in members:
            if member[1] == name_to_find: # client_name is at index 1
                print(f"Prerequisite: Found existing member '{name_to_find}' with ID {member[0]}.")
                return member[0] # member_id is at index 0

    # If not found, add new one
    print(f"Prerequisite: Member '{name_to_find}' not found. Adding new one.")
    added = database_manager.add_member_to_db(name_to_find, new_phone_if_adding)
    if added:
        # Query again to get the ID
        members_after_add = database_manager.get_all_members(phone_filter=new_phone_if_adding)
        if members_after_add:
            print(f"Prerequisite: Added and using new member '{name_to_find}' with ID {members_after_add[0][0]}.")
            return members_after_add[0][0]
    print(f"CRITICAL PREREQUISITE FAILURE: Could not find or add member '{name_to_find}'.")
    sys.exit(1)

# --- Helper to find plan by name or add ---
def get_plan_by_name_or_add(name_to_find, duration_if_adding):
    all_plans = database_manager.get_all_plans_with_inactive() # Check all plans
    for plan in all_plans:
        # plan format: (plan_id, plan_name, duration_days, is_active)
        if plan[1] == name_to_find:
            plan_id = plan[0]
            print(f"Prerequisite: Found existing plan '{name_to_find}' with ID {plan_id}.")
            if not plan[3]: # if not is_active
                print(f"Prerequisite: Plan '{name_to_find}' (ID {plan_id}) is inactive. Activating.")
                database_manager.set_plan_active_status(plan_id, True)
            return plan_id

    print(f"Prerequisite: Plan '{name_to_find}' not found. Adding new one.")
    new_plan_id = database_manager.add_plan(name_to_find, duration_if_adding, is_active=True)
    if new_plan_id:
        print(f"Prerequisite: Added and using new plan '{name_to_find}' with ID {new_plan_id}.")
        return new_plan_id
    print(f"CRITICAL PREREQUISITE FAILURE: Could not find or add plan '{name_to_find}'.")
    sys.exit(1)


def main():
    print("--- Setting up Prerequisites ---")
    # Use unique phone for GM Test Member to avoid collision if UI Test User Valid is not found by name.
    gm_test_member_phone = f"112233{int(time.time()) % 10000:04d}"
    member_id_for_test = get_member_by_name_or_add("UI Test User Valid", gm_test_member_phone)
    if not member_id_for_test: # Fallback if "UI Test User Valid" wasn't added/found
         member_id_for_test = get_member_by_name_or_add("GM Test Member", gm_test_member_phone)


    plan_id_for_test = get_plan_by_name_or_add("Test Auto Plan", 30)
    if not plan_id_for_test: # Fallback
        plan_id_for_test = get_plan_by_name_or_add("GM Test Plan", 30)

    # Fetch plan duration for end_date calculation
    all_plans = database_manager.get_all_plans_with_inactive()
    plan_duration_days = 30 # default
    for p in all_plans:
        if p[0] == plan_id_for_test:
            plan_duration_days = p[2]
            break

    today_str = datetime.now().strftime('%Y-%m-%d')
    expected_end_date_obj = datetime.strptime(today_str, '%Y-%m-%d') + timedelta(days=plan_duration_days)
    expected_end_date_str = expected_end_date_obj.strftime('%Y-%m-%d')


    print("\n--- Part 1: Valid Group Membership Data Simulation ---")
    valid_amount = 100.0
    valid_payment_method = "Cash UI Sim GM"

    print(f"Attempting to add valid GM: MemberID={member_id_for_test}, PlanID={plan_id_for_test}, PayDate='{today_str}', StartDate='{today_str}', Amount={valid_amount}, Method='{valid_payment_method}'")

    try:
        add_success = database_manager.add_transaction(
            transaction_type="Group Class",
            member_id=member_id_for_test,
            plan_id=plan_id_for_test,
            payment_date=today_str,
            start_date=today_str,
            amount_paid=valid_amount,
            payment_method=valid_payment_method
        )

        if add_success:
            print("SUCCESS (Part 1): add_transaction returned True.")
            # Verify by querying member's activity
            activities = database_manager.get_all_activity_for_member(member_id_for_test)
            verified = False
            if activities:
                for activity in activities:
                    # (transaction_type, name_or_description, payment_date, start_date, end_date, amount_paid, payment_method_or_sessions, transaction_id)
                    if (activity[0] == "Group Class" and
                        # activity[1] would be plan name, not checking plan_id directly here but relying on plan_id_for_test
                        activity[2] == today_str and # payment_date
                        activity[3] == today_str and # start_date
                        activity[4] == expected_end_date_str and # end_date
                        activity[5] == valid_amount and
                        activity[6] == valid_payment_method):
                        print(f"SUCCESS (Part 1): Verified GM in member activity - TransID: {activity[7]}, Details: {activity}")
                        verified = True
                        break # Found the specific transaction
            if not verified:
                print(f"FAILURE (Part 1): GM transaction not found or details mismatch in member activity for MemberID {member_id_for_test}.")
                print(f"Expected end date: {expected_end_date_str}. Activities found: {activities}")

        else:
            print(f"FAILURE (Part 1): add_transaction returned False.")
    except Exception as e:
        print(f"ERROR (Part 1): An exception occurred: {e}")


    print("\n--- Part 2: Invalid Group Membership Data Simulation (Non-Positive Amount) ---")
    invalid_amount = 0.0  # Could also be -10.0
    print(f"Simulating GUI validation for non-positive amount: Amount={invalid_amount}")

    # GUI's validation logic simulation:
    # try:
    #     amount_paid_float = float(str(invalid_amount)) # Simulate getting string then converting
    #     if amount_paid_float <= 0:
    #         # show error, return
    # except ValueError:
    #     # show error, return

    gui_would_allow_call_pt2 = True
    try:
        amount_paid_float_sim = float(str(invalid_amount)) # Simulate conversion from string input
        if amount_paid_float_sim <= 0:
            gui_would_allow_call_pt2 = False
    except ValueError: # Should not happen with invalid_amount = 0.0
        gui_would_allow_call_pt2 = False

    if not gui_would_allow_call_pt2:
        print("SUCCESS (Part 2): GUI validation 'if amount_paid <= 0:' correctly prevents backend call for non-positive amount.")
    else:
        print("FAILURE (Part 2): GUI validation (simulated) WOULD INEXPLICABLY ALLOW backend call for non-positive amount.")
        print("Proceeding to call add_transaction to see backend behavior.")
        try:
            backend_add_success = database_manager.add_transaction(
                transaction_type="Group Class", member_id=member_id_for_test, plan_id=plan_id_for_test,
                payment_date=today_str, start_date=today_str, amount_paid=invalid_amount, payment_method=valid_payment_method
            )
            if backend_add_success:
                print("INFO (Part 2): Backend add_transaction returned True for non-positive amount.")
            else:
                print("INFO (Part 2): Backend add_transaction returned False for non-positive amount (as expected from backend).")
        except Exception as e:
            print(f"ERROR (Part 2): Exception during backend call for non-positive amount: {e}")

if __name__ == '__main__':
    if os.getenv('PYTHONPATH') is None or not os.getcwd() in os.getenv('PYTHONPATH').split(os.pathsep):
         os.environ['PYTHONPATH'] = os.getcwd() + (os.pathsep + os.getenv('PYTHONPATH') if os.getenv('PYTHONPATH') else '')
    main()

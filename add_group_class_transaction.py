import sys
import os
from datetime import datetime, timedelta

# Adjust PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from reporter import database_manager
except ModuleNotFoundError:
    print("CRITICAL ERROR: Could not import 'reporter.database_manager'.")
    print("Ensure that the script is run from the project root where 'reporter' is a subdirectory.")
    sys.exit(1)

def main():
    member_id_to_use = 7 # Assuming 'Test User Script' with ID 7 exists
    plan_name = "Test Auto Plan"
    plan_duration_days = 30
    transaction_amount = 50.0
    payment_method = "Cash"
    today_date_str = datetime.now().strftime('%Y-%m-%d')

    print(f"--- Ensuring Plan '{plan_name}' Exists ---")
    plans = database_manager.get_all_plans() # Get active plans
    target_plan_id = None

    # Check if a plan with the same name and duration already exists
    # Note: get_all_plans only returns active plans. If we want to reuse an inactive one, logic needs adjustment.
    # For this script, we'll prefer an existing active plan or create a new one.
    existing_plans_with_name = [p for p in plans if p[1] == plan_name and p[2] == plan_duration_days]

    if existing_plans_with_name:
        target_plan_id = existing_plans_with_name[0][0] # Use the first match
        print(f"Using existing active plan: ID {target_plan_id}, Name: {existing_plans_with_name[0][1]}, Duration: {existing_plans_with_name[0][2]} days.")
    else:
        print(f"No existing active plan named '{plan_name}' with {plan_duration_days} days duration found. Attempting to add new plan.")
        # Check all plans (including inactive) to see if an identical inactive one exists
        all_plans_incl_inactive = database_manager.get_all_plans_with_inactive()
        identical_inactive_plan = next((p for p in all_plans_incl_inactive if p[1] == plan_name and p[2] == plan_duration_days and not p[3]), None)

        if identical_inactive_plan:
            target_plan_id = identical_inactive_plan[0]
            print(f"Found identical inactive plan: ID {target_plan_id}. Activating and using it.")
            activated = database_manager.set_plan_active_status(target_plan_id, True)
            if not activated:
                print(f"Error: Could not activate plan ID {target_plan_id}. Cannot proceed.")
                return
        else:
            print(f"Creating new plan: Name: {plan_name}, Duration: {plan_duration_days} days.")
            success, msg, target_plan_id = database_manager.add_plan(plan_name, plan_duration_days, is_active=True)
            if success:
                print(msg) # Should contain success message like "New plan created successfully: ID ..."
                # The message from add_plan already includes details, so we might not need the line below or can simplify it.
                # For now, let's assume msg is comprehensive.
                # print(f"New plan created successfully: ID {target_plan_id}, Name: {plan_name}, Duration: {plan_duration_days} days.")
            else:
                print(msg) # Should contain the error message
                print(f"Error: Could not create new plan '{plan_name}'. Cannot proceed.")
                return

    if not target_plan_id:
        print("Error: Failed to secure a plan_id. Aborting transaction.")
        return

    print(f"\n--- Adding 'Group Class' Transaction for Member ID {member_id_to_use} ---")
    print(f"Plan ID to be used: {target_plan_id}")
    print(f"Payment Date: {today_date_str}, Start Date: {today_date_str}")
    print(f"Amount: {transaction_amount}, Method: {payment_method}")

    transaction_success = database_manager.add_transaction(
        transaction_type='Group Class',
        member_id=member_id_to_use,
        plan_id=target_plan_id,
        start_date=today_date_str,
        amount_paid=transaction_amount,
        payment_method=payment_method,
        payment_date=today_date_str # Explicitly setting payment_date
    )

    if transaction_success:
        print("Transaction added successfully.")
    else:
        print("Error: Failed to add transaction.")
        # Attempt to find member to confirm they exist
        member_check = database_manager.get_all_members(phone_filter=None) # Get all to find by ID
        found_member_for_id_check = any(m[0] == member_id_to_use for m in member_check)
        if not found_member_for_id_check:
            print(f"Potential issue: Member with ID {member_id_to_use} might not exist.")
        return # Stop if transaction failed

    print(f"\n--- Verifying Transaction for Member ID {member_id_to_use} ---")
    activities = database_manager.get_all_activity_for_member(member_id_to_use)

    if not activities:
        print("Error: No activities found for member after adding transaction.")
        return

    # Calculate expected end date
    start_date_obj = datetime.strptime(today_date_str, '%Y-%m-%d')
    expected_end_date_obj = start_date_obj + timedelta(days=plan_duration_days)
    expected_end_date_str = expected_end_date_obj.strftime('%Y-%m-%d')

    verified = False
    print("Found activities:")
    for activity in activities:
        # activity format: (transaction_type, name_or_description, payment_date, start_date, end_date, amount_paid, payment_method_or_sessions, transaction_id)
        print(f"  - {activity}")
        if (activity[0] == 'Group Class' and
            activity[1] == plan_name and # Plan name used as name_or_description
            activity[2] == today_date_str and # payment_date
            activity[3] == today_date_str and # start_date
            activity[4] == expected_end_date_str and # end_date
            activity[5] == transaction_amount and
            activity[6] == payment_method):
            print(f"\nSuccessfully verified: Found matching 'Group Class' transaction (ID: {activity[7]})")
            print(f"  Details: Type='{activity[0]}', Plan='{activity[1]}', PaymentDate='{activity[2]}', Start='{activity[3]}', End='{activity[4]}', Amount='{activity[5]}', Method='{activity[6]}'")
            verified = True
            break # Found the transaction

    if not verified:
        print("\nVerification Failed: Did not find the exact 'Group Class' transaction in member's activity.")
        print(f"Expected: Type='Group Class', Plan='{plan_name}', PaymentDate='{today_date_str}', Start='{today_date_str}', End='{expected_end_date_str}', Amount='{transaction_amount}', Method='{payment_method}'")

if __name__ == '__main__':
    if os.getenv('PYTHONPATH') is None or not os.getcwd() in os.getenv('PYTHONPATH').split(os.pathsep):
         os.environ['PYTHONPATH'] = os.getcwd() + (os.pathsep + os.getenv('PYTHONPATH') if os.getenv('PYTHONPATH') else '')
    main()

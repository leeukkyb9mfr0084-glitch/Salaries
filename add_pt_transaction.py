import sys
import os
from datetime import datetime

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


def main():
    member_id_to_use = 7  # Assuming 'Test User Script' with ID 7 exists
    sessions_count = 10
    transaction_amount = 200.0
    today_date_str = datetime.now().strftime("%Y-%m-%d")

    print(
        f"--- Adding 'Personal Training' Transaction for Member ID {member_id_to_use} ---"
    )
    print(f"Start Date (and Payment Date): {today_date_str}")
    print(f"Sessions: {sessions_count}, Amount Paid: {transaction_amount}")

    transaction_success = database_manager.add_transaction(
        transaction_type="Personal Training",
        member_id=member_id_to_use,
        start_date=today_date_str,  # payment_date will default to start_date
        amount_paid=transaction_amount,
        sessions=sessions_count,
        # No plan_id for PT, payment_method is optional
    )

    if transaction_success:
        print("Personal Training transaction added successfully.")
    else:
        print("Error: Failed to add Personal Training transaction.")
        # Attempt to find member to confirm they exist
        member_check = database_manager.get_all_members(phone_filter=None)
        found_member_for_id_check = any(m[0] == member_id_to_use for m in member_check)
        if not found_member_for_id_check:
            print(
                f"Potential issue: Member with ID {member_id_to_use} might not exist."
            )
        return  # Stop if transaction failed

    print(f"\n--- Verifying Transaction for Member ID {member_id_to_use} ---")
    activities = database_manager.get_all_activity_for_member(member_id_to_use)

    if not activities:
        print("Error: No activities found for member after adding PT transaction.")
        return

    verified = False
    print("Found activities:")
    expected_payment_method_or_sessions_str = f"{sessions_count} sessions"

    for activity in activities:
        # activity format: (transaction_type, name_or_description, payment_date, start_date, end_date, amount_paid, payment_method_or_sessions, transaction_id)
        print(f"  - {activity}")
        if (
            activity[0] == "Personal Training"
            and
            # activity[1] for PT is 'PT Session'
            activity[2] == today_date_str  # payment_date
            and activity[3] == today_date_str  # start_date
            and activity[4] is None  # end_date is None for PT
            and activity[5] == transaction_amount
            and activity[6] == expected_payment_method_or_sessions_str
        ):  # sessions
            print(
                f"\nSuccessfully verified: Found matching 'Personal Training' transaction (ID: {activity[7]})"
            )
            print(
                f"  Details: Type='{activity[0]}', Name='{activity[1]}', PaymentDate='{activity[2]}', Start='{activity[3]}', EndDate='{activity[4]}', Amount='{activity[5]}', Sessions='{activity[6]}'"
            )
            verified = True
            break  # Found the transaction

    if not verified:
        print(
            "\nVerification Failed: Did not find the exact 'Personal Training' transaction in member's activity."
        )
        print(
            f"Expected: Type='Personal Training', PaymentDate='{today_date_str}', Start='{today_date_str}', EndDate=None, Amount='{transaction_amount}', Sessions='{expected_payment_method_or_sessions_str}'"
        )


if __name__ == "__main__":
    if os.getenv("PYTHONPATH") is None or not os.getcwd() in os.getenv(
        "PYTHONPATH"
    ).split(os.pathsep):
        os.environ["PYTHONPATH"] = os.getcwd() + (
            os.pathsep + os.getenv("PYTHONPATH") if os.getenv("PYTHONPATH") else ""
        )
    main()

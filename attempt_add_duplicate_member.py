import sys
import os
from datetime import datetime

# Adjust PYTHONPATH to include the 'reporter' module directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from reporter import database_manager
except ModuleNotFoundError:
    print("CRITICAL ERROR: Could not import 'reporter.database_manager'.")
    print(
        "Ensure that the script is run from the project root where 'reporter' is a subdirectory."
    )
    print(
        "PYTHONPATH might need to be set: export PYTHONPATH=/path/to/your/project/root"
    )
    sys.exit(1)


def main():
    # This phone number should already exist from the previous task
    duplicate_phone = "0000000000"
    member_name = "Duplicate Test User"
    join_date = datetime.now().strftime("%Y-%m-%d")

    print(
        f"Attempting to add member: {member_name} with existing phone: {duplicate_phone}"
    )

    # Attempt to add member with a duplicate phone number
    # The add_member_to_db function is expected to return False and print an error
    add_success = database_manager.add_member_to_db(
        member_name, duplicate_phone, join_date
    )

    if not add_success:
        print(
            f"Successfully prevented adding member with duplicate phone '{duplicate_phone}'."
        )
        print("The 'add_member_to_db' function returned False as expected.")

        # Optional: Verify that no new member with this name was added,
        # and the original member with that phone number is still the only one.
        members_with_phone = database_manager.get_all_members(
            phone_filter=duplicate_phone
        )
        count = 0
        original_member_name = ""
        for member in members_with_phone:
            if member[2] == duplicate_phone:  # phone is at index 2
                count += 1
                original_member_name = member[1]  # client_name is at index 1

        if count == 1:
            print(
                f"Verification: Still exactly one member with phone '{duplicate_phone}' (Name: '{original_member_name}'). No duplicate was added."
            )
        else:
            print(
                f"Verification ERROR: Found {count} members with phone '{duplicate_phone}'. Expected 1."
            )
            for member in members_with_phone:
                print(f"  - Found: {member}")

    else:
        print(
            f"ERROR: Member '{member_name}' with duplicate phone '{duplicate_phone}' was INCORRECTLY added to the database."
        )
        # Query to see what was added
        members = database_manager.get_all_members(phone_filter=duplicate_phone)
        print("Current members with this phone number:")
        for member in members:
            print(member)


if __name__ == "__main__":
    if os.getenv("PYTHONPATH") is None or not os.getcwd() in os.getenv(
        "PYTHONPATH"
    ).split(os.pathsep):
        os.environ["PYTHONPATH"] = os.getcwd() + (
            os.pathsep + os.getenv("PYTHONPATH") if os.getenv("PYTHONPATH") else ""
        )
    main()

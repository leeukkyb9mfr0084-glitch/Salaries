import sys
import os
from datetime import datetime

# Adjust PYTHONPATH to include the 'reporter' module directory
# This assumes the script is run from the root of the project where 'reporter' is a subdirectory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from reporter import database_manager
except ModuleNotFoundError:
    print("Error: Could not import 'reporter.database_manager'.")
    print("Ensure that the script is run from the project root and PYTHONPATH is set correctly if needed.")
    print("If reporter is not in the current directory, you might need to run: export PYTHONPATH=/path/to/your/project/root")
    sys.exit(1)


def main():
    member_name = "Test User Script"
    member_phone = "0000000000" # Unique phone number
    join_date = datetime.now().strftime('%Y-%m-%d')

    print(f"Attempting to add member: {member_name}, Phone: {member_phone}, Join Date: {join_date}")

    # Add member
    add_success = database_manager.add_member_to_db(member_name, member_phone, join_date)

    if add_success:
        print(f"Member '{member_name}' added successfully.")

        # Verify by querying
        print(f"Verifying member by phone: {member_phone}")
        # Use get_all_members with a phone filter to verify
        members = database_manager.get_all_members(phone_filter=member_phone)

        if members:
            verified = False
            for member in members:
                # member format is (member_id, client_name, phone, join_date)
                if member[1] == member_name and member[2] == member_phone:
                    print(f"Successfully verified: Member found - ID: {member[0]}, Name: {member[1]}, Phone: {member[2]}, Join Date: {member[3]}")
                    verified = True
                    break
            if not verified:
                print(f"Verification failed: Member with phone '{member_phone}' found, but details do not match.")
                print(f"Found members: {members}")
        else:
            print(f"Verification failed: Member with phone '{member_phone}' not found after add operation.")

    else:
        print(f"Failed to add member '{member_name}'. It might be due to an existing phone number or other database error.")
        # Attempt to query anyway, in case the error was misleading
        print(f"Checking if member '{member_name}' with phone '{member_phone}' already exists...")
        members = database_manager.get_all_members(phone_filter=member_phone)
        if members:
             for member in members:
                if member[1] == member_name and member[2] == member_phone:
                    print(f"Member '{member_name}' (Phone: {member_phone}) was already present in the database.")
                    break
        else:
            print(f"Member '{member_name}' (Phone: {member_phone}) was not found, confirming add operation failed and member does not exist.")


if __name__ == '__main__':
    # Ensure PYTHONPATH includes the project root for `reporter` module
    # This is another way to handle it directly in the script if not set externally
    if os.getenv('PYTHONPATH') is None or not os.getcwd() in os.getenv('PYTHONPATH').split(os.pathsep):
         os.environ['PYTHONPATH'] = os.getcwd() + (os.pathsep + os.getenv('PYTHONPATH') if os.getenv('PYTHONPATH') else '')
        # print(f"Temporarily set PYTHONPATH to: {os.environ['PYTHONPATH']}") # For debugging

    main()

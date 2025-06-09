import sys
import os

# Adjust PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from reporter import database_manager
except ModuleNotFoundError:
    print("CRITICAL ERROR: Could not import 'reporter.database_manager'.")
    print("Ensure that the script is run from the project root where 'reporter' is a subdirectory.")
    sys.exit(1)

def main():
    target_member_id = 7
    target_member_phone = "0000000000" # Phone for "Test User Script" (ID 7)
    target_member_name = "Test User Script"
    partial_name_search = "Test User"
    partial_phone_search = "0000000"

    print(f"--- 1. Fetching Details and Activity for Member ID {target_member_id} ('{target_member_name}') ---")

    # Fetch member details by their unique phone number
    member_details_list = database_manager.get_all_members(phone_filter=target_member_phone)
    found_target_member_details = False
    if member_details_list:
        for member in member_details_list:
            if member[0] == target_member_id and member[2] == target_member_phone:
                print(f"Member Details: ID={member[0]}, Name='{member[1]}', Phone='{member[2]}', JoinDate='{member[3]}'")
                found_target_member_details = True
                break
        if not found_target_member_details:
            print(f"Error: Member with ID {target_member_id} and Phone {target_member_phone} not found in list.")
    else:
        print(f"Error: No member found with phone filter '{target_member_phone}'. Expected to find '{target_member_name}'.")

    if not found_target_member_details:
        print(f"Could not definitively find member {target_member_id} to fetch activity. Aborting this step.")
    else:
        print(f"\nActivity History for Member ID {target_member_id} ('{target_member_name}'):")
        activities = database_manager.get_all_activity_for_member(target_member_id)
        if activities:
            for activity in activities:
                # (transaction_type, name_or_description, payment_date, start_date, end_date, amount_paid, payment_method_or_sessions, transaction_id)
                print(f"  - Type: {activity[0]}, Desc: {activity[1]}, Payment: {activity[2]}, Start: {activity[3]}, End: {activity[4]}, Amt: {activity[5]}, Method/Sessions: {activity[6]}, TransID: {activity[7]}")
            # We expect at least the two transactions from previous scripts
            if len(activities) >= 2:
                 print(f"Success: Fetched {len(activities)} activity records for member {target_member_id}.")
            else:
                 print(f"Warning: Fetched {len(activities)} activity records, expected at least 2.")

        else:
            print(f"No activity history found for member ID {target_member_id}. This might be an issue if transactions were expected.")

    print(f"\n--- 2. Searching Members by Partial Name: '{partial_name_search}' ---")
    members_by_name = database_manager.get_all_members(name_filter=partial_name_search)
    if members_by_name:
        print(f"Found {len(members_by_name)} member(s) matching partial name '{partial_name_search}':")
        expected_found_by_name = False
        for member in members_by_name:
            print(f"  - ID={member[0]}, Name='{member[1]}', Phone='{member[2]}', JoinDate='{member[3]}'")
            if target_member_name in member[1]: # Check if our main test user is among them
                expected_found_by_name = True
        if expected_found_by_name:
            print(f"Success: Search by partial name '{partial_name_search}' included the expected member '{target_member_name}'.")
        else:
            print(f"Warning: Search by partial name '{partial_name_search}' did NOT include the expected member '{target_member_name}'.")
    else:
        print(f"No members found matching partial name '{partial_name_search}'.")

    print(f"\n--- 3. Searching Members by Partial Phone: '{partial_phone_search}' ---")
    members_by_phone = database_manager.get_all_members(phone_filter=partial_phone_search)
    if members_by_phone:
        print(f"Found {len(members_by_phone)} member(s) matching partial phone '{partial_phone_search}':")
        expected_found_by_phone = False
        for member in members_by_phone:
            print(f"  - ID={member[0]}, Name='{member[1]}', Phone='{member[2]}', JoinDate='{member[3]}'")
            if target_member_phone in member[2]: # Check if our main test user's phone is matched
                expected_found_by_phone = True
        if expected_found_by_phone:
            print(f"Success: Search by partial phone '{partial_phone_search}' included the expected member with phone '{target_member_phone}'.")
        else:
            print(f"Warning: Search by partial phone '{partial_phone_search}' did NOT include the expected member with phone '{target_member_phone}'.")

    else:
        print(f"No members found matching partial phone '{partial_phone_search}'.")


    print("\n--- 4. Fetching All Members (Simulating Filter Clear) ---")
    all_members = database_manager.get_all_members()
    if all_members:
        print(f"Success: Fetched all members. Total count: {len(all_members)}.")
        # We know at least 'Test User Script' (ID 7) and the members from migrate_data.py exist.
        # migrate_data.py adds: 'Error User Amount', 'Test User PT1', 'Test User PT3', and 3 from group class if dates valid.
        # Total from migration was 6. Plus 'Test User Script' is 7.
        if len(all_members) >= 7:
             print(f"Count {len(all_members)} is consistent with expectations (>=7).")
        else:
             print(f"Warning: Count {len(all_members)} is lower than expected (>=7).")
        # print("List of all members:")
        # for member in all_members:
        #     print(f"  - ID={member[0]}, Name='{member[1]}', Phone='{member[2]}', JoinDate='{member[3]}'")
    else:
        print("Error: Failed to fetch all members or database is empty.")

if __name__ == '__main__':
    if os.getenv('PYTHONPATH') is None or not os.getcwd() in os.getenv('PYTHONPATH').split(os.pathsep):
         os.environ['PYTHONPATH'] = os.getcwd() + (os.pathsep + os.getenv('PYTHONPATH') if os.getenv('PYTHONPATH') else '')
    main()

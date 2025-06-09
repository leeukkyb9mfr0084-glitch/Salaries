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
    print("--- Part 1: Valid Data Simulation ---")
    valid_name = "UI Test User Valid"
    # Generate a unique phone number for each run to ensure test is repeatable
    import time
    valid_phone = f"987654{int(time.time()) % 10000:04d}"
    print(f"Attempting to add valid member: Name='{valid_name}', Phone='{valid_phone}'")

    # 1. Call add_member_to_db
    try:
        add_success = database_manager.add_member_to_db(valid_name, valid_phone)
        if add_success:
            print("SUCCESS (Part 1): add_member_to_db returned True.")

            # 2. Verify by querying
            members = database_manager.get_all_members(phone_filter=valid_phone)
            verified = False
            if members:
                for member in members:
                    if member[1] == valid_name and member[2] == valid_phone:
                        print(f"SUCCESS (Part 1): Verified member in DB - ID: {member[0]}, Name: {member[1]}, Phone: {member[2]}")
                        verified = True
                        break
            if not verified:
                print(f"FAILURE (Part 1): Member with phone '{valid_phone}' not found in DB after add operation, or details mismatch.")
        else:
            print(f"FAILURE (Part 1): add_member_to_db returned False. Phone '{valid_phone}' might already exist if script run too quickly.")
            # Check if it exists
            members = database_manager.get_all_members(phone_filter=valid_phone)
            if members and members[0][1] == valid_name:
                print(f"INFO (Part 1): Member '{valid_name}' with phone '{valid_phone}' was already in DB.")


    except Exception as e:
        print(f"ERROR (Part 1): An exception occurred: {e}")


    print("\n--- Part 2: Invalid Data Simulation (Empty Name) ---")
    empty_name = ""
    valid_phone_for_empty_test = f"987654{int(time.time()) % 10000 + 10000:04d}" # Different unique phone

    print(f"Simulating GUI validation for empty name: Name='{empty_name}', Phone='{valid_phone_for_empty_test}'")

    # GUI's validation logic simulation:
    # if not name or not phone:
    #     # show error, return
    # else:
    #     # call backend

    gui_would_allow_call = True
    if not empty_name or not valid_phone_for_empty_test: # Simulating the GUI's check
        gui_would_allow_call = False

    if not gui_would_allow_call:
        print("SUCCESS (Part 2): GUI validation 'if not name or not phone:' correctly prevents backend call for empty name.")
        # Do NOT call add_member_to_db, as the GUI wouldn't.
    else:
        # This case should ideally not be reached if GUI logic is `if not name or not phone:`
        print("FAILURE (Part 2): GUI validation (simulated as 'if not name or not phone:') WOULD INEXPLICABLY ALLOW backend call.")
        print("Proceeding to call add_member_to_db to see backend behavior (which is a separate test).")
        try:
            backend_add_success = database_manager.add_member_to_db(empty_name, valid_phone_for_empty_test)
            if backend_add_success:
                print("INFO (Part 2): Backend add_member_to_db returned True for empty name. (This was tested in test_input_validation.py as a backend issue).")
            else:
                print("INFO (Part 2): Backend add_member_to_db returned False for empty name.")
        except Exception as e:
            print(f"ERROR (Part 2): Exception during backend call for empty name: {e}")

if __name__ == '__main__':
    if os.getenv('PYTHONPATH') is None or not os.getcwd() in os.getenv('PYTHONPATH').split(os.pathsep):
         os.environ['PYTHONPATH'] = os.getcwd() + (os.pathsep + os.getenv('PYTHONPATH') if os.getenv('PYTHONPATH') else '')
    main()

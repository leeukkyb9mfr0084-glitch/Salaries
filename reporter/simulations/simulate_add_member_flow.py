import sys
import os
import time # For unique phone numbers

# Adjust PYTHONPATH to include the project root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from reporter import database_manager
    from reporter.gui import GuiController # Import GuiController
except ModuleNotFoundError as e:
    print(f"CRITICAL ERROR: Could not import necessary modules: {e}")
    print("Ensure that the script is run from a context where 'reporter' is discoverable.")
    print("Make sure PYTHONPATH is set up correctly if running from outside the project root.")
    sys.exit(1)

def main():
    controller = GuiController() # Instantiate the controller

    print("--- Part 1: Valid Data Simulation ---")
    valid_name = "UI Ctrl Test User Valid"
    valid_phone = f"98765{int(time.time()) % 10000:05d}" # Ensure unique phone
    print(f"Attempting to add valid member: Name='{valid_name}', Phone='{valid_phone}'")

    try:
        success, message = controller.save_member_action(valid_name, valid_phone)
        print(f"Controller action message: {message}")

        if success:
            print("SUCCESS (Part 1): controller.save_member_action returned success.")
            # Verify by querying
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
            print(f"FAILURE (Part 1): controller.save_member_action returned failure. Message: {message}")
            # Optionally, check if it exists if failure was due to duplication (controller should indicate this)
            if "already exist" in message:
                 members = database_manager.get_all_members(phone_filter=valid_phone)
                 if members and members[0][1] == valid_name:
                    print(f"INFO (Part 1): Member '{valid_name}' with phone '{valid_phone}' was already in DB, as indicated by controller.")

    except Exception as e:
        print(f"ERROR (Part 1): An exception occurred: {e}")


    print("\n--- Part 2: Invalid Data Simulation (Empty Name) ---")
    empty_name = ""
    # Use a different unique phone to avoid collision with Part 1 if it failed mid-way or if DB is not clean
    valid_phone_for_empty_test = f"98764{int(time.time()) % 10000:05d}"

    print(f"Attempting to add member with empty name: Name='{empty_name}', Phone='{valid_phone_for_empty_test}'")

    try:
        success, message = controller.save_member_action(empty_name, valid_phone_for_empty_test)
        print(f"Controller action message: {message}")

        if not success:
            print("SUCCESS (Part 2): controller.save_member_action correctly prevented adding member with empty name.")
            if "cannot be empty" in message: # Check for expected error message
                print("SUCCESS (Part 2): Correct error message for empty name received.")
            else:
                print("WARNING (Part 2): Incorrect error message received for empty name, but operation still failed as expected.")
        else:
            # This case should ideally not be reached if controller validation is correct
            print("FAILURE (Part 2): controller.save_member_action did NOT prevent adding member with empty name.")
            # Verify if it was actually added to the DB (it shouldn't be)
            members = database_manager.get_all_members(phone_filter=valid_phone_for_empty_test)
            if members:
                print(f"FAILURE (Part 2): Member with empty name WAS FOUND in DB with phone '{valid_phone_for_empty_test}'.")
            else:
                print("INFO (Part 2): Member with empty name was not found in DB, but controller reported success, which is inconsistent.")

    except Exception as e:
        print(f"ERROR (Part 2): An exception occurred during invalid data simulation: {e}")

if __name__ == '__main__':
    # The sys.path.insert at the top of the script should handle module discovery.
    # The old PYTHONPATH manipulation here is removed as it might be incorrect after file move.
    main()

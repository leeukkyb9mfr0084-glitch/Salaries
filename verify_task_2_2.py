import os
from reporter.database_manager import DatabaseManager
from reporter.database import create_database, seed_initial_plans # Corrected imports

DB_FILE = "test_duplicate.db"
print("Running verification for Task 2.2...")
if os.path.exists(DB_FILE): os.remove(DB_FILE)

# Initialize a clean database for the test
conn = create_database(DB_FILE)
if not conn:
    print(f"FAILURE: Could not create database {DB_FILE}")
    exit()
# seed_initial_plans(conn) # Not strictly necessary for this test, but good practice if DB constraints depend on it
db_manager = DatabaseManager(connection=conn)

try:
    # Add first member successfully
    member_id1 = db_manager.add_member("First Member", "555-1234", "first@test.com")
    if member_id1 is None:
        print("FAILURE: Could not add the first member, prerequisite for the test.")
        conn.close()
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        exit()

    # Try to add a second member with the same phone number
    db_manager.add_member("Second Member", "555-1234", "second@test.com")
    # If add_member does not raise ValueError for a duplicate, this line will be reached
    print("FAILURE: ValueError was NOT raised for a duplicate phone number during add_member.")

except ValueError as e:
    print(f"SUCCESS: ValueError was correctly raised for a duplicate phone number: {e}")
except Exception as e:
    print(f"FAILURE: An unexpected error occurred: {e}")
finally:
    if conn:
        conn.close()
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

import os
import sqlite3
from reporter.database_manager import DatabaseManager
from reporter.database import create_database, seed_initial_plans # Import create_database and seed_initial_plans

DB_FILE = "test_renewal.db"
print("Running verification for Task 2.1...")
if os.path.exists(DB_FILE): os.remove(DB_FILE)

# Create a connection object using create_database
conn = create_database(DB_FILE) # This creates the db file and tables

if conn:
    seed_initial_plans(conn) # Seed initial plans into the test database
    db_manager = DatabaseManager(connection=conn) # Pass the connection

    # Use different phone numbers for adding members to avoid ValueError for duplicate phone
    # Removed status ("Active") from add_member calls
    member_id1 = db_manager.add_member("Test Member 1", "555-0101", "test1@test.com")
    plan_id1 = db_manager.add_group_plan("Test Plan 1", 100, 30) # Removed status ("Active")

    if member_id1 is None or plan_id1 is None:
        print("FAILURE: Could not create test member or plan.")
        if conn: conn.close()
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        exit()

    # The create_group_class_membership now requires amount_paid
    db_manager.create_group_class_membership(member_id1, plan_id1, "2025-06-16", amount_paid=100.0)
    db_manager.create_group_class_membership(member_id1, plan_id1, "2025-07-16", amount_paid=100.0)

    # Add another member and a membership for them to ensure the logic is per member
    member_id2 = db_manager.add_member("Test Member 2", "555-0102", "test2@test.com")
    plan_id2 = db_manager.add_group_plan("Test Plan 2", 120, 30)

    if member_id2 is None or plan_id2 is None:
        print("FAILURE: Could not create second test member or plan.")
        if conn: conn.close()
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        exit()

    db_manager.create_group_class_membership(member_id2, plan_id2, "2025-08-16", amount_paid=120.0)

    results_cursor = conn.cursor()
    results_cursor.execute("SELECT member_id, membership_type FROM group_class_memberships ORDER BY member_id, start_date")
    results = results_cursor.fetchall()
    conn.close()

    expected_results = [
        (member_id1, "New"),
        (member_id1, "Renewal"),
        (member_id2, "New")
    ]

    filtered_results = [res for res in results if res[0] in (member_id1, member_id2)]

    if filtered_results == expected_results:
        print("SUCCESS: Membership types are correctly assigned as 'New' then 'Renewal' for the first member, and 'New' for the second member.")
    else:
        print(f"FAILURE: Expected {expected_results}, but got {filtered_results}.")
else:
    print(f"FAILURE: Could not connect to or create database {DB_FILE}")

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

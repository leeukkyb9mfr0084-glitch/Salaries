import csv
import os
import sqlite3 # Import for specific error types

# Make sure the main database file is initialized
from reporter.database import create_database, DB_FILE

# Import the necessary functions from the database manager
from reporter.database_manager import (
    get_db_connection,
    get_member_by_phone,
    add_member_with_join_date,
    get_or_create_plan_id,
    add_group_membership_to_db,
    add_pt_booking
)

# --- IMPORTANT ---
# Update these paths to where your CSV files are located.
# For simplicity, you can place the CSV files in the root folder of your project.
GC_CSV_PATH = 'Kranos MMA Members.xlsx - GC.csv'
PT_CSV_PATH = 'Kranos MMA Members.xlsx - PT.csv'

def process_gc_data():
    """Reads the Group Class CSV and populates members and group_memberships tables."""
    print("\nProcessing Group Class data...")
    if not os.path.exists(GC_CSV_PATH):
        print(f"ERROR: GC data file not found at '{GC_CSV_PATH}'")
        return

    with open(GC_CSV_PATH, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            try:
                # Standardize data
                name = row['Client Name'].strip()
                phone = row['Phone'].strip()
                plan_start_date = row['Plan Start Date'].strip()

                if not name or not phone:
                    print(f"Skipping row due to missing name or phone: {row}")
                    continue

                # 1. Get or Create Member
                member_info = get_member_by_phone(phone)
                if member_info:
                    member_id = member_info[0]
                else:
                    # Use Plan Start Date as the join date for new members
                    member_id = add_member_with_join_date(name, phone, plan_start_date)
                    if member_id:
                        print(f"Created new member: {name}")
                    else: # Member might exist with different capitalization, fetch again
                         member_info = get_member_by_phone(phone)
                         if member_info:
                            member_id = member_info[0]
                         else:
                            print(f"Could not create or find member: {name} ({phone})")
                            continue


                # 2. Get or Create Plan
                plan_name = row['Plan Type'].strip()
                duration = int(row['Plan Duration'])
                plan_id = get_or_create_plan_id(plan_name, duration)

                if not plan_id:
                    print(f"Could not create or find plan for row: {row}")
                    continue

                # 3. Add Group Membership
                add_group_membership_to_db(
                    member_id=member_id,
                    plan_id=plan_id,
                    payment_date=row['Payment Date'].strip(),
                    start_date=plan_start_date,
                    amount_paid=float(row['Amount']),
                    payment_method=row['Payment Mode'].strip()
                )
            except (ValueError, KeyError) as e:
                print(f"Skipping row due to data error ('{e}'): {row}")
            except Exception as e:
                print(f"An unexpected error occurred on row {row}: {e}")

def process_pt_data():
    """Reads the Personal Training CSV and populates pt_bookings table."""
    print("\nProcessing Personal Training data...")
    if not os.path.exists(PT_CSV_PATH):
        print(f"ERROR: PT data file not found at '{PT_CSV_PATH}'")
        return

    with open(PT_CSV_PATH, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            try:
                name = row['Client Name'].strip()
                phone = row['Phone'].strip()
                start_date = row['Start Date'].strip()

                if not name or not phone:
                    continue

                # 1. Get or Create Member
                member_info = get_member_by_phone(phone)
                if member_info:
                    member_id = member_info[0]
                else:
                    member_id = add_member_with_join_date(name, phone, start_date)
                    if member_id:
                        print(f"Created new member from PT data: {name}")
                    else:
                        print(f"Could not create or find member from PT data: {name}")
                        continue

                # 2. Add PT Booking
                add_pt_booking(
                    member_id=member_id,
                    start_date=start_date,
                    sessions=int(row['Session Count']),
                    amount_paid=float(row['Amount Paid'])
                )
            except (ValueError, KeyError) as e:
                print(f"Skipping PT row due to data error ('{e}'): {row}")


if __name__ == '__main__':
    print("--- Starting Database Initialization ---")

    # Ensure the database and tables exist
    data_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    create_database(DB_FILE)

    # Process the data
    process_gc_data()
    process_pt_data()

    print("\n--- Database Initialization Complete ---")

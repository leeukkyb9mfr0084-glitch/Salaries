import csv
import os
import sqlite3
from datetime import datetime

# Make sure the main database file is initialized
from reporter.database import create_database
from reporter.database_manager import DB_FILE

# Import the necessary functions from the database manager
from reporter.database_manager import (
    get_member_by_phone,
    add_member_with_join_date,
    get_or_create_plan_id,
    add_transaction  # Updated import
)

GC_CSV_PATH = 'Kranos MMA Members.xlsx - GC.csv'
PT_CSV_PATH = 'Kranos MMA Members.xlsx - PT.csv'

def parse_date(date_str):
    """Parses DD/MM/YY or DD/MM/YYYY and returns YYYY-MM-DD format."""
    date_str = date_str.strip()
    # Handle YYYY format in the date (e.g., 03/03/2025)
    if len(date_str.split('/')[-1]) == 4:
        try:
            return datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
        except ValueError:
            pass
    # Handle YY format (e.g., 13/05/24)
    try:
        return datetime.strptime(date_str, '%d/%m/%y').strftime('%Y-%m-%d')
    except ValueError:
        print(f"Warning: Could not parse date '{date_str}' with known formats.")
        return None

def parse_amount(amount_str):
    """Removes currency symbols, commas, and whitespace, then converts to float."""
    try:
        # Remove currency symbols, commas, and strip whitespace
        cleaned_str = amount_str.replace('₹', '').replace(',', '').strip()
        if cleaned_str in ('-', ''):
            return 0.0
        return float(cleaned_str)
    except (ValueError, AttributeError):
        print(f"Warning: Could not parse amount '{amount_str}'.")
        return 0.0

def process_gc_data():
    """Reads the Group Class CSV and populates members and group_memberships tables."""
    print("\nProcessing Group Class data...")
    if not os.path.exists(GC_CSV_PATH):
        print(f"ERROR: GC data file not found at '{GC_CSV_PATH}'")
        return

    with open(GC_CSV_PATH, mode='r', encoding='utf-8-sig') as infile: # Use utf-8-sig to handle BOM
        reader = csv.reader(infile)
        # Read header and strip spaces from each column name
        header = [h.strip() for h in next(reader)]

        for row_list in reader:
            row = dict(zip(header, row_list))
            try:
                name = row.get('Client Name', '').strip()
                phone = row.get('Phone', '').strip()
                plan_start_date_raw = row.get('Plan Start Date', '').strip()
                payment_date_raw = row.get('Payment Date', '').strip()

                if not all([name, phone, plan_start_date_raw, payment_date_raw]):
                    print(f"Skipping row due to missing essential data: {row}")
                    continue

                plan_start_date = parse_date(plan_start_date_raw)
                payment_date = parse_date(payment_date_raw)

                if not plan_start_date or not payment_date:
                    print(f"Skipping row due to unparsable date: {row}")
                    continue

                member_info = get_member_by_phone(phone)
                if member_info:
                    member_id = member_info[0]
                else:
                    member_id = add_member_with_join_date(name, phone, plan_start_date)
                    if not member_id: # If creation failed (maybe due to case), try fetching again
                        member_info = get_member_by_phone(phone)
                        if member_info:
                            member_id = member_info[0]
                        else:
                            print(f"Could not create or find member: {name} ({phone})")
                            continue
                    else:
                        print(f"Created new member: {name}")

                plan_name = row['Plan Type'].strip()
                duration_months = int(row['Plan Duration'])
                # Assuming an average of 30 days per month for duration calculation
                duration_days = duration_months * 30
                plan_id = get_or_create_plan_id(plan_name, duration_days)

                if not plan_id:
                    print(f"Could not create or find plan for row: {row}")
                    continue

                amount = parse_amount(row['Amount'])

                add_transaction(
                    transaction_type="Group Class",
                    member_id=member_id,
                    plan_id=plan_id,
                    payment_date=payment_date,
                    start_date=plan_start_date,
                    amount_paid=amount,
                    payment_method=row.get('Payment Mode', '').strip(),
                    sessions=None
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

    with open(PT_CSV_PATH, mode='r', encoding='utf-8-sig') as infile:
        reader = csv.reader(infile)
        header = [h.strip() for h in next(reader)]

        for row_list in reader:
            row = dict(zip(header, row_list))
            try:
                name = row.get('Client Name', '').strip()
                phone = row.get('Phone', '').strip()
                start_date_raw = row.get('Start Date', '').strip()

                if not name or not phone or not start_date_raw:
                    continue

                start_date = parse_date(start_date_raw)
                if not start_date:
                    print(f"Skipping PT row due to unparsable date: {row}")
                    continue

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

                amount_paid = parse_amount(row.get('Amount Paid', '0'))
                sessions_count = int(row.get('Session Count', 0)) if row.get('Session Count') else 0


                add_transaction(
                    transaction_type="Personal Training",
                    member_id=member_id,
                    start_date=start_date,
                    amount_paid=amount_paid,
                    sessions=sessions_count,
                    plan_id=None,
                    payment_method=None, # PT bookings didn't have this before
                    payment_date=start_date # Explicitly set payment_date as start_date for PT
                )
            except (ValueError, KeyError) as e:
                print(f"Skipping PT row due to data error ('{e}'): {row}")

if __name__ == '__main__':
    print("--- Starting Database Migration ---")
    data_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    create_database(DB_FILE)
    process_gc_data()
    process_pt_data()
    print("\n--- Database Migration Complete ---")

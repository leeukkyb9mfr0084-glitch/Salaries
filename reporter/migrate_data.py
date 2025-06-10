import csv
import os
import sqlite3
from datetime import datetime, timedelta

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

# Determine the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct absolute paths to the CSV files
# Assuming CSVs are in 'reporter/data/csv/' and this script is in 'reporter/'
csv_dir = os.path.join(script_dir, 'data', 'csv')

# Use specific filenames as mentioned in the script, but now within csv_dir
GC_CSV_PATH = os.path.join(csv_dir, 'Kranos MMA Members.xlsx - GC.csv')
PT_CSV_PATH = os.path.join(csv_dir, 'Kranos MMA Members.xlsx - PT.csv')

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

    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        print("Clearing existing data from tables: transactions, members, plans")
        cursor.execute("DELETE FROM transactions;")
        cursor.execute("DELETE FROM members;")
        cursor.execute("DELETE FROM plans;")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('members', 'transactions', 'plans');")
        conn.commit()
        print("Data cleared successfully.")
    except sqlite3.Error as e:
        print(f"Database error during data clearing: {e}")
    finally:
        if conn:
            conn.close()

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
                payment_date_raw = row.get('Payment Date', '').strip()

                # New logic for start and end dates
                plan_start_date_str = row.get('Plan Start Date', '').strip()
                duration_days = 0
                try:
                    duration_days_str = row.get('Plan Duration', '0').strip()
                    if duration_days_str: # Ensure it's not empty before int conversion
                        duration_days = int(duration_days_str)
                except ValueError:
                    print(f"Warning: Could not parse Plan Duration '{row.get('Plan Duration', '')}' to int for row: {row}. Skipping.")
                    continue

                if not plan_start_date_str or duration_days <= 0:
                    print(f"Skipping row due to missing Plan Start Date or invalid/zero Plan Duration: {row}")
                    continue

                if not all([name, phone, payment_date_raw]):
                    print(f"Skipping row due to missing essential data (Name, Phone, or Payment Date): {row}")
                    continue

                payment_date = parse_date(payment_date_raw)
                if not payment_date: # Check essential payment_date
                    print(f"Skipping row due to unparsable Payment Date: {row}")
                    continue

                try:
                    # Convert plan_start_date_str to a datetime object:
                    # Assuming plan_start_date_str is in '%d/%m/%y' format as per issue context
                    # If it could be '%d/%m/%Y' as well, more robust parsing is needed here
                    # For now, sticking to the issue's direct implication.
                    start_dt = datetime.strptime(plan_start_date_str, '%d/%m/%y')
                except ValueError:
                    try:
                        # Fallback to '%d/%m/%Y' if '%d/%m/%y' fails
                        start_dt = datetime.strptime(plan_start_date_str, '%d/%m/%Y')
                    except ValueError:
                        print(f"Skipping row due to unparsable Plan Start Date '{plan_start_date_str}': {row}")
                        continue

                # Calculate end_dt
                end_dt = start_dt + timedelta(days=duration_days)

                # Format dates for DB
                plan_start_date_db = start_dt.strftime('%Y-%m-%d')
                plan_end_date_db = end_dt.strftime('%Y-%m-%d')

                member_info = get_member_by_phone(phone)
                if member_info:
                    member_id = member_info[0]
                else:
                    # Use plan_start_date_db for join date if creating a new member
                    member_id = add_member_with_join_date(name, phone, plan_start_date_db)
                    if not member_id: # If creation failed, try fetching again
                        member_info = get_member_by_phone(phone)
                        if member_info:
                            member_id = member_info[0]
                        else:
                            print(f"Could not create or find member: {name} ({phone})")
                            continue
                    else:
                        print(f"Created new member: {name} with join date {plan_start_date_db}")

                plan_name = row.get('Plan Type', '').strip()
                if not plan_name:
                    print(f"Skipping row due to missing Plan Type: {row}")
                    continue

                # duration_days is already calculated and validated
                plan_id = get_or_create_plan_id(plan_name, duration_days)

                if not plan_id:
                    print(f"Could not create or find plan for row: {row}") # Should use plan_name and duration_days
                    continue

                amount = parse_amount(row.get('Amount','0'))

                add_transaction(
                    transaction_type="Group Class",
                    member_id=member_id,
                    plan_id=plan_id,
                    payment_date=payment_date, # This is YYYY-MM-DD from parse_date
                    start_date=plan_start_date_db, # This is YYYY-MM-DD
                    end_date=plan_end_date_db, # This is YYYY-MM-DD
                    amount_paid=amount,
                    payment_method=row.get('Payment Mode', '').strip(),
                    sessions=None
                    # Removed end_date_override as per new logic
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

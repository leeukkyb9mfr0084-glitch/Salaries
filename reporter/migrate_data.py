import csv
import os
import sqlite3
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Make sure the main database file is initialized
from .database import create_database
from .database_manager import DB_FILE, DatabaseManager

# Determine the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the project root by going up one level
project_root = os.path.dirname(script_dir)

# Construct absolute paths to the CSV files in the project root
GC_CSV_PATH = os.path.join(project_root, 'Kranos MMA Members.xlsx - GC.csv')
PT_CSV_PATH = os.path.join(project_root, 'Kranos MMA Members.xlsx - PT.csv')

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
        return None

def process_gc_data():
    """Reads the Group Class CSV and populates members and group_memberships tables."""
    print("\nProcessing Group Class data...")
    conn = sqlite3.connect(DB_FILE) # Connect once
    db_manager = DatabaseManager(conn) # Create manager

    try:
        cursor = db_manager.conn.cursor() # Use manager's connection
        print("Clearing existing data from tables: transactions, members, plans")
        cursor.execute("DELETE FROM transactions;")
        cursor.execute("DELETE FROM members;")
        cursor.execute("DELETE FROM plans;")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('members', 'transactions', 'plans');")
        db_manager.conn.commit()
        print("Data cleared successfully.")

        if not os.path.exists(GC_CSV_PATH):
            print(f"ERROR: GC data file not found at '{GC_CSV_PATH}'")
            return

        with open(GC_CSV_PATH, mode='r', encoding='utf-8-sig') as infile: # Use utf-8-sig to handle BOM
            reader = csv.reader(infile)
            # Read header and strip spaces from each column name
            header = [h.strip() for h in next(reader)]

            for row_list in reader:
                row = dict(zip(header, row_list))
                _process_gc_row(row, db_manager)
    # This is the except for the outer try (line 52)
    except sqlite3.Error as e:
        print(f"Database error during GC data processing: {e}")
    finally:
        if conn:
            conn.close() # Close the single connection at the end


def _process_gc_row(row, db_manager):
    """Processes a single row from the Group Class CSV."""
    try:
        name = row.get('Client Name', '').strip()
        phone = row.get('Phone', '').strip()
        payment_date_raw = row.get('Payment Date', '').strip()

        # New logic for start and end dates
        plan_start_date_str = row.get('Plan Start Date', '').strip()
        plan_duration_str = row.get('Plan Duration', '0').strip()
        plan_duration = 0
        if plan_duration_str:
            plan_duration = int(plan_duration_str)
        else:
            plan_duration = 0 # Or handle as error if empty is not allowed

        # This check uses the parsed integer plan_duration
        if not plan_start_date_str or plan_duration <= 0:
            print(f"Skipping row due to missing Plan Start Date or invalid/zero Plan Duration: {row}")
            return

        if not all([name, phone, payment_date_raw]):
            print(f"Skipping row due to missing essential data (Name, Phone, or Payment Date): {row}")
            return
    except Exception as e: # This is the new block
        print(f"Error during initial row parsing: {e} for row: {row}")
        return

    payment_date = parse_date(payment_date_raw)
    if not payment_date: # Check essential payment_date
        print(f"Skipping row due to unparsable Payment Date: {row}")
        return

    # This is the main try-catch for the rest of the processing for this row
    try:
        # Attempt to parse plan_start_date_str (with fallbacks)
        try:
            start_dt = datetime.strptime(plan_start_date_str, '%d/%m/%y')
        except ValueError:
            try:
                # Fallback to '%d/%m/%Y' if '%d/%m/%y' fails
                start_dt = datetime.strptime(plan_start_date_str, '%d/%m/%Y')
            except ValueError:
                print(f"Skipping row due to unparsable Plan Start Date '{plan_start_date_str}': {row}")
                return # Important: return here if date is unparsable

        # New end date logic using plan_duration
        # Simplified calculation: end_dt is always start_dt + plan_duration in days.
        end_dt = start_dt + timedelta(days=plan_duration)
        duration_for_db_days = plan_duration # This is already in days

        plan_end_date_db = end_dt.strftime('%Y-%m-%d')

        # Format start date for DB (already available as start_dt)
        plan_start_date_db = start_dt.strftime('%Y-%m-%d')

        member_info = db_manager.get_member_by_phone(phone)
        if member_info:
            member_id = member_info[0]
        else:
            # Use plan_start_date_db for join date if creating a new member
            member_id = db_manager.add_member_with_join_date(name, phone, plan_start_date_db)
            if not member_id: # If creation failed, try fetching again
                member_info = db_manager.get_member_by_phone(phone)
                if member_info:
                    member_id = member_info[0]
                else:
                    print(f"Could not create or find member: {name} ({phone})")
                    return
            else:
                print(f"Created new member: {name} with join date {plan_start_date_db}")

        plan_name = row.get('Plan Type', '').strip()
        if not plan_name:
            print(f"Skipping row due to missing Plan Type: {row}")
            return

        # Use duration_for_db_days for plan ID retrieval
        plan_id = db_manager.get_or_create_plan_id(plan_name, duration_for_db_days)

        if not plan_id:
            print(f"Could not create or find plan for {plan_name} with duration {duration_for_db_days} days for row: {row}")
            return

        amount = parse_amount(row.get('Amount','0'))
        if amount is None:
            print(f"Warning: Skipping row due to invalid amount. Data: {row}")
            return

        db_manager.add_transaction(
            transaction_type="Group Class",
            member_id=member_id,
            plan_id=plan_id,
            transaction_date=payment_date, # This is YYYY-MM-DD from parse_date
            start_date=plan_start_date_db, # This is YYYY-MM-DD
            end_date=plan_end_date_db, # This is YYYY-MM-DD
            amount=amount,
            payment_method=row.get('Payment Mode', '').strip(),
            sessions=None
        )
    except (ValueError, KeyError) as e: # Catches data-related errors from the main block
        print(f"Skipping row due to data error ('{e}'): {row}")
        return
    except Exception as e: # Catches any other unexpected errors from the main block
        print(f"An unexpected error occurred on row {row}: {e}")
        return


def process_pt_data():
    """Reads the Personal Training CSV and populates pt_bookings table."""
    print("\nProcessing Personal Training data...")
    conn = sqlite3.connect(DB_FILE)
    db_manager = DatabaseManager(conn)

    try:
        if not os.path.exists(PT_CSV_PATH):
            print(f"ERROR: PT data file not found at '{PT_CSV_PATH}'")
            return

        with open(PT_CSV_PATH, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.reader(infile)
            header = [h.strip() for h in next(reader)]

            for row_list in reader:
                row = dict(zip(header, row_list))
                # All indentation from here uses 4 spaces per level
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

                    member_info = db_manager.get_member_by_phone(phone)
                    if member_info:
                        member_id = member_info[0]
                    else:
                        member_id = db_manager.add_member_with_join_date(name, phone, start_date)
                        if member_id:
                            print(f"Created new member from PT data: {name}")
                        else:
                            print(f"Could not create or find member from PT data: {name}")
                            continue

                    amount_paid = parse_amount(row.get('Amount Paid', '0'))
                    sessions_str = row.get('Session Count', '0').strip()
                    sessions_count = int(sessions_str) if sessions_str else 0

                    db_manager.add_transaction(
                        transaction_type="Personal Training",
                        member_id=member_id,
                        start_date=start_date,
                        amount=amount_paid,
                        sessions=sessions_count,
                        plan_id=None,
                        payment_method=None,
                        transaction_date=start_date
                    )
                except (ValueError, KeyError) as e:
                    print(f"Skipping PT row due to data error ('{e}'): {row}")
                except Exception as e:
                    print(f"An unexpected error occurred on PT row {row}: {e}")
    except sqlite3.Error as e:
        print(f"Database error during PT data processing: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("--- Starting Database Migration ---")
    data_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    create_database(DB_FILE)
    process_gc_data()
    process_pt_data()
    print("\n--- Database Migration Complete ---")

import csv
import os
import sqlite3
from datetime import datetime, timedelta, date # Added date
import sys
import logging # Added logging

if __name__ == "__main__" and __package__ is None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    __package__ = "reporter"

from reporter.database import create_database # Keep for now, though commented out its use later
from reporter.database_manager import DB_FILE, DatabaseManager

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
GC_CSV_PATH = os.path.join(project_root, "Kranos MMA Members.xlsx - GC.csv")
PT_CSV_PATH = os.path.join(project_root, "Kranos MMA Members.xlsx - PT.csv")

def parse_date(date_str):
    date_str = date_str.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try: return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError: pass
    logging.warning(f"Could not parse date '{date_str}' with known formats.")
    return None

def parse_amount(amount_str):
    try:
        cleaned_str = str(amount_str).replace("₹", "").replace(",", "").strip()
        if cleaned_str in ("-", ""): return 0.0
        return float(cleaned_str)
    except (ValueError, AttributeError) as e:
        logging.warning(f"Could not parse amount '{amount_str}': {e}")
        return None

def process_gc_data():
    logging.info("\nProcessing Group Class data...")
    conn = sqlite3.connect(DB_FILE)
    db_manager = DatabaseManager(conn)
    try:
        cursor = db_manager.conn.cursor()
        logging.info("Clearing existing data from tables: memberships, members, plans")
        cursor.execute("DELETE FROM memberships;")
        cursor.execute("DELETE FROM members;")
        cursor.execute("DELETE FROM plans;")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('members', 'memberships', 'plans');")
        db_manager.conn.commit()
        logging.info("Data cleared successfully.")

        if not os.path.exists(GC_CSV_PATH):
            logging.error(f"GC data file not found at '{GC_CSV_PATH}'")
            return

        with open(GC_CSV_PATH, mode="r", encoding="utf-8-sig") as infile:
            reader = csv.DictReader(infile) # Use DictReader for easier column access
            for row in reader:
                _process_gc_row(row, db_manager)
    except sqlite3.Error as e: logging.error(f"Database error during GC data processing: {e}", exc_info=True)
    except Exception as e: logging.error(f"General error during GC data processing: {e}", exc_info=True)
    finally:
        if conn: conn.close()

def _process_gc_row(row, db_manager):
    try:
        name = row.get("Client Name", "").strip()
        phone = row.get("Phone", "").strip()
        plan_start_date_str = row.get("Plan Start Date", "").strip()
        plan_duration_str = row.get("Plan Duration", "0").strip()
        plan_duration_days = int(plan_duration_str) if plan_duration_str.isdigit() else 0

        if not (name and phone and plan_start_date_str and plan_duration_days > 0):
            logging.warning(f"Skipping GC row due to missing essential data or invalid duration: {row}")
            return

        plan_start_date_db = parse_date(plan_start_date_str)
        if not plan_start_date_db:
            logging.warning(f"Skipping GC row due to unparsable Plan Start Date '{plan_start_date_str}': {row}")
            return

        member_info = db_manager.get_member_by_phone(phone)
        if member_info: member_id = member_info[0]
        else:
            member_id = db_manager.add_member_with_join_date(name, phone, plan_start_date_db)
            if not member_id:
                logging.error(f"Could not create or find member: {name} ({phone}) for GC row: {row}")
                return
            logging.info(f"Created new member: {name} with join date {plan_start_date_db}")

        plan_name_from_csv = row.get("Plan Type", "").strip()
        if not plan_name_from_csv:
            logging.warning(f"Skipping GC row due to missing Plan Type: {row}")
            return

        price = parse_amount(row.get("Amount", "0"))
        if price is None: price = 0.0

        plan_id = db_manager.get_or_create_plan_id(plan_name_from_csv, price, "GC")
        if not plan_id:
            logging.error(f"Could not create/find plan for GC: '{plan_name_from_csv}', Price: {price}. Row: {row}")
            return

        amount_paid = parse_amount(row.get("Amount", "0"))
        if amount_paid is None: # Allow 0 amount paid, but not None if parse failed badly
             logging.warning(f"Skipping GC row due to unparseable amount. Data: {row}")
             return

        success, msg = db_manager.create_membership_record(
            member_id=member_id, plan_id=plan_id,
            plan_duration_days=plan_duration_days,
            amount_paid=amount_paid, start_date=plan_start_date_db
        )
        if not success:
            logging.error(f"Failed to create GC membership for {name}: {msg}. Data: {row}")

    except Exception as e:
        logging.error(f"Unexpected error processing GC row {row}: {e}", exc_info=True)

def process_pt_data():
    logging.info("\nProcessing Personal Training data...")
    conn = sqlite3.connect(DB_FILE)
    db_manager = DatabaseManager(conn)
    try:
        if not os.path.exists(PT_CSV_PATH):
            logging.error(f"PT data file not found at '{PT_CSV_PATH}'")
            return

        with open(PT_CSV_PATH, mode="r", encoding="utf-8-sig") as infile:
            reader = csv.DictReader(infile) # Use DictReader
            for row in reader:
                _process_pt_row(row, db_manager)
    except sqlite3.Error as e: logging.error(f"Database error during PT data processing: {e}", exc_info=True)
    except Exception as e: logging.error(f"General error during PT data processing: {e}", exc_info=True)
    finally:
        if conn: conn.close()

def _process_pt_row(row, db_manager):
    try:
        name = row.get("Client Name", "").strip()
        phone = row.get("Phone", "").strip()
        start_date_raw = row.get("Start Date", "").strip()

        if not (name and phone and start_date_raw):
            logging.warning(f"Skipping PT row due to missing essential data: {row}")
            return

        pt_start_date = parse_date(start_date_raw)
        if not pt_start_date:
            logging.warning(f"Skipping PT row due to unparsable Start Date: {row}")
            return

        member_info = db_manager.get_member_by_phone(phone)
        if member_info: member_id = member_info[0]
        else:
            member_id = db_manager.add_member_with_join_date(name, phone, pt_start_date)
            if not member_id:
                logging.error(f"Could not create or find member from PT data: {name}. Row: {row}")
                return
            logging.info(f"Created new member from PT data: {name}")

        amount_paid = parse_amount(row.get("Amount Paid", "0"))
        if amount_paid is None or amount_paid <= 0: # PT amount should be positive
            logging.warning(f"Skipping PT row due to invalid or zero amount: {row}")
            return

        pt_plan_name = "PT Package" # Generic plan name
        # Duration for PT memberships: Use "Plan Duration Days" if available in CSV, else default (e.g., 90)
        # This column might not exist, so handle potential KeyError or use a default.
        pt_membership_duration_days_str = row.get("Plan Duration Days", "90").strip()
        pt_membership_duration_days = int(pt_membership_duration_days_str) if pt_membership_duration_days_str.isdigit() else 90

        plan_price_for_pt = amount_paid # Price for this PT plan instance is the amount paid

        plan_id = db_manager.get_or_create_plan_id(
            name=pt_plan_name, price=plan_price_for_pt, type_text="PT"
        )
        if not plan_id:
            logging.error(f"Could not get/create plan_id for PT: '{pt_plan_name}', Price: {plan_price_for_pt}. Row: {row}")
            return

        success, msg = db_manager.create_membership_record(
            member_id=member_id, plan_id=plan_id,
            plan_duration_days=pt_membership_duration_days,
            amount_paid=amount_paid, start_date=pt_start_date
        )
        if not success:
            logging.error(f"Failed to create PT membership for {name}: {msg}. Data: {row}")

    except Exception as e:
        logging.error(f"Unexpected error processing PT row {row}: {e}", exc_info=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("--- Starting Database Migration ---")
    # Ensure DB_FILE directory exists
    data_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    # It's assumed the database schema is already created and up-to-date (post Task 1.1)
    # create_database(DB_FILE) # This line is intentionally commented out.
    process_gc_data()
    process_pt_data()
    logging.info("\n--- Database Migration Complete ---")

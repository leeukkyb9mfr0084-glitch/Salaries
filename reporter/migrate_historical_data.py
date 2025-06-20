import csv
import logging  # Added logging
import os
import sqlite3
from datetime import datetime, timedelta

import pandas as pd  # Ensure pandas is imported

from .database import DB_FILE, create_database
from .database_manager import DatabaseManager

# Source CSV files (expected in the project root directory)
GC_MEMBERS_CSV = "Kranos MMA Members.xlsx - GC.csv"
PT_MEMBERS_CSV = "Kranos MMA Members.xlsx - PT.csv"

# Basic logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def parse_date_dmy_to_ymd(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt_obj = datetime.strptime(date_str, "%d/%m/%y").date()
    except ValueError:
        try:
            dt_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            return ""
    return dt_obj.strftime("%Y-%m-%d")


def clean_amount(amount_str: str) -> float:
    if not amount_str:
        return 0.0
    cleaned_str = amount_str.replace("₹", "").replace(",", "").strip()
    try:
        return float(cleaned_str)
    except ValueError:
        # Updated logging for consistency, though this function wasn't explicitly asked to be changed.
        if cleaned_str == "-" or cleaned_str == "":
            return 0.0
        return 0.0  # Or raise error, depending on desired strictness


def migrate_gc_data(
    db_mngr: DatabaseManager, processed_members: dict, earliest_start_dates: dict
):  # group_plans_map removed, added earliest_start_dates
    logging.info(f"Starting GC data migration from {GC_MEMBERS_CSV}...")
    if not os.path.exists(GC_MEMBERS_CSV):
        logging.error(f"GC CSV file not found at {GC_MEMBERS_CSV}")
        return 0, 0

    line_count = 0
    success_count = 0
    failed_rows = []

    with open(GC_MEMBERS_CSV, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            line_count += 1
            try:
                phone = row.get("Phone", "").strip()
                name = row.get("Client Name", "").strip()

                if not phone or not name:
                    failed_rows.append((line_count, row, "Missing name or phone"))
                    continue

                member_id = None
                if phone in processed_members:
                    member_id = processed_members[phone]
                else:
                    try:
                        # phone from CSV is row.get('Phone', '').strip()
                        # name from CSV is row.get('Client Name', '').strip()
                        # email can be None
                        member_join_date = earliest_start_dates.get(phone)
                        # Create a Member object
                        from .models import Member # Ensure Member is imported
                        new_member_obj = Member(
                            id=None, # id is None for new members
                            name=name,
                            phone=phone, # field name is 'phone' in Member dataclass
                            email=row.get("Email"),
                            join_date=member_join_date, # This will be used or overridden by add_member if None
                            is_active=True # Default to active for migrated members
                        )
                        # logging.info(f"GC Member to add: {name}, Phone: {phone}, Raw Join Date from CSV: {row.get('Plan Start Date')}, Calculated Join Date: {member_join_date}, Member Obj: {new_member_obj}")
                        added_member_obj = db_mngr.add_member(new_member_obj)
                        if added_member_obj and added_member_obj.id is not None:
                            member_id = added_member_obj.id
                            processed_members[phone] = member_id
                        else:
                            logging.warning(
                                f"Failed to add member (add_member returned None) for row {line_count}: {name}, {phone}"
                            )
                            failed_rows.append(
                                (
                                    line_count,
                                    row,
                                    "Failed to add member (add_member returned None)",
                                )
                            )
                            continue
                    except ValueError:  # Member with phone likely exists
                        cursor = db_mngr.conn.cursor()
                        cursor.execute(
                            "SELECT id FROM members WHERE phone = ?", (phone,)
                        )
                        existing_member_row = cursor.fetchone()
                        if existing_member_row:
                            member_id = existing_member_row[0]
                            processed_members[phone] = member_id
                            logging.info(
                                f"Found existing member by phone for row {line_count}: {name}, {phone}, ID: {member_id}"
                            )
                        else:
                            logging.error(
                                f"Member add failed (ValueError) and fetch failed for row {line_count}: {name}, {phone}"
                            )
                            failed_rows.append(
                                (
                                    line_count,
                                    row,
                                    "Member add failed (ValueError) and fetch failed",
                                )
                            )
                            continue

                if not member_id:
                    logging.warning(
                        f"Could not obtain member_id for row {line_count}: {name}, {phone}"
                    )
                    failed_rows.append((line_count, row, "Could not obtain member_id"))
                    continue

                # New ETL Logic for plan_id
                plan_type = row.get("Plan Type")
                plan_duration_str = row.get("Plan Duration")
                try:
                    plan_duration = int(plan_duration_str)
                except (ValueError, TypeError):
                    logging.warning(
                        f"Could not parse plan duration for row {line_count}. Value was: '{plan_duration_str}'. Skipping row."
                    )
                    failed_rows.append(
                        (line_count, row, f"Invalid Plan Duration: {plan_duration_str}")
                    )
                    continue

                amount_str = (
                    str(row.get("Amount", "")).strip().replace("₹", "").replace(",", "") # Corrected key to "Amount"
                )
                try:
                    plan_price = float(amount_str)
                except (ValueError, TypeError):
                    logging.warning(
                        f"Could not parse price for row {line_count}. Setting price to 0.0. Value was: '{row.get('Amount')}'" # Corrected key
                    )
                    plan_price = 0.0

                plan_id = db_mngr.find_or_create_group_plan(
                    name=plan_type, duration_days=plan_duration, price=plan_price
                )
                if not plan_id:
                    logging.warning(
                        f"Could not find or create plan for row {line_count}. Plan: {plan_type}, Duration: {plan_duration}. Skipping row."
                    )
                    failed_rows.append(
                        (
                            line_count,
                            row,
                            f"Failed to find or create plan: {plan_type} / {plan_duration}",
                        )
                    )
                    continue

                # Need to fetch plan_duration_days from DB for end_date calculation,
                # as find_or_create_group_plan only returns id.
                # Alternatively, modify find_or_create_group_plan to return duration or a plan object.
                # For now, let's assume duration_days from CSV (plan_duration) is sufficient if plan is newly created.
                # If plan exists, its duration_days should match.
                # This part might need adjustment if the price in CSV is different from DB plan price for existing plans.
                # The prompt for find_or_create_group_plan uses price from CSV to create if not exists.

                purchase_date_csv = row.get("Payment Date", "").strip()
                start_date_csv = row.get("Plan Start Date", "").strip()
                amount_csv = row.get("Amount", "").strip() # Corrected key to "Amount"
                membership_type_csv = row.get("Membership Type", "Fresh").strip()
                # plan_status_csv = row.get('Plan Status', 'EXPIRED').strip() # Removed

                purchase_date = parse_date_dmy_to_ymd(purchase_date_csv)
                start_date = parse_date_dmy_to_ymd(start_date_csv)
                amount_paid = clean_amount(amount_csv)

                db_membership_type = (
                    "New" if membership_type_csv.lower() == "fresh" else "Renewal"
                )
                # db_is_active = 1 if plan_status_csv.lower() == "active" else 0 # Removed

                if not start_date:
                    logging.warning(
                        f"Invalid start date for row {line_count}. Value: '{start_date_csv}'. Skipping."
                    )
                    failed_rows.append((line_count, row, "Invalid start date"))
                    continue
                if not purchase_date:  # If payment date is missing, use start date
                    purchase_date = start_date
                    logging.info(
                        f"Purchase date missing for row {line_count}, using start date: {start_date}"
                    )

                cursor = db_mngr.conn.cursor()
                # plan_duration_days is now plan_duration (parsed int from CSV)
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date_obj = start_date_obj + timedelta(
                    days=plan_duration - 1
                )  # Use plan_duration from CSV
                end_date = end_date_obj.strftime("%Y-%m-%d")

                sql_insert_gc = """
                INSERT INTO group_class_memberships (
                    member_id, plan_id, start_date, end_date, amount_paid,
                    purchase_date, membership_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(member_id, plan_id, start_date) DO NOTHING;
                """
                cursor.execute(
                    sql_insert_gc,
                    (
                        member_id,
                        plan_id,
                        start_date,
                        end_date,
                        amount_paid,
                        purchase_date,
                        db_membership_type,
                    ),
                )
                if cursor.rowcount > 0:
                    success_count += 1
                db_mngr.conn.commit()

            except Exception as e:
                db_mngr.conn.rollback()
                logging.error(
                    f"Exception processing GC row {line_count}: {e} - Data: {dict(row)}",
                    exc_info=True,
                )
                failed_rows.append((line_count, row, str(e)))

    logging.info(
        f"GC data migration: Processed {line_count} rows. Migrated/updated: {success_count}. Failed: {len(failed_rows)}."
    )
    if failed_rows:
        logging.warning("Failed GC rows details (first 5):")
        for i, (r_num, r_data, r_error) in enumerate(failed_rows[:5]):
            logging.warning(f"  GC Row {r_num}: {r_error} - Data: {dict(r_data)}")
    return success_count, len(failed_rows)


def migrate_pt_data(
    db_mngr: DatabaseManager, processed_members: dict, earliest_start_dates: dict
):  # Added earliest_start_dates
    logging.info(f"Starting PT data migration from {PT_MEMBERS_CSV}...")

    if not os.path.exists(PT_MEMBERS_CSV):
        logging.error(f"PT CSV file not found at {PT_MEMBERS_CSV}")
        return 0, 0

    line_count = 0
    success_count = 0
    failed_rows = []

    with open(PT_MEMBERS_CSV, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            line_count += 1
            try:
                phone = row.get("Phone", "").strip()
                name = row.get("Client Name", "").strip()

                if not phone or not name:
                    failed_rows.append((line_count, row, "Missing name or phone"))
                    continue

                member_id = None
                if phone in processed_members:
                    member_id = processed_members[phone]
                else:
                    try:
                        member_join_date = earliest_start_dates.get(phone)
                        # Create a Member object
                        from .models import Member # Ensure Member is imported (already imported in the other block, but good for clarity)
                        new_member_obj_pt = Member(
                            id=None,
                            name=name,
                            phone=phone, # field name is 'phone'
                            email=row.get("Email"),
                            join_date=member_join_date,
                            is_active=True
                        )
                        # logging.info(f"PT Member to add: {name}, Phone: {phone}, Raw Join Date from CSV: {row.get('Payment Date')}, Calculated Join Date: {member_join_date}, Member Obj: {new_member_obj_pt}")
                        added_member_obj_pt = db_mngr.add_member(new_member_obj_pt)
                        if added_member_obj_pt and added_member_obj_pt.id is not None:
                            member_id = added_member_obj_pt.id
                            processed_members[phone] = member_id
                        else:
                            logging.warning(
                                f"Failed to add member (add_member returned None) for PT row {line_count}: {name}, {phone}"
                            )
                            failed_rows.append(
                                (
                                    line_count,
                                    row,
                                    "Failed to add member (add_member returned None)",
                                )
                            )
                            continue
                    except ValueError:  # Member with phone likely exists
                        cursor = db_mngr.conn.cursor()
                        cursor.execute(
                            "SELECT id FROM members WHERE phone = ?", (phone,)
                        )
                        existing_member_row = cursor.fetchone()
                        if existing_member_row:
                            member_id = existing_member_row[0]
                            processed_members[phone] = member_id
                            logging.info(
                                f"Found existing member by phone for PT row {line_count}: {name}, {phone}, ID: {member_id}"
                            )
                        else:
                            logging.error(
                                f"Member add failed (ValueError) and fetch failed for PT row {line_count}: {name}, {phone}"
                            )
                            failed_rows.append(
                                (
                                    line_count,
                                    row,
                                    "Member add failed (ValueError) and fetch failed for PT",
                                )
                            )
                            continue

                if not member_id:
                    logging.warning(
                        f"Could not obtain member_id for PT row {line_count}: {name}, {phone}"
                    )
                    failed_rows.append(
                        (line_count, row, "Could not obtain member_id for PT")
                    )
                    continue

                purchase_date_csv = row.get("Payment Date", "").strip()
                amount_paid_csv = row.get("Amount Paid", "").strip()
                sessions_csv = row.get("Session Count", "").strip()

                purchase_date = parse_date_dmy_to_ymd(purchase_date_csv)
                amount_paid = clean_amount(amount_paid_csv)
                try:
                    sessions_purchased = int(sessions_csv) if sessions_csv else 0
                except ValueError:
                    sessions_purchased = 0
                    logging.warning(
                        f"Invalid session count for PT row {line_count}. Value: '{sessions_csv}'. Setting to 0."
                    )

                if not purchase_date:
                    logging.warning(
                        f"Invalid purchase date for PT row {line_count}. Value: '{purchase_date_csv}'. Skipping."
                    )
                    failed_rows.append(
                        (line_count, row, "Invalid purchase date for PT")
                    )
                    continue

                cursor_check = db_mngr.conn.cursor()
                # Check if a similar record already exists, now including new fields
                # Defaulting notes to '' and sessions_remaining to sessions_purchased for the check
                cursor_check.execute(
                    """
                    SELECT id FROM pt_memberships
                    WHERE member_id = ? AND purchase_date = ? AND amount_paid = ? AND sessions_total = ? AND sessions_remaining = ?
                """,
                    (
                        member_id,
                        purchase_date,
                        amount_paid,
                        sessions_purchased, # For sessions_total
                        sessions_purchased, # For sessions_remaining (as it's a new membership)
                    ),
                )
                if cursor_check.fetchone():
                    logging.info(
                        f"Skipping existing PT record for member_id {member_id} on {purchase_date}"
                    )
                    continue

                # Call the updated method. DatabaseManager.add_pt_membership now handles setting
                # sessions_total and sessions_remaining internally.
                from .models import PTMembership # Ensure PTMembership is imported
                new_pt_obj = PTMembership(
                    id=None,
                    member_id=member_id,
                    purchase_date=purchase_date,
                    amount_paid=amount_paid,
                    sessions_total=sessions_purchased,
                    sessions_remaining=sessions_purchased # For new memberships, remaining is total
                )
                added_pt_obj = db_mngr.add_pt_membership(new_pt_obj)
                if added_pt_obj and added_pt_obj.id is not None:
                    success_count += 1
                else:
                    failed_rows.append(
                        (line_count, row, "add_pt_membership returned None or error")
                    )

            except Exception as e:
                try:
                    db_mngr.conn.rollback()
                except Exception:
                    pass
                failed_rows.append((line_count, row, str(e)))
                logging.error(
                    f"Exception processing PT row {line_count}: {e} - Data: {dict(row)}",
                    exc_info=True,
                )

    logging.info(
        f"PT data migration: Processed {line_count} rows. Migrated: {success_count}. Failed: {len(failed_rows)}."
    )
    if failed_rows:
        logging.warning("Failed PT rows details (first 5):")
        for i, (r_num, r_data, r_error) in enumerate(failed_rows[:5]):
            logging.warning(f"  PT Row {r_num}: {r_error} - Data: {dict(r_data)}")
    return success_count, len(failed_rows)


def migrate_historical_data():
    logging.info("Starting data migration script...")
    conn = None
    total_gc_success = 0
    total_gc_failed = 0
    total_pt_success = 0
    total_pt_failed = 0
    try:
        db_dir = os.path.dirname(DB_FILE)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logging.info(f"Created database directory: {db_dir}")

        conn = create_database(DB_FILE)

        if conn is None:
            logging.error(
                f"Failed to create or connect to database {DB_FILE}. Migration aborted."
            )
        else:
            conn.execute("PRAGMA foreign_keys = ON;")
            db_mngr = DatabaseManager(connection=conn)
            logging.info(f"Connected to database: {DB_FILE}")

            # --- Start of new logic for earliest_start_dates ---
            gc_csv_path = GC_MEMBERS_CSV  # Using constant defined at the top
            pt_csv_path = PT_MEMBERS_CSV  # Using constant defined at the top
            earliest_start_dates = {}

            if os.path.exists(gc_csv_path):
                df_gc = pd.read_csv(gc_csv_path, dtype={"Phone": str}) # Ensure Phone is read as string
                for index, row in df_gc.iterrows():
                    phone = str(
                        row.get("Phone", "") # row.get should be fine now as dtype is str
                    ).strip()  # Changed 'Phone Number' to 'Phone'
                    if not phone:
                        continue  # Skip if phone is empty
                    try:
                        # Assuming 'Plan Start Date' is in 'dd/mm/yy' or 'dd/mm/yyyy'
                        # parse_date_dmy_to_ymd handles both and returns 'YYYY-MM-DD' or empty
                        start_date_iso = parse_date_dmy_to_ymd(
                            str(row.get("Plan Start Date", "")).strip()
                        )
                        if start_date_iso:  # Only process if date is valid
                            if phone in earliest_start_dates:
                                if start_date_iso < earliest_start_dates[phone]:
                                    earliest_start_dates[phone] = start_date_iso
                            else:
                                earliest_start_dates[phone] = start_date_iso
                    except (
                        Exception
                    ) as e_gc_date:  # Catch generic exception for date processing
                        logging.warning(
                            f"Warning: Could not parse date for GC member {row.get('Client Name')} with phone {phone}: {row.get('Plan Start Date')}. Error: {e_gc_date}"
                        )
            else:
                logging.warning(
                    f"GC CSV file not found at {gc_csv_path} for earliest date processing."
                )

            if os.path.exists(pt_csv_path):
                df_pt = pd.read_csv(pt_csv_path, dtype={"Phone": str}) # Ensure Phone is read as string
                for index, row in df_pt.iterrows():
                    phone = str(
                        row.get("Phone", "") # row.get should be fine now as dtype is str
                    ).strip()  # Changed 'Phone Number' to 'Phone'
                    if not phone:
                        continue
                    try:
                        # Assuming 'Payment Date' is in 'dd/mm/yy' or 'dd/mm/yyyy'
                        payment_date_iso = parse_date_dmy_to_ymd(
                            str(row.get("Payment Date", "")).strip()
                        )
                        if payment_date_iso:
                            if phone in earliest_start_dates:
                                if payment_date_iso < earliest_start_dates[phone]:
                                    earliest_start_dates[phone] = payment_date_iso
                            else:
                                earliest_start_dates[phone] = payment_date_iso
                    except Exception as e_pt_date:
                        logging.warning(
                            f"Warning: Could not parse date for PT member {row.get('Client Name')} with phone {phone}: {row.get('Payment Date')}. Error: {e_pt_date}"
                        )
            else:
                logging.warning(
                    f"PT CSV file not found at {pt_csv_path} for earliest date processing."
                )

            # logging.info(f"Earliest start dates collected: {earliest_start_dates}") # Log the dictionary
            # --- End of new logic for earliest_start_dates ---

            processed_members = {}
            total_gc_success, total_gc_failed = migrate_gc_data(
                db_mngr, processed_members, earliest_start_dates
            )
            total_pt_success, total_pt_failed = migrate_pt_data(
                db_mngr, processed_members, earliest_start_dates
            )

    except Exception as e:
        logging.critical(
            f"A critical error occurred in migrate_historical_data: {e}", exc_info=True
        )
        if conn:
            try:
                conn.rollback()
                logging.info("Transaction rolled back due to error.")
            except Exception as rb_e:
                logging.error(f"Error during rollback: {rb_e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

    logging.info("Data migration script finished.")
    logging.info(
        f"Summary: GC (Success: {total_gc_success}, Failed: {total_gc_failed}), PT (Success: {total_pt_success}, Failed: {total_pt_failed})"
    )


if __name__ == "__main__":
    migrate_historical_data()

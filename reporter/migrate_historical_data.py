import csv
import sqlite3
from datetime import datetime, timedelta
import os
from reporter.database_manager import DatabaseManager
from reporter.database import DB_FILE, create_database

# Source CSV files (expected in the project root directory)
GC_MEMBERS_CSV = "Kranos MMA Members.xlsx - GC.csv"
PT_MEMBERS_CSV = "Kranos MMA Members.xlsx - PT.csv"

def parse_date_dmy_to_ymd(date_str: str) -> str:
    if not date_str:
        return ''
    try:
        dt_obj = datetime.strptime(date_str, "%d/%m/%y").date()
    except ValueError:
        try:
            dt_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            return ''
    return dt_obj.strftime("%Y-%m-%d")

def clean_amount(amount_str: str) -> float:
    if not amount_str:
        return 0.0
    cleaned_str = amount_str.replace('₹', '').replace(',', '').strip()
    try:
        return float(cleaned_str)
    except ValueError:
        if cleaned_str == '-' or cleaned_str == '':
            return 0.0
        return 0.0

def migrate_gc_data(db_mngr: DatabaseManager, group_plans_map: dict, processed_members: dict):
    print(f"Starting GC data migration from {GC_MEMBERS_CSV}...")
    if not os.path.exists(GC_MEMBERS_CSV):
        print(f"Error: GC CSV file not found at {GC_MEMBERS_CSV}")
        return 0, 0

    line_count = 0
    success_count = 0
    failed_rows = []

    with open(GC_MEMBERS_CSV, 'r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            line_count += 1
            try:
                phone = row.get('Phone', '').strip()
                name = row.get('Client Name', '').strip()

                if not phone or not name:
                    failed_rows.append((line_count, row, "Missing name or phone"))
                    continue

                member_id = None
                if phone in processed_members:
                    member_id = processed_members[phone]
                else:
                    try:
                        member_id = db_mngr.add_member(name=name, phone=phone, email=None)
                        if member_id:
                            processed_members[phone] = member_id
                        else:
                            failed_rows.append((line_count, row, "Failed to add member (add_member returned None)"))
                            continue
                    except ValueError:
                        cursor = db_mngr.conn.cursor()
                        cursor.execute("SELECT id FROM members WHERE phone = ?", (phone,))
                        existing_member_row = cursor.fetchone()
                        if existing_member_row:
                            member_id = existing_member_row[0]
                            processed_members[phone] = member_id
                        else:
                            failed_rows.append((line_count, row, "Member add failed (ValueError) and fetch failed"))
                            continue

                if not member_id:
                    failed_rows.append((line_count, row, "Could not obtain member_id"))
                    continue

                plan_type_csv = row.get('Plan Type', '').strip()
                plan_duration_csv = row.get('Plan Duration', '').strip()
                plan_key = (plan_type_csv, plan_duration_csv)

                if plan_key not in group_plans_map:
                    plan_key_alt_mms = ("MMS Focus", plan_duration_csv)
                    if plan_key_alt_mms in group_plans_map:
                        plan_key = plan_key_alt_mms
                    else:
                        failed_rows.append((line_count, row, f"Plan type/duration not mapped: {plan_key}"))
                        continue

                plan_info = group_plans_map[plan_key]
                plan_id = plan_info['id']

                purchase_date_csv = row.get('Payment Date', '').strip()
                start_date_csv = row.get('Plan Start Date', '').strip()
                amount_csv = row.get(' Amount ', '').strip()
                membership_type_csv = row.get('Membership Type', 'Fresh').strip()
                plan_status_csv = row.get('Plan Status', 'EXPIRED').strip()

                purchase_date = parse_date_dmy_to_ymd(purchase_date_csv)
                start_date = parse_date_dmy_to_ymd(start_date_csv)
                amount_paid = clean_amount(amount_csv)

                db_membership_type = "New" if membership_type_csv.lower() == "fresh" else "Renewal"
                db_is_active = 1 if plan_status_csv.lower() == "active" else 0

                if not start_date:
                    failed_rows.append((line_count, row, "Invalid start date"))
                    continue
                if not purchase_date:
                    purchase_date = start_date

                cursor = db_mngr.conn.cursor()
                plan_duration_days = int(plan_info['duration_days'])
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date_obj = start_date_obj + timedelta(days=plan_duration_days -1)
                end_date = end_date_obj.strftime("%Y-%m-%d")

                sql_insert_gc = """
                INSERT INTO group_class_memberships (
                    member_id, plan_id, start_date, end_date, amount_paid,
                    purchase_date, membership_type, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(member_id, plan_id, start_date) DO NOTHING;
                """
                cursor.execute(sql_insert_gc, (
                    member_id, plan_id, start_date, end_date, amount_paid,
                    purchase_date, db_membership_type, db_is_active
                ))
                if cursor.rowcount > 0:
                    success_count += 1
                db_mngr.conn.commit()

            except Exception as e:
                db_mngr.conn.rollback()
                failed_rows.append((line_count, row, str(e)))

    print(f"GC data migration: Processed {line_count} rows. Migrated/updated: {success_count}. Failed: {len(failed_rows)}.")
    if failed_rows:
        print("Failed GC rows details (first 5):")
        for i, (r_num, r_data, r_error) in enumerate(failed_rows[:5]):
            print(f"  GC Row {r_num}: {r_error} - Data: {dict(r_data)}")
    return success_count, len(failed_rows)

def migrate_pt_data(db_mngr: DatabaseManager, processed_members: dict):
    print(f"Starting PT data migration from {PT_MEMBERS_CSV}...")

    if not os.path.exists(PT_MEMBERS_CSV):
        print(f"Error: PT CSV file not found at {PT_MEMBERS_CSV}")
        return 0, 0

    line_count = 0
    success_count = 0
    failed_rows = []

    with open(PT_MEMBERS_CSV, 'r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            line_count += 1
            try:
                phone = row.get('Phone', '').strip()
                name = row.get('Client Name', '').strip()

                if not phone or not name:
                    failed_rows.append((line_count, row, "Missing name or phone"))
                    continue

                member_id = None
                if phone in processed_members:
                    member_id = processed_members[phone]
                else:
                    try:
                        member_id = db_mngr.add_member(name=name, phone=phone, email=None)
                        if member_id:
                            processed_members[phone] = member_id
                        else:
                            failed_rows.append((line_count, row, "Failed to add member (add_member returned None)"))
                            continue
                    except ValueError:
                        cursor = db_mngr.conn.cursor()
                        cursor.execute("SELECT id FROM members WHERE phone = ?", (phone,))
                        existing_member_row = cursor.fetchone()
                        if existing_member_row:
                            member_id = existing_member_row[0]
                            processed_members[phone] = member_id
                        else:
                            failed_rows.append((line_count, row, "Member add failed (ValueError) and fetch failed for PT"))
                            continue

                if not member_id:
                    failed_rows.append((line_count, row, "Could not obtain member_id for PT"))
                    continue

                purchase_date_csv = row.get('Payment Date', '').strip()
                amount_paid_csv = row.get('Amount Paid', '').strip()
                sessions_csv = row.get('Session Count', '').strip()

                purchase_date = parse_date_dmy_to_ymd(purchase_date_csv)
                amount_paid = clean_amount(amount_paid_csv)
                try:
                    sessions_purchased = int(sessions_csv) if sessions_csv else 0
                except ValueError:
                    sessions_purchased = 0

                if not purchase_date:
                    failed_rows.append((line_count, row, "Invalid purchase date for PT"))
                    continue

                cursor_check = db_mngr.conn.cursor()
                cursor_check.execute("""
                    SELECT id FROM pt_memberships
                    WHERE member_id = ? AND purchase_date = ? AND amount_paid = ? AND sessions_purchased = ?
                """, (member_id, purchase_date, amount_paid, sessions_purchased))
                if cursor_check.fetchone():
                    continue

                pt_id = db_mngr.add_pt_membership(
                    member_id=member_id, purchase_date=purchase_date, amount_paid=amount_paid,
                    sessions_purchased=sessions_purchased,
                    notes=f"Migrated from {PT_MEMBERS_CSV} row {line_count}"
                )
                if pt_id:
                    success_count +=1
                else:
                    failed_rows.append((line_count, row, "add_pt_membership returned None or error"))

            except Exception as e:
                try:
                    db_mngr.conn.rollback()
                except Exception: pass
                failed_rows.append((line_count, row, str(e)))

    print(f"PT data migration: Processed {line_count} rows. Migrated: {success_count}. Failed: {len(failed_rows)}.")
    if failed_rows:
        print("Failed PT rows details (first 5):")
        for i, (r_num, r_data, r_error) in enumerate(failed_rows[:5]):
            print(f"  PT Row {r_num}: {r_error} - Data: {dict(r_data)}")
    return success_count, len(failed_rows)

def main():
    print("Starting data migration script...")
    conn = None
    total_gc_success = 0
    total_gc_failed = 0
    total_pt_success = 0
    total_pt_failed = 0
    try:
        # The following lines related to db_dir and ACTUAL_APP_DB_PATH might cause errors
        # as ACTUAL_APP_DB_PATH is no longer defined.
        # However, the instructions are specific about changing the create_database line.
        db_dir = os.path.dirname(DB_FILE) # Assuming DB_FILE can be used here
        if db_dir and not os.path.exists(db_dir):
             os.makedirs(db_dir, exist_ok=True)
             print(f"Created database directory: {db_dir}")

        conn = create_database(DB_FILE)
        conn.execute("PRAGMA foreign_keys = ON;")
        db_mngr = DatabaseManager(connection=conn)
        print(f"Connected to database: {DB_FILE}") # Changed to DB_FILE

        db_group_plans = db_mngr.get_all_group_plans()
        group_plans_map = {}

        for plan in db_group_plans:
            group_plans_map[(plan['name'], str(plan['duration_days']))] = {'id': plan['id'], 'duration_days': plan['duration_days']}

        potential_mappings = {
            ("MMA Focus", "30"): ("MMA Starter", "30"),
            ("MMS Focus", "30"): ("MMA Starter", "30"),
            ("MMA Focus", "60"): ("MMA Starter", "60"),
            ("MMS Focus", "60"): ("MMA Starter", "60"),
            ("MMA Focus", "90"): ("MMA Intermediate", "90"),
            ("MMA Mastery", "30"): ("MMA Starter", "30"),
            ("MMA Mastery", "90"): ("MMA Intermediate", "90"),
            ("MMA Mastery", "180"): ("MMA Advanced", "180"),
            ("MMA Day Pass", "3"): ("MMA Day Pass", "3")
        }

        for csv_key, db_key in potential_mappings.items():
            if db_key in group_plans_map:
                group_plans_map[csv_key] = group_plans_map[db_key]

        print(f"Loaded and mapped {len(group_plans_map)} group plans from DB. Sample keys: {list(group_plans_map.keys())[:5]}")
        if not db_group_plans:
            print("Warning: No group plans found in DB. GC migration likely to fail mapping.")

        processed_members = {}
        total_gc_success, total_gc_failed = migrate_gc_data(db_mngr, group_plans_map, processed_members)
        total_pt_success, total_pt_failed = migrate_pt_data(db_mngr, processed_members)

    except Exception as e:
        print(f"A critical error occurred in main: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception: pass
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

    print("Data migration script finished.")
    print(f"Summary: GC (Success: {total_gc_success}, Failed: {total_gc_failed}), PT (Success: {total_pt_success}, Failed: {total_pt_failed})")

if __name__ == "__main__":
    main()

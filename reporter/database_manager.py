import sqlite3
from datetime import datetime, timedelta, date  # Added date
from typing import Tuple, Optional  # Union might not be needed yet
import logging

# Basic logging configuration (can be overridden by application's config)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# This constant can remain as per original file analysis
DB_FILE = "reporter/data/kranos_data.db"


class DatabaseManager:
    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        # Optional, can be kept or removed
        # self.conn.row_factory = sqlite3.Row

    def create_membership_record(
        self,
        member_id: int,
        plan_id: int,
        plan_duration_days: int,
        amount_paid: float,
        start_date: str,
    ) -> Tuple[bool, str]:
        # Ensure necessary datetime imports (datetime, timedelta, date) are available.
        # (These should be at the top of the file from the previous step)

        cursor = self.conn.cursor()

        # 1. Determine if 'New' or 'Renewal'
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM memberships WHERE member_id = ?", (member_id,)
            )
            count = cursor.fetchone()[0]
            membership_type = "Renewal" if count > 0 else "New"

            # 2. Calculate end_date
            start_date_obj = datetime.strptime(
                start_date, "%Y-%m-%d"
            ).date()  # noqa: E501
            end_date_obj = start_date_obj + timedelta(days=plan_duration_days)
            end_date_str = end_date_obj.strftime("%Y-%m-%d")

            # 3. Set purchase_date to current date
            purchase_date_str = date.today().strftime("%Y-%m-%d")

            # 4. Set is_active to True
            is_active = True

            # 5. Insert into memberships table
            sql_insert = """
            INSERT INTO memberships (
                member_id, plan_id, start_date, end_date, amount_paid,
                purchase_date, membership_type, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                sql_insert,  # Renamed sql to sql_insert to avoid conflict with sql in get_all_memberships_for_view
                (
                    member_id,
                    plan_id,
                    start_date,
                    end_date_str,
                    amount_paid,
                    purchase_date_str,
                    membership_type,
                    is_active,
                ),
            )
            self.conn.commit()
            logging.info(
                f"Membership record created for member_id {member_id}, "
                f"plan_id {plan_id}."
            )
            return True, "Membership record created successfully."

        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"DB error creating membership for member {member_id}: {e}",
                exc_info=True,
            )
            return False, f"Database error: {e}"
        except ValueError as ve:
            # Handle potential errors from strptime if start_date format is wrong
            logging.error(
                f"Date format error for start_date '{start_date}': {ve}",  # noqa: E501
                exc_info=True,
            )
            return False, f"Date format error for start_date: {ve}"

    def get_all_memberships_for_view(
        self,
        name_filter: Optional[str] = None,
        phone_filter: Optional[str] = None,
        status_filter: Optional[str] = None,  # 'Active', 'Inactive', or None
    ) -> list:
        try:
            cursor = self.conn.cursor()
            # These are the columns as per app_specs.md for the memberships table
            # plus the joined columns needed for the view.
            # Adjust column names if they differ in your actual schema (e.g. members.name vs members.client_name)
            # Based on app_specs: members.name, plans.name
            # Based on old code exploration, it was members.client_name. Sticking to app_specs.md.
            sql_select = """
            SELECT
                ms.id AS membership_id,
                m.name AS member_name,
                m.phone AS member_phone,
                p.name AS plan_name,
                ms.start_date,
                ms.end_date,
                ms.amount_paid,
                ms.purchase_date,
                ms.membership_type,
                ms.is_active
            FROM memberships ms
            JOIN members m ON ms.member_id = m.id
            JOIN plans p ON ms.plan_id = p.id
            """  # Renamed sql to sql_select
            conditions = []
            params = []

            if name_filter:
                conditions.append("m.name LIKE ?")
                params.append(f"%{name_filter}%")
            if phone_filter:
                conditions.append("m.phone LIKE ?")
                params.append(f"%{phone_filter}%")
            if status_filter:
                if status_filter.lower() == "active":
                    conditions.append("ms.is_active = ?")
                    params.append(1)  # Assuming 1 for True
                elif status_filter.lower() == "inactive":
                    conditions.append("ms.is_active = ?")
                    params.append(0)  # Assuming 0 for False

            if conditions:
                sql_select += " WHERE " + " AND ".join(conditions)

            sql_select += " ORDER BY ms.purchase_date DESC, m.name ASC"  # Sensible default ordering

            cursor.execute(sql_select, params)
            # Fetch as a list of dictionaries for easier UI consumption if desired,
            # or tuples if that's preferred. For now, default to tuples.
            # To fetch as dicts:
            # self.conn.row_factory = sqlite3.Row
            # cursor = self.conn.cursor()
            # ... execute ...
            # rows = [dict(row) for row in cursor.fetchall()]
            # self.conn.row_factory = None # Reset if it was set temporarily
            return cursor.fetchall()

        except sqlite3.Error as e:
            logging.error(
                f"Database error while fetching memberships for view: {e}",
                exc_info=True,
            )
            return []

    def update_membership_record(
        self,
        membership_id: int,
        member_id: int,  # Assuming member_id might be updatable for a membership, or plan_id
        plan_id: int,
        plan_duration_days: int,
        amount_paid: float,
        start_date: str,  # Date as string e.g., "YYYY-MM-DD"
        is_active: bool,
    ) -> Tuple[bool, str]:
        try:
            # Calculate end_date
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = start_date_obj + timedelta(days=plan_duration_days)
            end_date_str = end_date_obj.strftime("%Y-%m-%d")

            cursor = self.conn.cursor()
            sql_update = """
            UPDATE memberships
            SET
                member_id = ?,
                plan_id = ?,
                start_date = ?,
                end_date = ?,
                amount_paid = ?,
                is_active = ?
            WHERE id = ?
            """
            # Note: purchase_date and membership_type are intentionally not updated.
            cursor.execute(
                sql_update,  # Renamed sql to sql_update
                (
                    member_id,
                    plan_id,
                    start_date,
                    end_date_str,
                    amount_paid,
                    1 if is_active else 0,  # Convert boolean to int for SQLite
                    membership_id,
                ),
            )
            self.conn.commit()

            if cursor.rowcount == 0:
                logging.warning(
                    f"No membership record found with id {membership_id} to update."
                )
                return False, "No membership record found with the given ID to update."

            logging.info(f"Membership record {membership_id} updated successfully.")
            return True, "Membership record updated successfully."

        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"Database error while updating membership {membership_id}: {e}",
                exc_info=True,
            )
            return False, f"Database error: {e}"
        except ValueError as ve:
            # Handle potential errors from strptime if start_date format is wrong
            logging.error(
                f"Date format error for start_date '{start_date}' during update: {ve}",
                exc_info=True,
            )
            return False, f"Date format error for start_date: {ve}"

    def delete_membership_record(self, membership_id: int) -> Tuple[bool, str]:
        try:
            cursor = self.conn.cursor()
            sql_delete = (
                "DELETE FROM memberships WHERE id = ?"  # Renamed for consistency
            )
            cursor.execute(sql_delete, (membership_id,))
            self.conn.commit()

            if cursor.rowcount == 0:
                logging.warning(
                    f"No membership record found with id {membership_id} to delete."
                )
                return False, "No membership record found with the given ID to delete."

            logging.info(f"Membership record {membership_id} deleted successfully.")
            return True, "Membership record deleted successfully."

        except sqlite3.Error as e:
            self.conn.rollback()  # Good practice, though for a simple delete it might not be strictly necessary if autocommit is off
            logging.error(
                f"Database error while deleting membership {membership_id}: {e}",
                exc_info=True,
            )
            return False, f"Database error: {e}"

    def generate_financial_report_data(self, start_date: str, end_date: str) -> dict:
        summary = {"total_revenue": 0.0}
        details = []

        try:
            cursor = self.conn.cursor()
            # Query for detailed list of transactions
            # Joining with members and plans to get names
            sql_select_details = """
            SELECT
                m.name AS member_name,
                p.name AS plan_name,
                ms.amount_paid,
                ms.purchase_date,
                ms.membership_type
            FROM memberships ms
            JOIN members m ON ms.member_id = m.id
            JOIN plans p ON ms.plan_id = p.id
            WHERE ms.purchase_date BETWEEN ? AND ?
            ORDER BY ms.purchase_date ASC;
            """
            cursor.execute(sql_select_details, (start_date, end_date))

            # It's good practice to define the structure of the details.
            # Using a list of dictionaries for the details.
            column_names = [description[0] for description in cursor.description]
            details = [dict(zip(column_names, row)) for row in cursor.fetchall()]

            # Query for total revenue
            sql_select_sum = """
            SELECT SUM(ms.amount_paid)
            FROM memberships ms
            WHERE ms.purchase_date BETWEEN ? AND ?;
            """
            cursor.execute(sql_select_sum, (start_date, end_date))
            total_revenue_result = cursor.fetchone()
            if total_revenue_result and total_revenue_result[0] is not None:
                summary["total_revenue"] = float(total_revenue_result[0])

            return {"summary": summary, "details": details}

        except sqlite3.Error as e:
            logging.error(
                f"Database error while generating financial report data for {start_date} to {end_date}: {e}",
                exc_info=True,
            )
            # Return empty/default structure on error
            return {"summary": {"total_revenue": 0.0}, "details": []}
        except Exception as ex:  # Catch any other unexpected errors
            logging.error(
                f"Unexpected error while generating financial report data: {ex}",
                exc_info=True,
            )
            return {"summary": {"total_revenue": 0.0}, "details": []}

    def generate_renewal_report_data(self) -> list:
        try:
            cursor = self.conn.cursor()
            current_date_str = date.today().strftime("%Y-%m-%d")
            thirty_days_later_obj = date.today() + timedelta(days=30)
            thirty_days_later_str = thirty_days_later_obj.strftime("%Y-%m-%d")

            # Query for renewal data
            # Joins with members and plans to get names.
            # Filters for active memberships ending in the next 30 days.
            sql_select_renewals = """
            SELECT
                m.name AS member_name,
                m.phone AS member_phone,
                p.name AS plan_name,
                ms.start_date,
                ms.end_date,
                ms.amount_paid,
                ms.membership_type
            FROM memberships ms
            JOIN members m ON ms.member_id = m.id
            JOIN plans p ON ms.plan_id = p.id
            WHERE ms.is_active = 1  -- Assuming 1 for True
            AND ms.end_date BETWEEN ? AND ?
            ORDER BY ms.end_date ASC, m.name ASC;
            """
            # Parameters for the query: current_date and 30_days_from_current_date
            # The range should be from today to 30 days from today.
            cursor.execute(
                sql_select_renewals, (current_date_str, thirty_days_later_str)
            )

            # Fetch as a list of dictionaries or tuples.
            # Using dictionaries for consistency with financial report details.
            column_names = [description[0] for description in cursor.description]
            renewal_list = [dict(zip(column_names, row)) for row in cursor.fetchall()]

            return renewal_list

        except sqlite3.Error as e:
            logging.error(
                f"Database error while generating renewal report data: {e}",  # Corrected f-string
                exc_info=True,
            )
            return []  # Return empty list on error
        except Exception as ex:  # Catch any other unexpected errors
            logging.error(
                f"Unexpected error while generating renewal report data: {ex}",
                exc_info=True,
            )
            return []

    def get_active_members(self) -> list:
        try:
            cursor = self.conn.cursor()
            # Select id and name for active members, ordered by name.
            # Assuming 'id' and 'name' are the column names in the 'members' table as per app_specs.md.
            # And is_active is 1 for active.
            sql_select_active_members = """
            SELECT
                id,
                name
            FROM members
            WHERE is_active = 1  -- Assuming 1 for True
            ORDER BY name ASC;
            """
            cursor.execute(sql_select_active_members)

            # Fetch as a list of dictionaries
            column_names = [description[0] for description in cursor.description]
            active_members_list = [
                dict(zip(column_names, row)) for row in cursor.fetchall()
            ]

            return active_members_list

        except sqlite3.Error as e:
            logging.error(
                f"Database error while fetching active members: {e}",  # Corrected f-string
                exc_info=True,
            )
            return []  # Return empty list on error
        except Exception as ex:  # Catch any other unexpected errors
            logging.error(
                f"Unexpected error while fetching active members: {ex}", exc_info=True
            )
            return []

    def get_active_plans(self) -> list:
        try:
            cursor = self.conn.cursor()
            # Select id, name, and price for active plans, ordered by name.
            # Assuming 'id', 'name', 'price', and 'is_active' are columns in 'plans' table as per app_specs.md.
            sql_select_active_plans = """
            SELECT
                id,
                name,
                price,
                type -- also including type as it's in app_specs for plans table
            FROM plans
            WHERE is_active = 1  -- Assuming 1 for True
            ORDER BY name ASC;
            """
            cursor.execute(sql_select_active_plans)

            # Fetch as a list of dictionaries
            column_names = [description[0] for description in cursor.description]
            active_plans_list = [
                dict(zip(column_names, row)) for row in cursor.fetchall()
            ]

            return active_plans_list

        except sqlite3.Error as e:
            logging.error(
                f"Database error while fetching active plans: {e}",  # Corrected f-string
                exc_info=True,
            )
            return []  # Return empty list on error
        except Exception as ex:  # Catch any other unexpected errors
            logging.error(
                f"Unexpected error while fetching active plans: {ex}", exc_info=True
            )
            return []

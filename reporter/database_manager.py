import sys
import sqlite3
from datetime import datetime, timedelta, date
from typing import Tuple, Optional, Union
import logging

# Basic logging configuration (can be overridden by application's config)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# DB_FILE constant might still be useful for default database path for applications
# that use this manager, but the DatabaseManager class itself won't use it to create connections.
DB_FILE = "reporter/data/kranos_data.db"


class DatabaseManager:
    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        # self.conn.row_factory = sqlite3.Row # Optional: if column access by name is desired

    def add_member_to_db(
        self, name: str, phone: str, join_date: str = None
    ) -> Tuple[bool, str]:
        if not name or not phone:
            # Consider logging this instead of printing, or raising an error
            logging.error("Member name and phone number cannot be empty.")
            return False, "Error: Member name and phone number cannot be empty."
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
                (name, phone, join_date),
            )
            self.conn.commit()
            return True, "Member added successfully."
        except sqlite3.IntegrityError:
            logging.warning(
                f"Error adding member: Phone number '{phone}' likely already exists."
            )
            return (
                False,
                f"Error adding member: Phone number '{phone}' likely already exists.",
            )
        except sqlite3.Error as e:
            logging.error(f"Database error while adding member: {e}", exc_info=True)
            return False, f"Database error while adding member: {e}"

    def _update_member_join_date_if_earlier(
        self, member_id: int, activity_start_date_str: str, cursor: sqlite3.Cursor
    ):
        try:
            activity_start_date = datetime.strptime(
                activity_start_date_str, "%Y-%m-%d"
            ).date()
            cursor.execute(
                "SELECT join_date FROM members WHERE member_id = ?", (member_id,)
            )
            result = cursor.fetchone()
            if result:
                current_join_date_str = result[0]
                update_needed = False
                if current_join_date_str is None:
                    update_needed = True
                else:
                    current_join_date = datetime.strptime(
                        current_join_date_str, "%Y-%m-%d"
                    ).date()
                    if activity_start_date < current_join_date:
                        update_needed = True
                if update_needed:
                    cursor.execute(
                        "UPDATE members SET join_date = ? WHERE member_id = ?",
                        (activity_start_date_str, member_id),
                    )
        except sqlite3.Error as e:
            logging.error(
                f"Error in _update_member_join_date_if_earlier for member {member_id}: {e}",
                exc_info=True,
            )
        except ValueError as ve:
            logging.error(
                f"Date parsing error in _update_member_join_date_if_earlier: {ve}",
                exc_info=True,
            )

    def get_all_members(
        self, name_filter: str = None, phone_filter: str = None
    ) -> list:
        try:
            cursor = self.conn.cursor()
            base_query = "SELECT member_id, client_name, phone, join_date, is_active FROM members"
            conditions = ["is_active = 1"]
            params = []
            if name_filter:
                conditions.append("client_name LIKE ?")
                params.append(f"%{name_filter}%")
            if phone_filter:
                conditions.append("phone LIKE ?")
                params.append(f"%{phone_filter}%")
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            base_query += " ORDER BY client_name ASC"
            cursor.execute(base_query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Database error while fetching members: {e}", exc_info=True)
            return []

    def get_member_by_id(self, member_id: int) -> Optional[tuple]:
        """Fetches a member's details by their ID."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT member_id, client_name, phone, join_date, is_active FROM members WHERE member_id = ?",
                (member_id,),
            )
            member_data = cursor.fetchone()
            if member_data:
                # Convert is_active from integer (0 or 1) to boolean
                data_list = list(member_data)
                data_list[4] = bool(data_list[4])
                return tuple(data_list)
            return None
        except sqlite3.Error as e:
            logging.error(
                f"Database error while fetching member by ID {member_id}: {e}",
                exc_info=True,
            )
            return None

    def update_member(
        self, member_id: int, name: str, phone: str, join_date: str, is_active: bool
    ) -> Tuple[bool, str]:
        """Updates an existing member's details."""
        if not name or not phone:
            logging.error("Member name and phone number cannot be empty for update.")
            return False, "Error: Member name and phone number cannot be empty."
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE members SET client_name = ?, phone = ?, join_date = ?, is_active = ? WHERE member_id = ?",
                (name, phone, join_date, 1 if is_active else 0, member_id),
            )
            self.conn.commit()
            if cursor.rowcount > 0:
                # After updating member details, especially status, recalculate overall status.
                self._update_member_status(member_id)
                return True, "Member updated successfully."
            return False, "Failed to update member. Member not found or data unchanged."
        except sqlite3.IntegrityError:
            logging.warning(
                f"Error updating member {member_id}: Phone number '{phone}' likely already exists for another member."
            )
            return (
                False,
                f"Error updating member: Phone number '{phone}' likely already exists for another member.",
            )
        except sqlite3.Error as e:
            logging.error(
                f"Database error while updating member {member_id}: {e}", exc_info=True
            )
            return False, f"Database error while updating member: {e}"

    def get_filtered_members(
        self, name_query: Optional[str] = None, status: Optional[str] = None
    ) -> list:
        """
        Fetches members, optionally filtered by name (partial match) and status.
        Status can be "Active" or "Inactive".
        Returns list of tuples: (member_id, client_name, phone, join_date, is_active (bool)).
        """
        try:
            cursor = self.conn.cursor()
            base_query = "SELECT member_id, client_name, phone, join_date, is_active FROM members"
            conditions = []
            params = []

            if name_query:
                conditions.append("client_name LIKE ?")
                params.append(f"%{name_query}%")

            if status:
                if status.lower() == "active":
                    conditions.append("is_active = 1")
                elif status.lower() == "inactive":
                    conditions.append("is_active = 0")
                # If status is something else, it's ignored, or you could log a warning.

            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)

            base_query += " ORDER BY client_name ASC"

            cursor.execute(base_query, params)
            rows = cursor.fetchall()
            # Convert is_active from integer (0 or 1) to boolean for each row
            return [
                tuple(list(row[:4]) + [bool(row[4])]) for row in rows
            ]
        except sqlite3.Error as e:
            logging.error(
                f"Database error while fetching filtered members: {e}", exc_info=True
            )
            return []

    def add_plan(
        self, name: str, duration: int, price: int, type_text: str
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Adds a new plan to the database.

        Args:
            name: The name of the plan. Must be unique.
            duration: The duration of the plan in days. Must be positive.
            price: The price of the plan. Must not be negative.
            type_text: The type or category of the plan (e.g., 'GC', 'PT'). Must not be empty.

        Returns:
            A tuple containing:
            - bool: True if the plan was added successfully, False otherwise.
            - str: A message indicating success or the reason for failure.
            - Optional[int]: The ID of the newly added plan if successful, None otherwise.
        """
        if duration <= 0:
            logging.error("Plan duration must be a positive number of days.")
            return (
                False,
                "Error: Plan duration must be a positive number of days.",
                None,
            )
        if price < 0:  # Assuming price cannot be negative
            logging.error("Plan price cannot be negative.")
            return False, "Error: Plan price cannot be negative.", None
        if not type_text:  # Assuming type cannot be empty
            logging.error("Plan type cannot be empty.")
            return False, "Error: Plan type cannot be empty.", None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO plans (name, duration, price, type) VALUES (?, ?, ?, ?)",
                (name, duration, price, type_text),
            )
            self.conn.commit()
            return True, "Plan added successfully.", cursor.lastrowid
        except sqlite3.IntegrityError:
            logging.warning(
                f"Error adding plan: Plan name '{name}' likely already exists."
            )  # Name is UNIQUE
            return (
                False,
                f"Error adding plan: Plan name '{name}' likely already exists.",
                None,
            )
        except sqlite3.Error as e:
            logging.error(f"Database error while adding plan: {e}", exc_info=True)
            return False, f"Database error while adding plan: {e}", None

    def update_plan(
        self, plan_id: int, name: str, duration: int, price: int, type_text: str, is_active: Optional[bool] = None
    ) -> Tuple[bool, str]:
        if duration <= 0:
            logging.error("Plan duration must be a positive number of days.")
            return False, "Error: Plan duration must be a positive number of days."
        if price < 0:  # Assuming price cannot be negative
            logging.error("Plan price cannot be negative.")
            return False, "Error: Plan price cannot be negative."
        if not type_text:  # Assuming type cannot be empty
            logging.error("Plan type cannot be empty.")
            return False, "Error: Plan type cannot be empty."

        try:
            cursor = self.conn.cursor()

            fields_to_update = {
                "name": name,
                "duration": duration,
                "price": price,
                "type": type_text,
            }
            if is_active is not None:
                fields_to_update["is_active"] = 1 if is_active else 0

            set_clause = ", ".join([f"{key} = ?" for key in fields_to_update])
            params = list(fields_to_update.values())
            params.append(plan_id)

            sql = f"UPDATE plans SET {set_clause} WHERE id = ?"

            cursor.execute(sql, params)
            self.conn.commit()

            if cursor.rowcount > 0:
                # If plan status is changed, members' overall status might change.
                # This is a potentially heavy operation if done here directly.
                # Consider if _update_member_status should be called for all affected members.
                # For now, focusing on plan update. The _update_member_status is typically called
                # after a transaction, or for a specific member.
                # If a plan deactivation should immediately make all members on that plan inactive
                # (if it's their only active plan), that logic would be more involved.
                # The current _update_member_status is member-centric.
                return True, "Plan updated successfully."
            return False, "Failed to update plan. Plan not found or data unchanged."
        except (
            sqlite3.IntegrityError
        ):  # This typically means the 'name' (which is UNIQUE) conflicts.
            logging.warning(
                f"Error updating plan {plan_id}: New plan name '{name}' likely already exists for another plan."
            )
            return (
                False,
                f"Error updating plan: Plan name '{name}' likely already exists for another plan.",
            )
        except sqlite3.Error as e:
            logging.error(
                f"Database error while updating plan {plan_id}: {e}", exc_info=True
            )
            return False, f"Database error while updating plan {plan_id}: {e}"

    def get_plan_by_id(self, plan_id: int) -> Optional[tuple]:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, default_duration, price, type, is_active FROM plans WHERE id = ?", # Changed duration to default_duration
                (plan_id,),
            )
            return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(
                f"Database error fetching plan by ID {plan_id}: {e}", exc_info=True
            )
            return None

    def get_all_plans(self) -> list:  # Fetches all plans (is_active column was removed)
        try:
            cursor = self.conn.cursor()
            # Selects all plans, including their is_active status.
            # Callers can filter based on is_active if needed.
            cursor.execute(
                "SELECT id, name, default_duration, price, type, is_active FROM plans ORDER BY name ASC" # Changed duration to default_duration
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(
                f"Database error fetching all plans: {e}", exc_info=True
            )  # Updated log message
            return []

    def _update_member_status(self, member_id: int):
        """
        Updates the is_active status of a member based on their memberships.
        A member is active if they have at least one active membership
        where the current date is between the start_date and end_date.
        """
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT start_date, end_date
                FROM memberships
                WHERE member_id = ? AND is_active = 1
            """
            cursor.execute(query, (member_id,))
            memberships = cursor.fetchall()

            today = date.today()
            is_currently_active = False

            for start_date_str, end_date_str in memberships:
                if not start_date_str or not end_date_str:
                    logging.warning(
                        f"Skipping membership for member {member_id} due to missing start_date or end_date."
                    )
                    continue
                try:
                    start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    if start_date_obj <= today <= end_date_obj:
                        is_currently_active = True
                        break  # Found an active membership
                except ValueError as ve:
                    logging.error(
                        f"Date parsing error for member {member_id}, start_date '{start_date_str}', end_date '{end_date_str}': {ve}",
                        exc_info=True,
                    )

            update_status_query = "UPDATE members SET is_active = ? WHERE member_id = ?"
            cursor.execute(update_status_query, (1 if is_currently_active else 0, member_id))
            self.conn.commit()
            logging.info(
                f"Member {member_id} status updated to {'active' if is_currently_active else 'inactive'}."
            )

        except sqlite3.Error as e:
            logging.error(
                f"Database error in _update_member_status for member {member_id}: {e}",
                exc_info=True,
            )
        except Exception as ex:
            logging.error(
                f"Unexpected error in _update_member_status for member {member_id}: {ex}",
                exc_info=True,
            )

    def get_all_activity_for_member(self, member_id: int) -> list:
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT
                    ms.id AS membership_id,
                    p.name AS plan_name,
                    ms.start_date,
                    ms.end_date,
                    ms.amount_paid,
                    ms.purchase_date,
                    ms.membership_type,
                    ms.is_active
                FROM memberships ms
                JOIN members m ON ms.member_id = m.member_id
                JOIN plans p ON ms.plan_id = p.id
                WHERE ms.member_id = ?
                ORDER BY ms.purchase_date DESC, ms.start_date DESC;
            """
            cursor.execute(query, (member_id,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(
                f"Database error fetching activity for member {member_id}: {e}",
                exc_info=True,
            )
            return []

    def get_pending_renewals(self, year: int, month: int) -> list:
        if not (1 <= month <= 12):
            return []
        # Ensure month is zero-padded
        month_str = f"{month:02d}"
        # Construct the first and last day of the target month for accurate date range filtering
        first_day_of_month = f"{year:04d}-{month_str}-01"
        # To get the last day, add one month to the first day, then subtract one day.
        # This handles varying month lengths and leap years correctly.
        try:
            next_month_first_day = (datetime.strptime(first_day_of_month, "%Y-%m-%d") + timedelta(days=32)).replace(day=1)
            last_day_of_month_obj = next_month_first_day - timedelta(days=1)
            last_day_of_month = last_day_of_month_obj.strftime("%Y-%m-%d")
        except ValueError: # Should not happen with validated year/month
            logging.error(f"Date calculation error for pending renewals {year}-{month_str}.")
            return []

        try:
            cursor = self.conn.cursor()
            query = """
                SELECT m.client_name, m.phone, p.name AS plan_name, ms.end_date
                FROM memberships ms
                JOIN members m ON ms.member_id = m.member_id
                JOIN plans p ON ms.plan_id = p.id
                WHERE ms.end_date BETWEEN ? AND ?
                  AND ms.is_active = 1
                ORDER BY ms.end_date ASC, m.client_name ASC;
            """
            cursor.execute(query, (first_day_of_month, last_day_of_month))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(
                f"Database error fetching pending renewals for {year}-{month_str}: {e}",
                exc_info=True,
            )
            return []

    def get_finance_report(self, year: int, month: int) -> float | None:
        if not (1 <= month <= 12):
            return None
        # Ensure month is zero-padded
        month_str = f"{month:02d}"
        year_month_str = f"{year:04d}-{month_str}" # Used for strftime filtering

        try:
            cursor = self.conn.cursor()
            # Filters by the 'YYYY-MM' part of purchase_date
            cursor.execute(
                "SELECT SUM(amount_paid) FROM memberships WHERE strftime('%Y-%m', purchase_date) = ?",
                (year_month_str,),
            )
            result = cursor.fetchone()
            return float(result[0]) if result and result[0] is not None else 0.0
        except sqlite3.Error as e:
            logging.error(
                f"Database error for finance report {year_month_str}: {e}",
                exc_info=True,
            )
            return None

    def get_member_by_phone(self, phone: str) -> tuple | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT member_id, client_name FROM members WHERE phone = ? AND is_active = 1",
                (phone,),
            )
            return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(
                f"Database error fetching member by phone '{phone}': {e}", exc_info=True
            )
            return None

    def add_member_with_join_date(
        self, name: str, phone: str, join_date: str
    ) -> int | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
                (name, phone, join_date),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:  # Phone likely exists
            return None
        except sqlite3.Error as e:
            logging.error(
                f"Database error adding member '{name}' with join date: {e}",
                exc_info=True,
            )
            return None

    def get_plan_by_name_and_duration( # Changed duration to default_duration
        self, name: str, default_duration: int
    ) -> tuple | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, default_duration, price, type FROM plans WHERE name = ? AND default_duration = ?",
                (name, default_duration),
            )
            return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(
                f"DB error fetching plan '{name}' dur {default_duration} days: {e}", # Changed duration to default_duration
                exc_info=True,
            )
            return None

    def get_or_create_plan_id( # Changed duration to default_duration
        self, name: str, default_duration: int, price: int, type_text: str
    ) -> Optional[int]:
        """
        Retrieves the ID of an existing plan or creates a new one.

        The method first queries the database for a plan with the specified 'name'
        and 'default_duration'.
        - If a plan with the same name and default_duration is found, its ID is returned.
        - If no such plan exists, a new plan is created with the provided 'name',
          'default_duration', 'price', and 'type_text', and the ID of the new plan is returned.

        This approach helps prevent "UNIQUE constraint failed" errors when data migration
        or other processes attempt to add plans, assuming the relevant unique constraint
        involves at least 'name' and 'default_duration'.

        Args:
            name: The name of the plan.
            default_duration: The default_duration of the plan in days.
            price: The price of the plan. Used if creating a new plan.
            type_text: The type of the plan (e.g., 'GC', 'PT'). Used if creating a new plan.

        Returns:
            The ID of the existing or newly created plan, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        try:
            # Check if a plan with the same name and default_duration already exists
            cursor.execute(
                "SELECT id FROM plans WHERE name = ? AND default_duration = ?", (name, default_duration)
            )
            result = cursor.fetchone()
            if result:
                logging.debug(
                    f"Found existing plan for name='{name}', default_duration={default_duration}. ID: {result[0]}"
                )
                return result[0]
            else:
                # If it doesn't exist, insert the new plan
                logging.info(
                    f"Creating new plan: name='{name}', default_duration={default_duration}, price={price}, type='{type_text}'"
                )
                cursor.execute(
                    "INSERT INTO plans (name, default_duration, price, type) VALUES (?, ?, ?, ?)",
                    (name, default_duration, price, type_text),
                )
                self.conn.commit()
                new_plan_id = cursor.lastrowid
                logging.info(
                    f"Created new plan with ID: {new_plan_id} (Name: '{name}', Default Duration: {default_duration} days)"
                )
                return new_plan_id
        except sqlite3.IntegrityError as ie:
            # This specific catch can be useful if there's a race condition or
            # if the UNIQUE constraint is on something unexpected (e.g. name alone)
            # and the initial check passed.
            self.conn.rollback()  # Rollback any pending transaction
            logging.error(
                f"Integrity error in get_or_create_plan_id for name='{name}', default_duration={default_duration}: {ie}. "
                "This might indicate a conflict with an existing plan not caught by the initial check.",
                exc_info=True,
            )
            # Attempt to fetch again, in case another process created it.
            # This is an optimistic recovery for race conditions.
            try:
                cursor.execute(
                    "SELECT id FROM plans WHERE name = ? AND default_duration = ?",
                    (name, default_duration),
                )
                result = cursor.fetchone()
                if result:
                    logging.warning(
                        f"Found plan ID {result[0]} for name='{name}', default_duration={default_duration} after initial IntegrityError."
                    )
                    return result[0]
                logging.error(
                    f"Still no plan found for name='{name}', default_duration={default_duration} after IntegrityError and re-check."
                )
                return None
            except sqlite3.Error as final_e:
                logging.error(
                    f"Further SQLite error after IntegrityError in get_or_create_plan_id for '{name}': {final_e}",
                    exc_info=True,
                )
                return None

        except sqlite3.Error as e:
            self.conn.rollback()  # Rollback any pending transaction
            logging.error(
                f"General SQLite error in get_or_create_plan_id for name='{name}', default_duration={default_duration}: {e}",
                exc_info=True,
            )
            return None

    def get_book_status(self, month_key: str) -> str:  # YYYY-MM
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT status FROM monthly_book_status WHERE month_key = ?",
                (month_key,),
            )
            result = cursor.fetchone()
            return "closed" if result and result[0] == "closed" else "open"
        except sqlite3.Error as e:
            logging.error(
                f"DB error fetching book status for {month_key}: {e}", exc_info=True
            )
            return "open"  # Default to open on error

    def set_book_status(self, month_key: str, status: str) -> bool:  # YYYY-MM
        if status not in ["open", "closed"]:
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO monthly_book_status (month_key, status) VALUES (?, ?)",
                (month_key, status),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logging.error(
                f"DB error setting book status for {month_key} to {status}: {e}",
                exc_info=True,
            )
            return False

    def deactivate_member(self, member_id: int) -> Tuple[bool, str]:
        # TODO: Handle active transactions for the member (e.g., by updating their end dates or status) when deactivating.
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE members SET is_active = 0 WHERE member_id = ?", (member_id,)
            )
            self.conn.commit()
            if cursor.rowcount > 0:
                return True, "Member deactivated successfully."
            return False, "Failed to deactivate member. Member not found."
        except sqlite3.Error as e:
            logging.error(
                f"DB error deactivating member {member_id}: {e}", exc_info=True
            )
            return False, f"Database error while deactivating member {member_id}: {e}"

    def delete_plan(self, plan_id: int) -> tuple[bool, str]:
        try:
            cursor = self.conn.cursor()
            # Check if the plan is used in any memberships
            cursor.execute(
                "SELECT 1 FROM memberships WHERE plan_id = ? LIMIT 1", (plan_id,)
            )
            if cursor.fetchone():
                return False, "Plan is in use by a membership and cannot be deleted."

            cursor.execute(
                "DELETE FROM plans WHERE id = ?", (plan_id,)
            )
            self.conn.commit()
            if cursor.rowcount > 0:
                return True, "Plan deleted successfully."
            return False, "Error deleting plan or plan not found."
        except sqlite3.Error as e:
            logging.error(f"Database error deleting plan {plan_id}: {e}", exc_info=True)
            return False, f"Database error while deleting plan {plan_id}: {e}"


# Removed module-level get_db_connection and _TEST_IN_MEMORY_CONNECTION as connection is now managed externally.
# The DB_FILE constant is kept as it might be used by the application to know the default DB path.
# Helper functions like _update_member_join_date_if_earlier are now private methods.
# All database operations now use self.conn.
# Removed conn.close() from individual methods.
# Print statements for errors/warnings replaced with logging.

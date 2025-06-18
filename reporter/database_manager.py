import sqlite3
from datetime import datetime, timedelta, date
from typing import Tuple, Optional, List, Dict # Added List, Dict
import logging
from .models import MemberView, GroupPlanView, GroupClassMembershipView, PTMembershipView

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

    def add_member(self, name: str, phone_number: str, email: Optional[str] = None, is_active=True, join_date=None) -> Optional[int]:
        """Adds a new member to the database.
        Sets join_date to current date and is_active to True by default.
        Raises ValueError if phone number already exists.
        Returns the id of the newly created member, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        try:
            # Check for phone uniqueness
            cursor.execute("SELECT id FROM members WHERE phone = ?", (phone_number,))
            if cursor.fetchone():
                logging.warning(f"Attempt to add member with existing phone number: {phone_number}")
                raise ValueError(f"Phone number {phone_number} already exists.")

            join_date_to_use = join_date if join_date else date.today().isoformat()
            # Ensure is_active is 1 or 0 for SQLite
            is_active_int = 1 if is_active else 0

            cursor.execute(
                "INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                (name, phone_number, email, join_date_to_use, is_active_int),
            )
            self.conn.commit()
            member_id = cursor.lastrowid
            logging.info(f"Member '{name}' added with ID {member_id}.")
            return member_id
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error in add_member for '{name}': {e}", exc_info=True)
            return None
        except ValueError: # Re-raise ValueError for phone uniqueness
            raise

    def update_member(
        self,
        member_id: int,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """Updates an existing member's details.
        If phone is provided, checks for uniqueness unless it's the member's current phone.
        Returns True if update was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        fields_to_update = []
        params = []

        if name is not None:
            fields_to_update.append("name = ?")
            params.append(name)
        if email is not None:
            fields_to_update.append("email = ?")
            params.append(email)
        if is_active is not None:
            fields_to_update.append("is_active = ?")
            params.append(1 if is_active else 0)

        try:
            if phone is not None:
                # Check if the new phone number is different from the current one
                cursor.execute("SELECT phone FROM members WHERE id = ?", (member_id,))
                current_phone_row = cursor.fetchone()
                if not current_phone_row:
                    logging.warning(f"Member with ID {member_id} not found for update.")
                    return False

                current_phone = current_phone_row[0]
                if phone != current_phone:
                    # If different, check for uniqueness among other members
                    cursor.execute("SELECT id FROM members WHERE phone = ? AND id != ?", (phone, member_id))
                    if cursor.fetchone():
                        logging.warning(f"Attempt to update member {member_id} with existing phone number: {phone}")
                        raise ValueError(f"Phone number {phone} already exists for another member.")
                fields_to_update.append("phone = ?")
                params.append(phone)

            if not fields_to_update:
                logging.info(f"No fields provided to update for member ID {member_id}.")
                return True # Or False, depending on desired behavior for no-op updates

            sql_update = f"UPDATE members SET {', '.join(fields_to_update)} WHERE id = ?"
            params.append(member_id)

            cursor.execute(sql_update, tuple(params))
            self.conn.commit()

            if cursor.rowcount == 0:
                logging.warning(f"No member found with ID {member_id} to update, or data was the same.")
                # Consider if this should be False if no row found, True if data was same.
                # For now, if rowcount is 0, it means either not found or no change needed.
                # Let's assume not finding the member is a failure.
                # A more robust check would be to see if the member exists first.
                cursor.execute("SELECT id FROM members WHERE id = ?", (member_id,))
                if not cursor.fetchone():
                    return False # Member not found
                return True # Data was the same, no update needed but operation considered successful

            logging.info(f"Member ID {member_id} updated successfully.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error in update_member for ID {member_id}: {e}", exc_info=True)
            return False
        except ValueError: # Re-raise ValueError for phone uniqueness
            raise

    def get_all_members(self) -> List[Dict]:
        """Retrieves all members from the database."""
        cursor = self.conn.cursor()
        try:
            self.conn.row_factory = sqlite3.Row # To get results as dicts
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, phone, email, join_date, is_active FROM members ORDER BY name ASC")
            members = [dict(row) for row in cursor.fetchall()]
            self.conn.row_factory = None # Reset row_factory
            return members
        except sqlite3.Error as e:
            logging.error(f"Database error in get_all_members: {e}", exc_info=True)
            self.conn.row_factory = None # Ensure reset on error too
            return []

    def get_all_members_for_view(self) -> List[MemberView]:
        """Retrieves all members from the database for view purposes."""
        try:
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            # Ensure query selects columns matching MemberView DTO
            # MemberView DTO is expected to be simplified as per Task 1.3,
            # containing fields like: id, name, phone, email, join_date, is_active.
            # The 'notes' field's presence in MemberView depends on whether it's a direct column in 'members' table
            # and if it was kept in the simplified DTO.
            # This query aligns with a simplified MemberView that includes is_active.
            cursor.execute("SELECT id, name, phone, email, join_date, is_active FROM members ORDER BY name ASC")
            rows = cursor.fetchall()
            # Assumes MemberView constructor matches these fields (e.g., includes is_active).
            # If MemberView expects 'status' instead of 'is_active', a transformation would be needed here.
            # However, Task 1.3 implies 'status' was removed.
            return [MemberView(**row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Database error in get_all_members_for_view: {e}", exc_info=True)
            return []
        finally:
            self.conn.row_factory = None # Reset row_factory

    def delete_member(self, member_id: int) -> bool:
        """Deletes a member from the database by their ID.
        Returns True if deletion was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        try:
            # Future consideration: Check for related records (e.g., active memberships)
            # and decide on deletion policy (cascade, prevent, set null).
            # For now, direct delete.
            cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                logging.warning(f"No member found with ID {member_id} to delete.")
                return False
            logging.info(f"Member ID {member_id} deleted successfully.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error in delete_member for ID {member_id}: {e}", exc_info=True)
            return False

    def add_group_plan(self, name: str, duration_days: int, default_amount: float) -> Optional[int]:
        """Adds a new group_plan to the database.
        Generates display_name from name and duration_days.
        Sets is_active to True by default.
        Raises ValueError if display_name already exists.
        Returns the id of the newly created group_plan, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        display_name = f"{name} - {duration_days} days"
        is_active = 1  # True

        try:
            # Check for display_name uniqueness
            cursor.execute("SELECT id FROM group_plans WHERE display_name = ?", (display_name,))
            if cursor.fetchone():
                logging.warning(f"Attempt to add group_plan with existing display_name: {display_name}")
                raise ValueError(f"Display name '{display_name}' already exists.")

            cursor.execute(
                "INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active) VALUES (?, ?, ?, ?, ?)",
                (name, duration_days, default_amount, display_name, is_active),
            )
            self.conn.commit()
            plan_id = cursor.lastrowid
            logging.info(f"Group Plan '{name}' added with ID {plan_id}, display_name '{display_name}'.")
            return plan_id
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error in add_group_plan for '{name}': {e}", exc_info=True)
            return None
        except ValueError: # Re-raise ValueError for display_name uniqueness
            raise

    def update_group_plan(
        self,
        plan_id: int,
        name: Optional[str] = None,
        duration_days: Optional[int] = None,
        default_amount: Optional[float] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """Updates an existing group_plan's details.
        If name or duration_days are changed, display_name is regenerated and its uniqueness checked.
        Returns True if update was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        fields_to_update = []
        params_for_update = []

        # Fetch current group_plan details first to determine if display_name needs update and for current values
        try:
            cursor.execute("SELECT name, duration_days, display_name FROM group_plans WHERE id = ?", (plan_id,))
            current_plan_row = cursor.fetchone()
            if not current_plan_row:
                logging.warning(f"Group Plan with ID {plan_id} not found for update.")
                return False
            current_name, current_duration_days, current_display_name = current_plan_row

            new_name = name if name is not None else current_name
            new_duration_days = duration_days if duration_days is not None else current_duration_days
            new_display_name = current_display_name

            display_name_changed = False
            if name is not None and name != current_name:
                fields_to_update.append("name = ?")
                params_for_update.append(name)
                display_name_changed = True
            elif name is not None: # name is provided but same as current_name
                fields_to_update.append("name = ?") # ensure it's part of the update if provided
                params_for_update.append(name)


            if duration_days is not None and duration_days != current_duration_days:
                fields_to_update.append("duration_days = ?")
                params_for_update.append(duration_days)
                display_name_changed = True
            elif duration_days is not None: # duration_days is provided but same as current
                fields_to_update.append("duration_days = ?")
                params_for_update.append(duration_days)


            if display_name_changed:
                new_display_name = f"{new_name} - {new_duration_days} days"
                if new_display_name != current_display_name:
                    cursor.execute("SELECT id FROM group_plans WHERE display_name = ? AND id != ?", (new_display_name, plan_id))
                    if cursor.fetchone():
                        logging.warning(f"Attempt to update group_plan {plan_id} with existing display_name: {new_display_name}")
                        raise ValueError(f"Display name '{new_display_name}' already exists for another group_plan.")
                fields_to_update.append("display_name = ?")
                params_for_update.append(new_display_name)

            if default_amount is not None:
                fields_to_update.append("default_amount = ?")
                params_for_update.append(default_amount)

            if is_active is not None:
                fields_to_update.append("is_active = ?")
                params_for_update.append(1 if is_active else 0)

            if not fields_to_update:
                logging.info(f"No fields provided to update for group_plan ID {plan_id}.")
                return True

            sql_update_stmt = f"UPDATE group_plans SET {', '.join(fields_to_update)} WHERE id = ?"
            params_for_update.append(plan_id)

            cursor.execute(sql_update_stmt, tuple(params_for_update))
            self.conn.commit()

            if cursor.rowcount == 0:
                # This could mean plan_id not found OR data was identical.
                # We already checked for plan_id existence. So, data was identical.
                logging.info(f"Group Plan ID {plan_id} data was the same, no update performed in DB, but operation considered successful.")
                return True

            logging.info(f"Group Plan ID {plan_id} updated successfully. New display_name: '{new_display_name if display_name_changed else current_display_name}'.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error in update_group_plan for ID {plan_id}: {e}", exc_info=True)
            return False
        except ValueError: # Re-raise ValueError for display_name uniqueness
            raise

    def get_all_group_plans(self) -> List[Dict]:
        """Retrieves all group_plans from the database."""
        cursor = self.conn.cursor()
        try:
            self.conn.row_factory = sqlite3.Row # To get results as dicts
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, duration_days, default_amount, display_name, is_active FROM group_plans ORDER BY name ASC")
            plans = [dict(row) for row in cursor.fetchall()]
            self.conn.row_factory = None # Reset row_factory
            return plans
        except sqlite3.Error as e:
            logging.error(f"Database error in get_all_group_plans: {e}", exc_info=True)
            self.conn.row_factory = None # Ensure reset on error too
            return []

    def get_all_group_plans_for_view(self) -> List[GroupPlanView]:
        """Retrieves all group_plans from the database for view purposes."""
        try:
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            # GroupPlanView: id, name, price, duration_days, display_name, is_active (changed from status)
            # Query maps default_amount to price, and selects is_active.
            cursor.execute("SELECT id, name, default_amount as price, duration_days, display_name, is_active FROM group_plans ORDER BY name ASC")
            rows = cursor.fetchall()
            # Ensure GroupPlanView DTO constructor aligns with these fields, especially 'is_active'
            return [GroupPlanView(**row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Database error in get_all_group_plans_for_view: {e}", exc_info=True)
            return []
        finally:
            self.conn.row_factory = None

    def delete_group_plan(self, plan_id: int) -> bool:
        """Deletes a group_plan from the database by its ID.
        Returns True if deletion was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        try:
            # Future consideration: Check for related memberships.
            # For now, direct delete.
            cursor.execute("DELETE FROM group_plans WHERE id = ?", (plan_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                logging.warning(f"No group_plan found with ID {plan_id} to delete.")
                return False
            logging.info(f"Group Plan ID {plan_id} deleted successfully.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error in delete_group_plan for ID {plan_id}: {e}", exc_info=True)
            return False

    def find_or_create_group_plan(self, name: str, duration_days: int, price: float):
        """
        Finds a group plan by name and duration, or creates it if it doesn't exist.
        Returns the plan_id.
        """
        cursor = self.conn.cursor()

        # First, try to find the plan
        cursor.execute(
            "SELECT id FROM group_plans WHERE name = ? AND duration_days = ?",
            (name, duration_days)
        )
        result = cursor.fetchone()

        if result:
            # If found, return the existing plan_id
            return result[0]
        else:
            # If not found, create it
            # Ensure logging is imported if not already: import logging
            display_name = f"{name} - {duration_days} days - ₹{price}"
            logging.info(f"Creating new group plan: {name} ({duration_days} days)")
            cursor.execute(
                "INSERT INTO group_plans (name, display_name, duration_days, default_amount) VALUES (?, ?, ?, ?)", # Changed price to default_amount
                (name, display_name, duration_days, price) # price parameter now maps to default_amount column
            )
            self.conn.commit()
            return cursor.lastrowid

    def get_group_plan_by_display_name(self, display_name: str) -> Optional[Dict]:
        """Retrieves a specific group_plan by its display_name."""
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM group_plans WHERE display_name = ?", (display_name,))
            plan_row = cursor.fetchone()
            self.conn.row_factory = None # Reset
            if plan_row:
                return dict(plan_row)
            return None
        except sqlite3.Error as e:
            logging.error(f"Database error in get_group_plan_by_display_name for '{display_name}': {e}", exc_info=True)
            self.conn.row_factory = None # Ensure reset on error too
            return None

    def create_group_class_membership(
        self,
        member_id: int,
        plan_id: int,
        start_date_str: str,
        amount_paid: float,
        payment_method: Optional[str] = None, # Not in current schema, but in prompt
        notes: Optional[str] = None, # Not in current schema, but in prompt
    ) -> Optional[int]:
        """Creates a new group_class_membership record.
        Calculates end_date based on group_plan's duration_days.
        Sets transaction_date (purchase_date) to current timestamp.
        membership_type to "New" or "Renewal" by default.
        Raises ValueError if plan_id is not found or start_date_str is invalid.
        Returns the id of the newly created group_class_membership, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        try:
            # Retrieve group_plan duration
            cursor.execute("SELECT duration_days FROM group_plans WHERE id = ?", (plan_id,))
            plan_row = cursor.fetchone()
            if not plan_row:
                logging.error(f"Group Plan with ID {plan_id} not found.")
                raise ValueError(f"Group Plan with ID {plan_id} not found.")
            duration_days = plan_row[0]

            # Calculate end_date
            try:
                start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError as ve:
                logging.error(f"Invalid start_date format: {start_date_str}. Error: {ve}")
                raise ValueError(f"Invalid start_date format: {start_date_str}. Expected YYYY-MM-DD.")

            if duration_days is not None and duration_days > 0:
                end_date_obj = start_date_obj + timedelta(days=duration_days -1) # Inclusive end date
            else: # if duration_days is 0, None, or negative, end_date is same as start_date
                end_date_obj = start_date_obj
            end_date_str_calculated = end_date_obj.strftime("%Y-%m-%d")

            transaction_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # membership_type = "New" # Default for new memberships
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM group_class_memberships WHERE member_id = ?", (member_id,))
            membership_type = "Renewal" if cursor.fetchone() else "New"

            # Note: payment_method and notes are not part of the current 'group_class_memberships' table schema.
            # They are included in the function signature as per the prompt, but will not be inserted.
            # If they need to be stored, the 'group_class_memberships' table schema must be altered.

            sql_insert = """
            INSERT INTO group_class_memberships (
                member_id, plan_id, start_date, end_date, amount_paid,
                purchase_date, membership_type, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                sql_insert,
                (
                    member_id,
                    plan_id,
                    start_date_str,
                    end_date_str_calculated,
                    amount_paid,
                    transaction_date_str, # Stored in purchase_date
                    membership_type,
                    1 # Explicitly set is_active to 1 (True)
                ),
            )
            self.conn.commit()
            membership_id = cursor.lastrowid
            logging.info(f"Group Class Membership record created for member ID {member_id}, plan ID {plan_id} with membership ID {membership_id}.")
            # Logging payment_method and notes if provided, even if not stored, for audit/debugging
            if payment_method:
                logging.info(f"Membership ID {membership_id} - Payment Method (not stored): {payment_method}")
            if notes:
                logging.info(f"Membership ID {membership_id} - Notes (not stored): {notes}")
            return membership_id
        except sqlite3.IntegrityError as ie: # Specifically catch IntegrityError
            self.conn.rollback()
            logging.error(f"DB integrity error creating group_class_membership for member {member_id}, plan {plan_id}: {ie}", exc_info=True)
            raise # Re-raise the IntegrityError
        except sqlite3.Error as e: # Catches other sqlite errors
            self.conn.rollback()
            logging.error(f"DB error (type: {type(e)}) creating group_class_membership for member {member_id}, plan {plan_id}: {e}", exc_info=True) # Modified logging
            return None
        except ValueError: # Re-raise ValueError for plan_id not found or date format issues
            raise


    def get_all_group_class_memberships_for_view( # Renamed function
        self,
        name_filter: Optional[str] = None,
        phone_filter: Optional[str] = None,
        status_filter: Optional[str] = None,  # 'Active', 'Inactive', or None
    ) -> List[GroupClassMembershipView]:
        try:
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            # Query based on prompt for GroupClassMembershipView DTO:
            # id, member_id, member_name, plan_id, plan_name, start_date, end_date, status, auto_renewal_enabled
            sql_select = """
            SELECT
                gcm.id,
                m.id as member_id,
                m.name as member_name,
                gp.id as plan_id,
                gp.name as plan_name,
                gcm.start_date,
                gcm.end_date,
                gcm.is_active,
                gcm.amount_paid,
                gcm.purchase_date,
                gcm.membership_type
            FROM group_class_memberships gcm
            JOIN members m ON gcm.member_id = m.id
            JOIN group_plans gp ON gcm.plan_id = gp.id
            """
            conditions = []
            params = []

            if name_filter:
                conditions.append("m.name LIKE ?")
                params.append(f"%{name_filter}%")
            # phone_filter was in original, but GroupClassMembershipView doesn't have phone.
            # If needed, DTO should be updated or a different view model used.
            # For now, removing phone_filter from conditions based on current DTO.
            if status_filter:
                # Convert 'Active'/'Inactive' to boolean/integer for query
                is_active_val = 1 if status_filter.lower() == 'active' else 0
                conditions.append("gcm.is_active = ?")
                params.append(is_active_val)

            if conditions:
                sql_select += " WHERE " + " AND ".join(conditions)

            # Original ordering was by purchase_date, then m.name. DTO doesn't have purchase_date.
            # Ordering by start_date then member_name as a sensible alternative.
            sql_select += " ORDER BY gcm.start_date DESC, m.name ASC"

            cursor.execute(sql_select, params)
            rows = cursor.fetchall()
            return [GroupClassMembershipView(**row) for row in rows]
        except sqlite3.Error as e:
            logging.error(
                f"Database error while fetching group_class_memberships for view: {e}",
                exc_info=True,
            )
            return []

    def update_group_class_membership_record(
        self,
        membership_id: int,
        member_id: int,
        plan_id: int,
        start_date_str: str,
        amount_paid: float,
    ) -> Tuple[bool, str]:
        cursor = self.conn.cursor()
        try:
            # Fetch plan duration from group_plans table
            cursor.execute("SELECT duration_days FROM group_plans WHERE id = ?", (plan_id,))
            plan_row = cursor.fetchone()
            if not plan_row:
                logging.warning(f"Group Plan with ID {plan_id} not found during membership update for ID {membership_id}.")
                return False, f"Group Plan with ID {plan_id} not found."
            duration_days = plan_row[0]

            # Calculate end_date
            try:
                start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError as ve:
                logging.error(f"Invalid start_date format: {start_date_str} for membership ID {membership_id}. Error: {ve}")
                return False, f"Invalid start_date format: {start_date_str}. Expected YYYY-MM-DD."

            if duration_days is not None and duration_days > 0:
                end_date_obj = start_date_obj + timedelta(days=duration_days -1) # Inclusive end date
            else: # if duration_days is 0, None, or negative, end_date is same as start_date
                end_date_obj = start_date_obj
            end_date_str_calculated = end_date_obj.strftime("%Y-%m-%d")

            sql_update = """
            UPDATE group_class_memberships
            SET
                member_id = ?,
                plan_id = ?,
                start_date = ?,
                end_date = ?,
                amount_paid = ?
            WHERE id = ?
            """
            # purchase_date and membership_type are not updated here.
            # is_active is not stored; it's derived.
            cursor.execute(
                sql_update,
                (
                    member_id,
                    plan_id,
                    start_date_str,
                    end_date_str_calculated,
                    amount_paid,
                    membership_id,
                ),
            )
            self.conn.commit()

            if cursor.rowcount == 0:
                logging.warning(
                    f"No group_class_membership record found with id {membership_id} to update, or data was the same."
                )
                # Check if the record actually exists to differentiate
                cursor.execute("SELECT id FROM group_class_memberships WHERE id = ?", (membership_id,))
                if not cursor.fetchone():
                    return False, "No group_class_membership record found with the given ID to update."
                return True, "Membership data was the same; no update performed, but operation considered successful."


            logging.info(f"Group Class Membership record {membership_id} updated successfully.")
            return True, "Group Class Membership record updated successfully."

        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"Database error while updating group_class_membership {membership_id}: {e}",
                exc_info=True,
            )
            return False, f"Database error: {e}"
        except ValueError as ve: # Should be caught by the specific strptime check now
            self.conn.rollback() # Ensure rollback on ValueErrors too, if they escape initial checks
            logging.error(
                f"Value error during update for membership ID {membership_id}: {ve}",
                exc_info=True,
            )
            return False, str(ve)


    def delete_group_class_membership_record(self, membership_id: int) -> Tuple[bool, str]: # Renamed function
        try:
            cursor = self.conn.cursor()
            sql_delete = (
                "DELETE FROM group_class_memberships WHERE id = ?"  # Renamed for consistency
            )
            cursor.execute(sql_delete, (membership_id,))
            self.conn.commit()

            if cursor.rowcount == 0:
                logging.warning(
                    f"No group_class_membership record found with id {membership_id} to delete."
                )
                return False, "No group_class_membership record found with the given ID to delete."

            logging.info(f"Group Class Membership record {membership_id} deleted successfully.")
            return True, "Group Class Membership record deleted successfully."

        except sqlite3.Error as e:
            self.conn.rollback()  # Good practice, though for a simple delete it might not be strictly necessary if autocommit is off
            logging.error(
                f"Database error while deleting group_class_membership {membership_id}: {e}",
                exc_info=True,
            )
            return False, f"Database error: {e}"

    # Personal Training (PT) Membership CRUD operations
    def add_pt_membership(self, member_id: int, purchase_date: str, amount_paid: float, sessions_purchased: int) -> Optional[int]:
        """Adds a new PT membership record.
        Handles sessions_total (from sessions_purchased param). Sessions_remaining is set to sessions_total initially.
        Returns the id of the newly created PT membership, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        try:
            # sessions_purchased parameter maps to sessions_total column.
            # sessions_remaining is initialized with the value of sessions_purchased.
            # notes column is no longer managed by this function.
            sql_insert = """
            INSERT INTO pt_memberships (member_id, purchase_date, amount_paid, sessions_total, sessions_remaining)
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(
                sql_insert,
                (member_id, purchase_date, amount_paid, sessions_purchased, sessions_purchased),
            )
            self.conn.commit()
            pt_membership_id = cursor.lastrowid
            logging.info(f"PT Membership record created for member ID {member_id} with ID {pt_membership_id}.")
            return pt_membership_id
        except sqlite3.IntegrityError as ie:
            self.conn.rollback()
            logging.error(f"DB integrity error creating PT membership for member {member_id}: {ie}", exc_info=True)
            # Could be due to member_id not existing if foreign key constraint is on.
            raise # Re-raise the IntegrityError to signal issue (e.g. member_id invalid)
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"DB error creating PT membership for member {member_id}: {e}", exc_info=True)
            return None

    def get_all_pt_memberships(self) -> List[Dict]:
        """Retrieves all PT memberships, joining with member's name."""
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        try:
            sql_select = """
            SELECT pt.id, pt.member_id, pt.purchase_date, pt.amount_paid, pt.sessions_purchased, m.name as member_name
            FROM pt_memberships pt
            JOIN members m ON pt.member_id = m.id
            ORDER BY pt.purchase_date DESC, pt.id DESC;
            """
            cursor.execute(sql_select)
            pt_memberships = [dict(row) for row in cursor.fetchall()]
            self.conn.row_factory = None # Reset
            return pt_memberships
        except sqlite3.Error as e:
            logging.error(f"Database error in get_all_pt_memberships: {e}", exc_info=True)
            self.conn.row_factory = None # Ensure reset
            return []

    def get_all_pt_memberships_for_view(self) -> List[PTMembershipView]:
        """Retrieves all PT memberships for view purposes."""
        try:
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            sql_select = """
            SELECT
                pt.id AS membership_id,
                pt.member_id AS member_id,
                m.name AS member_name,
                pt.purchase_date AS purchase_date,
                pt.sessions_total AS sessions_total,
                pt.sessions_remaining AS sessions_remaining,
                pt.amount_paid AS amount_paid
            FROM pt_memberships pt
            JOIN members m ON pt.member_id = m.id
            ORDER BY pt.purchase_date DESC, pt.id DESC
            """
            cursor.execute(sql_select)
            rows = cursor.fetchall()
            memberships = []
            for row in rows:
                memberships.append(PTMembershipView(
                    membership_id=row['membership_id'],
                    member_id=row['member_id'],
                    member_name=row['member_name'],
                    purchase_date=row['purchase_date'],
                    sessions_total=row['sessions_total'],
                    sessions_remaining=row['sessions_remaining'],
                amount_paid=row['amount_paid'] # Changed from notes
                ))
            return memberships
        except sqlite3.Error as e:
            logging.error(f"Database error in get_all_pt_memberships_for_view: {e}", exc_info=True)
            return []
        finally:
            self.conn.row_factory = None

    def delete_pt_membership(self, membership_id: int) -> bool:
        """Deletes a PT membership by its ID.
        Returns True if deletion was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM pt_memberships WHERE id = ?", (membership_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                logging.warning(f"No PT membership found with ID {membership_id} to delete.")
                return False
            logging.info(f"PT Membership ID {membership_id} deleted successfully.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error deleting PT membership ID {membership_id}: {e}", exc_info=True)
            return False

    def update_pt_membership(self, membership_id: int, purchase_date: Optional[str] = None, amount_paid: Optional[float] = None, sessions_purchased: Optional[int] = None) -> bool:
        """Updates an existing PT membership's details.
        Only includes fields in the UPDATE statement if they are provided.
        Returns True if update was successful or no changes were needed, False otherwise.
        """
        cursor = self.conn.cursor()

        # Check if the PT membership exists
        cursor.execute("SELECT id FROM pt_memberships WHERE id = ?", (membership_id,))
        if not cursor.fetchone():
            logging.warning(f"PT Membership with ID {membership_id} not found for update.")
            return False

        fields_to_update = []
        params = []

        if purchase_date is not None:
            # Basic validation for date format, can be expanded
            try:
                datetime.strptime(purchase_date, "%Y-%m-%d")
                fields_to_update.append("purchase_date = ?")
                params.append(purchase_date)
            except ValueError:
                logging.error(f"Invalid purchase_date format: {purchase_date}. Expected YYYY-MM-DD.")
                return False # Or raise ValueError

        if amount_paid is not None:
            if amount_paid < 0:
                logging.error(f"Invalid amount_paid: {amount_paid}. Cannot be negative.")
                return False # Or raise ValueError
            fields_to_update.append("amount_paid = ?")
            params.append(amount_paid)

        if sessions_purchased is not None:
            if sessions_purchased < 0: # Assuming sessions cannot be negative
                logging.error(f"Invalid sessions_purchased: {sessions_purchased}. Cannot be negative.")
                return False # Or raise ValueError
            fields_to_update.append("sessions_purchased = ?")
            params.append(sessions_purchased)

        if not fields_to_update:
            logging.info(f"No fields provided to update for PT Membership ID {membership_id}.")
            return True # No update needed, operation considered successful

        sql_update_stmt = f"UPDATE pt_memberships SET {', '.join(fields_to_update)} WHERE id = ?"
        params.append(membership_id)

        try:
            cursor.execute(sql_update_stmt, tuple(params))
            self.conn.commit()

            if cursor.rowcount == 0:
                # This could happen if data provided is identical to existing data.
                # The initial check ensures the record exists.
                logging.info(f"PT Membership ID {membership_id} data was the same, no update performed in DB, but operation considered successful.")
            else:
                logging.info(f"PT Membership ID {membership_id} updated successfully.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error in update_pt_membership for ID {membership_id}: {e}", exc_info=True)
            return False

    def generate_financial_report_data(self, start_date: str, end_date: str) -> dict:
        summary = {"total_revenue": 0.0}
        details = []

        try:
            cursor = self.conn.cursor()
            # Query for detailed list of transactions from group_class_memberships
            sql_group_details = """
            SELECT
                gcm.purchase_date,
                gcm.amount_paid,
                'Group Class' as type,
                m.name as member_name,
                gp.name as item_name -- Plan name for group class
            FROM group_class_memberships gcm
            JOIN members m ON gcm.member_id = m.id
            JOIN group_plans gp ON gcm.plan_id = gp.id
            WHERE gcm.purchase_date BETWEEN ? AND ?
            """
            cursor.execute(sql_group_details, (start_date, end_date))
            column_names_group = [description[0] for description in cursor.description]
            details.extend([dict(zip(column_names_group, row)) for row in cursor.fetchall()])

            # Query for detailed list of transactions from pt_memberships
            sql_pt_details = """
            SELECT
                ptm.purchase_date,
                ptm.amount_paid,
                'Personal Training' as type,
                m.name as member_name,
                CAST(ptm.sessions_total AS TEXT) || ' PT Sessions' as item_name -- e.g., "10 PT Sessions"
            FROM pt_memberships ptm
            JOIN members m ON ptm.member_id = m.id
            WHERE ptm.purchase_date BETWEEN ? AND ?
            """
            cursor.execute(sql_pt_details, (start_date, end_date))
            column_names_pt = [description[0] for description in cursor.description]
            details.extend([dict(zip(column_names_pt, row)) for row in cursor.fetchall()])

            # Sort all details by purchase_date
            details.sort(key=lambda x: x['purchase_date'])

            # Calculate total revenue from both sources
            total_revenue = sum(item['amount_paid'] for item in details)
            summary["total_revenue"] = total_revenue

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
            # Joins with members and group_plans to get names.
            # Filters for group_class_memberships ending in the next 30 days.
            # The check for gcm.is_active = 1 is replaced by date comparison.
            # PT memberships are not included here as they are session-based.
            sql_select_renewals = """
            SELECT
                m.name AS member_name,
                m.phone AS member_phone,
                gp.name AS plan_name,
                gcm.start_date,
                gcm.end_date,
                gcm.amount_paid,
                gcm.membership_type
            FROM group_class_memberships gcm
            JOIN members m ON gcm.member_id = m.id
            JOIN group_plans gp ON gcm.plan_id = gp.id
            WHERE gcm.is_active = 1 -- Ensure the membership itself is marked active
            AND date('now') BETWEEN gcm.start_date AND gcm.end_date -- Check for current active status by date range
            AND gcm.end_date BETWEEN ? AND ? -- Check for renewal period
            ORDER BY gcm.end_date ASC, m.name ASC;
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

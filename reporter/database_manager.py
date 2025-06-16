import sqlite3
from datetime import datetime, timedelta, date
from typing import Tuple, Optional, List, Dict # Added List, Dict
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

    def add_member(self, name: str, phone: str, email: Optional[str] = None) -> Optional[int]:
        """Adds a new member to the database.
        Sets join_date to current date and is_active to True by default.
        Raises ValueError if phone number already exists.
        Returns the id of the newly created member, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        try:
            # Check for phone uniqueness
            cursor.execute("SELECT id FROM members WHERE phone = ?", (phone,))
            if cursor.fetchone():
                logging.warning(f"Attempt to add member with existing phone number: {phone}")
                raise ValueError(f"Phone number {phone} already exists.")

            join_date = date.today().strftime("%Y-%m-%d")
            is_active = 1  # True

            cursor.execute(
                "INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                (name, phone, email, join_date, is_active),
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

    def add_plan(self, name: str, duration_days: int, default_amount: float) -> Optional[int]:
        """Adds a new plan to the database.
        Generates display_name from name and duration_days.
        Sets is_active to True by default.
        Raises ValueError if display_name already exists.
        Returns the id of the newly created plan, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        display_name = f"{name} - {duration_days} days"
        is_active = 1  # True

        try:
            # Check for display_name uniqueness
            cursor.execute("SELECT id FROM plans WHERE display_name = ?", (display_name,))
            if cursor.fetchone():
                logging.warning(f"Attempt to add plan with existing display_name: {display_name}")
                raise ValueError(f"Display name '{display_name}' already exists.")

            cursor.execute(
                "INSERT INTO plans (name, duration_days, default_amount, display_name, is_active) VALUES (?, ?, ?, ?, ?)",
                (name, duration_days, default_amount, display_name, is_active),
            )
            self.conn.commit()
            plan_id = cursor.lastrowid
            logging.info(f"Plan '{name}' added with ID {plan_id}, display_name '{display_name}'.")
            return plan_id
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error in add_plan for '{name}': {e}", exc_info=True)
            return None
        except ValueError: # Re-raise ValueError for display_name uniqueness
            raise

    def update_plan(
        self,
        plan_id: int,
        name: Optional[str] = None,
        duration_days: Optional[int] = None,
        default_amount: Optional[float] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """Updates an existing plan's details.
        If name or duration_days are changed, display_name is regenerated and its uniqueness checked.
        Returns True if update was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        fields_to_update = []
        params_for_update = []

        # Fetch current plan details first to determine if display_name needs update and for current values
        try:
            cursor.execute("SELECT name, duration_days, display_name FROM plans WHERE id = ?", (plan_id,))
            current_plan_row = cursor.fetchone()
            if not current_plan_row:
                logging.warning(f"Plan with ID {plan_id} not found for update.")
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
                    cursor.execute("SELECT id FROM plans WHERE display_name = ? AND id != ?", (new_display_name, plan_id))
                    if cursor.fetchone():
                        logging.warning(f"Attempt to update plan {plan_id} with existing display_name: {new_display_name}")
                        raise ValueError(f"Display name '{new_display_name}' already exists for another plan.")
                fields_to_update.append("display_name = ?")
                params_for_update.append(new_display_name)

            if default_amount is not None:
                fields_to_update.append("default_amount = ?")
                params_for_update.append(default_amount)

            if is_active is not None:
                fields_to_update.append("is_active = ?")
                params_for_update.append(1 if is_active else 0)

            if not fields_to_update:
                logging.info(f"No fields provided to update for plan ID {plan_id}.")
                return True

            sql_update_stmt = f"UPDATE plans SET {', '.join(fields_to_update)} WHERE id = ?"
            params_for_update.append(plan_id)

            cursor.execute(sql_update_stmt, tuple(params_for_update))
            self.conn.commit()

            if cursor.rowcount == 0:
                # This could mean plan_id not found OR data was identical.
                # We already checked for plan_id existence. So, data was identical.
                logging.info(f"Plan ID {plan_id} data was the same, no update performed in DB, but operation considered successful.")
                return True

            logging.info(f"Plan ID {plan_id} updated successfully. New display_name: '{new_display_name if display_name_changed else current_display_name}'.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error in update_plan for ID {plan_id}: {e}", exc_info=True)
            return False
        except ValueError: # Re-raise ValueError for display_name uniqueness
            raise

    def get_all_plans(self) -> List[Dict]:
        """Retrieves all plans from the database."""
        cursor = self.conn.cursor()
        try:
            self.conn.row_factory = sqlite3.Row # To get results as dicts
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, duration_days, default_amount, display_name, is_active FROM plans ORDER BY name ASC")
            plans = [dict(row) for row in cursor.fetchall()]
            self.conn.row_factory = None # Reset row_factory
            return plans
        except sqlite3.Error as e:
            logging.error(f"Database error in get_all_plans: {e}", exc_info=True)
            self.conn.row_factory = None # Ensure reset on error too
            return []

    def delete_plan(self, plan_id: int) -> bool:
        """Deletes a plan from the database by its ID.
        Returns True if deletion was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        try:
            # Future consideration: Check for related memberships.
            # For now, direct delete.
            cursor.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                logging.warning(f"No plan found with ID {plan_id} to delete.")
                return False
            logging.info(f"Plan ID {plan_id} deleted successfully.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Database error in delete_plan for ID {plan_id}: {e}", exc_info=True)
            return False

    def create_membership(
        self,
        member_id: int,
        plan_id: int,
        start_date_str: str,
        amount_paid: float,
        payment_method: Optional[str] = None, # Not in current schema, but in prompt
        notes: Optional[str] = None, # Not in current schema, but in prompt
    ) -> Optional[int]:
        """Creates a new membership record.
        Calculates end_date based on plan's duration_days.
        Sets transaction_date (purchase_date) to current timestamp.
        Sets is_active to True and membership_type to "New" by default.
        Raises ValueError if plan_id is not found or start_date_str is invalid.
        Returns the id of the newly created membership, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        try:
            # Retrieve plan duration
            cursor.execute("SELECT duration_days FROM plans WHERE id = ?", (plan_id,))
            plan_row = cursor.fetchone()
            if not plan_row:
                logging.error(f"Plan with ID {plan_id} not found.")
                raise ValueError(f"Plan with ID {plan_id} not found.")
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
            is_active = 1  # True
            membership_type = "New" # Default for new memberships

            # Note: payment_method and notes are not part of the current 'memberships' table schema.
            # They are included in the function signature as per the prompt, but will not be inserted.
            # If they need to be stored, the 'memberships' table schema must be altered.

            sql_insert = """
            INSERT INTO memberships (
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
                    is_active,
                ),
            )
            self.conn.commit()
            membership_id = cursor.lastrowid
            logging.info(f"Membership record created for member ID {member_id}, plan ID {plan_id} with membership ID {membership_id}.")
            # Logging payment_method and notes if provided, even if not stored, for audit/debugging
            if payment_method:
                logging.info(f"Membership ID {membership_id} - Payment Method (not stored): {payment_method}")
            if notes:
                logging.info(f"Membership ID {membership_id} - Notes (not stored): {notes}")
            return membership_id
        except sqlite3.IntegrityError as ie: # Specifically catch IntegrityError
            self.conn.rollback()
            logging.error(f"DB integrity error creating membership for member {member_id}, plan {plan_id}: {ie}", exc_info=True)
            raise # Re-raise the IntegrityError
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"DB error creating membership for member {member_id}, plan {plan_id}: {e}", exc_info=True)
            return None
        except ValueError: # Re-raise ValueError for plan_id not found or date format issues
            raise


    # def get_or_create_plan_id(self, name: str, price: float, type_text: str) -> Optional[int]:
    #     cursor = self.conn.cursor()
    #     try:
    #         cursor.execute("SELECT id, price FROM plans WHERE name = ? AND type = ?", (name, type_text))
    #         row = cursor.fetchone()
    #         if row:
    #             plan_id = row[0]
    #             existing_price = row[1]
    #             if existing_price != price:
    #                 logging.warning(f"Plan '{name}' (type: {type_text}) exists with price {existing_price} but new data suggests price {price}. Using existing plan ID {plan_id} with original price.")
    #             return plan_id
    #         else:
    #             cursor.execute(
    #                 "INSERT INTO plans (name, price, type, is_active) VALUES (?, ?, ?, ?)",
    #                 (name, price, type_text, 1)
    #             )
    #             self.conn.commit()
    #             new_plan_id = cursor.lastrowid
    #             logging.info(f"Created new plan '{name}' (type: {type_text}, price: {price}) with ID {new_plan_id}.")
    #             return new_plan_id
    #     except sqlite3.Error as e:
    #         self.conn.rollback()
    #         logging.error(f"Database error in get_or_create_plan_id for plan '{name}': {e}", exc_info=True)
    #         return None

    # def create_membership_record(self, data: Dict) -> Tuple[bool, str]:
    #     member_id = data.get("member_id")
    #     plan_id = data.get("plan_id")
        plan_duration_days = data.get("plan_duration_days")
        amount_paid = data.get("amount_paid")
        start_date = data.get("start_date")

        if not all([member_id, plan_id, plan_duration_days, amount_paid, start_date]):
            missing_keys = [key for key, value in data.items() if not value and key in ["member_id", "plan_id", "plan_duration_days", "amount_paid", "start_date"]]
            logging.error(f"Missing required data for creating membership record. Missing: {missing_keys}")
            return False, f"Missing required data: {', '.join(missing_keys)}"

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM memberships WHERE member_id = ?", (member_id,)
            )
            count = cursor.fetchone()[0]
            membership_type = "Renewal" if count > 0 else "New"

            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = start_date_obj + timedelta(days=plan_duration_days)
            end_date_str = end_date_obj.strftime("%Y-%m-%d")
            purchase_date_str = date.today().strftime("%Y-%m-%d")
            is_active = True

            sql_insert = """
            INSERT INTO memberships (
                member_id, plan_id, start_date, end_date, amount_paid,
                purchase_date, membership_type, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                sql_insert,
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
            logging.info(f"Membership record created for member_id {member_id}, plan_id {plan_id}.")
            return True, "Membership record created successfully."
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"DB error creating membership for member {member_id}: {e}", exc_info=True)
            return False, f"Database error: {e}"
        except ValueError as ve:
            logging.error(f"Date format error for start_date '{start_date}': {ve}", exc_info=True)
            return False, f"Date format error for start_date: {ve}"

    # def get_all_memberships_for_view( # Commenting out this function as well
    #     self,
    #     name_filter: Optional[str] = None,
    #     phone_filter: Optional[str] = None,
    #     status_filter: Optional[str] = None,  # 'Active', 'Inactive', or None
    # ) -> list:
    #     try:
    #         cursor = self.conn.cursor()
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

    # def get_active_plans(self) -> list:
    #     try:
    #         cursor = self.conn.cursor()
    #         # Select id, name, and price for active plans, ordered by name.
    #         # Assuming 'id', 'name', 'price', and 'is_active' are columns in 'plans' table as per app_specs.md.
    #         sql_select_active_plans = """
    #         SELECT
    #             id,
    #             name,
    #             price,
    #             type -- also including type as it's in app_specs for plans table
    #         FROM plans
    #         WHERE is_active = 1  # Assuming 1 for True
    #         ORDER BY name ASC;
    #         """
    #         cursor.execute(sql_select_active_plans)

    #         # Fetch as a list of dictionaries
    #         column_names = [description[0] for description in cursor.description]
    #         active_plans_list = [
    #             dict(zip(column_names, row)) for row in cursor.fetchall()
    #         ]

    #         return active_plans_list

    #     except sqlite3.Error as e:
    #         logging.error(
    #             f"Database error while fetching active plans: {e}",  # Corrected f-string
    #             exc_info=True,
    #         )
    #         return []  # Return empty list on error
    #     except Exception as ex:  # Catch any other unexpected errors
    #         logging.error(
    #             f"Unexpected error while fetching active plans: {ex}", exc_info=True
    #         )
    #         return []

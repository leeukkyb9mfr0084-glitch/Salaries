import sys
import sqlite3
from datetime import datetime, timedelta, date
from typing import Tuple, Optional, Union
import logging

# Basic logging configuration (can be overridden by application's config)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# DB_FILE constant might still be useful for default database path for applications
# that use this manager, but the DatabaseManager class itself won't use it to create connections.
DB_FILE = 'reporter/data/kranos_data.db'

class DatabaseManager:
    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        # self.conn.row_factory = sqlite3.Row # Optional: if column access by name is desired

    def add_member_to_db(self, name: str, phone: str, join_date: str = None) -> Tuple[bool, str]:
        if not name or not phone:
            # Consider logging this instead of printing, or raising an error
            logging.error("Member name and phone number cannot be empty.")
            return False, "Error: Member name and phone number cannot be empty."
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
                (name, phone, join_date)
            )
            self.conn.commit()
            return True, "Member added successfully."
        except sqlite3.IntegrityError:
            logging.warning(f"Error adding member: Phone number '{phone}' likely already exists.")
            return False, f"Error adding member: Phone number '{phone}' likely already exists."
        except sqlite3.Error as e:
            logging.error(f"Database error while adding member: {e}", exc_info=True)
            return False, f"Database error while adding member: {e}"

    def _update_member_join_date_if_earlier(self, member_id: int, activity_start_date_str: str, cursor: sqlite3.Cursor):
        try:
            activity_start_date = datetime.strptime(activity_start_date_str, '%Y-%m-%d').date()
            cursor.execute("SELECT join_date FROM members WHERE member_id = ?", (member_id,))
            result = cursor.fetchone()
            if result:
                current_join_date_str = result[0]
                update_needed = False
                if current_join_date_str is None:
                    update_needed = True
                else:
                    current_join_date = datetime.strptime(current_join_date_str, '%Y-%m-%d').date()
                    if activity_start_date < current_join_date:
                        update_needed = True
                if update_needed:
                    cursor.execute("UPDATE members SET join_date = ? WHERE member_id = ?", (activity_start_date_str, member_id))
        except sqlite3.Error as e:
            logging.error(f"Error in _update_member_join_date_if_earlier for member {member_id}: {e}", exc_info=True)
        except ValueError as ve:
            logging.error(f"Date parsing error in _update_member_join_date_if_earlier: {ve}", exc_info=True)

    def get_all_members(self, name_filter: str = None, phone_filter: str = None) -> list:
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

    def add_plan(self, name: str, duration: int, price: int, type_text: str) -> Tuple[bool, str, Optional[int]]:
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
            return False, "Error: Plan duration must be a positive number of days.", None
        if price < 0: # Assuming price cannot be negative
            logging.error("Plan price cannot be negative.")
            return False, "Error: Plan price cannot be negative.", None
        if not type_text: # Assuming type cannot be empty
            logging.error("Plan type cannot be empty.")
            return False, "Error: Plan type cannot be empty.", None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO plans (name, duration, price, type) VALUES (?, ?, ?, ?)",
                (name, duration, price, type_text)
            )
            self.conn.commit()
            return True, "Plan added successfully.", cursor.lastrowid
        except sqlite3.IntegrityError:
            logging.warning(f"Error adding plan: Plan name '{name}' likely already exists.") # Name is UNIQUE
            return False, f"Error adding plan: Plan name '{name}' likely already exists.", None
        except sqlite3.Error as e:
            logging.error(f"Database error while adding plan: {e}", exc_info=True)
            return False, f"Database error while adding plan: {e}", None

    def update_plan(self, plan_id: int, name: str, duration: int, price: int, type_text: str) -> Tuple[bool, str]:
        if duration <= 0:
            logging.error("Plan duration must be a positive number of days.")
            return False, "Error: Plan duration must be a positive number of days."
        if price < 0: # Assuming price cannot be negative
            logging.error("Plan price cannot be negative.")
            return False, "Error: Plan price cannot be negative."
        if not type_text: # Assuming type cannot be empty
            logging.error("Plan type cannot be empty.")
            return False, "Error: Plan type cannot be empty."
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE plans SET name = ?, duration = ?, price = ?, type = ? WHERE id = ?",
                (name, duration, price, type_text, plan_id)
            )
            self.conn.commit()
            if cursor.rowcount > 0:
                return True, "Plan updated successfully."
            return False, "Failed to update plan. Plan not found or data unchanged."
        except sqlite3.IntegrityError: # This typically means the 'name' (which is UNIQUE) conflicts.
            logging.warning(f"Error updating plan {plan_id}: New plan name '{name}' likely already exists for another plan.")
            return False, f"Error updating plan: Plan name '{name}' likely already exists for another plan."
        except sqlite3.Error as e:
            logging.error(f"Database error while updating plan {plan_id}: {e}", exc_info=True)
            return False, f"Database error while updating plan {plan_id}: {e}"

    def get_plan_by_id(self, plan_id: int) -> Optional[tuple]:
        try:
            cursor = self.conn.cursor()
            # Assuming you want all new fields. Adjust if is_active was intentionally kept for some logic.
            cursor.execute("SELECT id, name, duration, price, type FROM plans WHERE id = ?", (plan_id,))
            return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"Database error fetching plan by ID {plan_id}: {e}", exc_info=True)
            return None

    def get_all_plans(self) -> list: # Fetches all plans (is_active column was removed)
        try:
            cursor = self.conn.cursor()
            # is_active column is removed, so WHERE condition is removed.
            # Adjust if there's a new way to determine active plans (e.g., via 'type' or a new 'status' column)
            cursor.execute("SELECT id, name, duration, price, type FROM plans ORDER BY name ASC")
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Database error fetching all plans: {e}", exc_info=True) # Updated log message
            return []

    def get_member_id_from_transaction(self, transaction_id: int) -> Optional[int]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT member_id FROM transactions WHERE transaction_id = ?", (transaction_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logging.error(f"Database error fetching member_id for transaction {transaction_id}: {e}", exc_info=True)
            return None

    def add_transaction(self, transaction_type: str, member_id: int, start_date: str, amount: float,
                        plan_id: int = None, sessions: int = None, payment_method: str = None, # payment_method is unused now
                        transaction_date: str = None, end_date: str = None) -> Tuple[bool, str]:
        # Determine book month and status
        effective_date_for_booking = transaction_date if transaction_date else start_date
        transaction_month_key = "N/A"
        book_status = "open"
        try:
            transaction_month_key = datetime.strptime(effective_date_for_booking, '%Y-%m-%d').strftime('%Y-%m')
            book_status = self.get_book_status(transaction_month_key)
        except ValueError:
            msg = f"Invalid date format '{effective_date_for_booking}'. Cannot determine book status."
            logging.error(msg)
            return False, msg

        if book_status == "closed":
            msg = f"Cannot add transaction. Books for {transaction_month_key} are closed."
            logging.warning(msg)
            return False, msg

        # Validate amount (assuming amount is price, so it can be > 0)
        # The problem description implies amount is INTEGER in DB, ensure conversion if float is passed.
        if not isinstance(amount, (int, float)) or amount <= 0:
            return False, "Amount paid must be a positive number."

        db_amount = int(amount) # Ensure amount is integer for DB

        # Validate sessions for Personal Training
        if transaction_type == 'Personal Training' and (sessions is None or sessions <= 0):
            return False, "Number of sessions must be a positive number for Personal Training."

        # --- Parameter Mapping ---
        db_type = ""
        db_description = ""

        if transaction_type == "Personal Training":
            db_type = "payment"
            if sessions:
                db_description = f"{sessions} PT sessions"
            else: # Should be caught by above validation, but as a fallback
                db_description = "Personal Training"
        elif transaction_type == "Group Class":
            db_type = "new_subscription" # As per instruction
            # Try to get plan name for description
            plan_name_desc = transaction_type # Fallback
            if plan_id:
                plan_details_for_desc = self.get_plan_by_id(plan_id)
                if plan_details_for_desc and plan_details_for_desc[1]: # plan_details_for_desc[1] is name
                    plan_name_desc = plan_details_for_desc[1]
            db_description = f"Subscription: {plan_name_desc}"
        elif transaction_type in ["renewal", "payment", "expense", "new_subscription"]: # If a valid DB type is passed directly
            db_type = transaction_type
            db_description = f"Transaction type: {transaction_type}" # Generic description
        else:
            # Fallback for unmapped transaction_type
            logging.warning(f"Unmapped transaction_type '{transaction_type}' received. Storing as 'payment' with original type in description.")
            db_type = "payment" # Default to 'payment' or choose another appropriate default
            db_description = f"Original type: {transaction_type}"

        final_transaction_date = transaction_date if transaction_date else start_date
        final_end_date = end_date

        # Date validation for start_date and final_transaction_date
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(final_transaction_date, '%Y-%m-%d')
        except ValueError as ve:
            logging.error(f"Invalid date format for start_date or transaction_date: {ve}", exc_info=True)
            return False, f"Invalid date format for start_date ('{start_date}') or transaction_date ('{final_transaction_date}')."

        if transaction_type == 'Group Class': # This logic seems to apply to 'new_subscription' or 'renewal' related to plans
            if final_end_date:
                try:
                    datetime.strptime(final_end_date, '%Y-%m-%d')
                except ValueError:
                    # If end_date is provided but invalid, it might be better to error out or log
                    logging.warning(f"Invalid end_date format '{final_end_date}' for Group Class. Will attempt to calculate if possible.")
                    final_end_date = None # Reset to trigger calculation if plan_id is present

            if not final_end_date: # Calculate if not provided or if it was invalid
                if not plan_id:
                    # If it's a group class, it should have a plan_id to calculate duration.
                    # If not, it's ambiguous how to set end_date.
                    logging.error("plan_id is required for Group Class if end_date is not supplied or invalid.")
                    return False, "plan_id is required for Group Class if end_date is not supplied or invalid."

                plan_details = self.get_plan_by_id(plan_id)
                if not plan_details:
                    return False, f"Plan with ID {plan_id} not found."

                # plan_details structure: id (0), name (1), duration (2), price (3), type (4)
                duration_days = plan_details[2]
                if duration_days is None or not isinstance(duration_days, int) or duration_days <=0:
                    logging.error(f"Invalid duration ({duration_days}) for plan ID {plan_id}. Cannot calculate end_date.")
                    return False, f"Invalid duration for plan ID {plan_id}. Cannot calculate end_date."

                try:
                    final_end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=duration_days)).strftime('%Y-%m-%d')
                except ValueError as ve: # Catch error from strptime if start_date was somehow bad despite earlier check
                    logging.error(f"Date calculation error for end_date: {ve}", exc_info=True)
                    return False, f"Error calculating end_date from start_date '{start_date}'."

        # For other types like 'Personal Training' (payment), 'expense', direct 'payment',
        # end_date might not be applicable or directly provided.
        # If final_end_date is still None here for such cases, it will be inserted as NULL.

        try:
            cursor = self.conn.cursor()

            sql = """
                INSERT INTO transactions
                (member_id, plan_id, transaction_date, amount, transaction_type, description, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            # Ensure 'type' in the SQL query above is changed to 'transaction_type'
            # if that's the actual column name in the transactions table.
            # Based on database.py, the column is 'transaction_type'.
            # The variable db_type should map to this column.
            params = (
                member_id,
                plan_id,
                final_transaction_date,
                db_amount, # Use integer amount
                db_type,
                db_description,
                start_date,
                final_end_date
            )

            cursor.execute(sql, params)
            self._update_member_join_date_if_earlier(member_id, start_date, cursor)
            self.conn.commit()
            self._update_member_status(member_id) # Update member status after successful transaction
            return True, "Transaction added successfully."
        except ValueError as ve:
            logging.error(f"Data validation or date parsing error in add_transaction: {ve}", exc_info=True)
            # It's possible some specific ValueError was not caught by earlier checks, e.g. if a date format was missed.
            return False, f"Data validation or date parsing error: {ve}"
        except sqlite3.Error as e:
            logging.error(f"Database error while adding transaction: {e}", exc_info=True)
            return False, f"Database error while adding transaction: {e}"

    def _update_member_status(self, member_id: int):
        """
        Updates the is_active status of a member based on their transactions.
        A member is active if they have any transaction whose end_date (calculated
        from start_date and plan_duration) is after the current date.
        """
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT t.start_date, p.duration
                FROM transactions t
                JOIN plans p ON t.plan_id = p.id
                WHERE t.member_id = ? AND t.plan_id IS NOT NULL
            """
            # Note: The original instructions mentioned p.duration_days, but the plans table schema
            # in the provided code uses 'duration'. Assuming 'duration' stores days.
            # Removed filter on transaction_type to consider all transactions with a valid plan.
            # Added 't.plan_id IS NOT NULL' to ensure only transactions linked to a plan are considered,
            # as transactions like direct PT session entries might not have a plan_id and thus no duration.

            cursor.execute(query, (member_id,))
            transactions = cursor.fetchall()

            today = date.today()
            is_currently_active = False

            for transaction_start_date_str, duration_days in transactions:
                if not transaction_start_date_str or duration_days is None:
                    logging.warning(f"Skipping transaction for member {member_id} due to missing start_date or duration_days.")
                    continue
                try:
                    start_date_obj = datetime.strptime(transaction_start_date_str, '%Y-%m-%d').date()
                    end_date_obj = start_date_obj + timedelta(days=duration_days)
                    if end_date_obj > today:
                        is_currently_active = True
                        break  # Found an active transaction, no need to check further
                except ValueError as ve:
                    logging.error(f"Date parsing error for member {member_id}, start_date '{transaction_start_date_str}': {ve}", exc_info=True)
                except TypeError as te: # Handles if duration_days is not an int/float
                    logging.error(f"Duration calculation error for member {member_id}, duration '{duration_days}': {te}", exc_info=True)


            # Update member's status
            update_status_query = "UPDATE members SET is_active = ? WHERE member_id = ?"
            cursor.execute(update_status_query, (1 if is_currently_active else 0, member_id))
            self.conn.commit()
            logging.info(f"Member {member_id} status updated to {'active' if is_currently_active else 'inactive'}.")

        except sqlite3.Error as e:
            logging.error(f"Database error in _update_member_status for member {member_id}: {e}", exc_info=True)
            # Optionally, re-raise or handle so the caller knows the update might have failed.
        except Exception as ex: # Catch any other unexpected errors
            logging.error(f"Unexpected error in _update_member_status for member {member_id}: {ex}", exc_info=True)


    def get_all_activity_for_member(self, member_id: int) -> list:
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT t.transaction_type,
                       CASE WHEN t.transaction_type = 'Group Class' THEN p.plan_name ELSE 'PT Session' END,
                       t.payment_date, t.start_date, t.end_date, t.amount_paid,
                       CASE WHEN t.transaction_type = 'Group Class' THEN t.payment_method ELSE CAST(t.sessions AS TEXT) || ' sessions' END,
                       t.transaction_id
                FROM transactions t LEFT JOIN plans p ON t.plan_id = p.plan_id
                WHERE t.member_id = ? ORDER BY t.start_date DESC;
            """
            cursor.execute(query, (member_id,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Database error fetching activity for member {member_id}: {e}", exc_info=True)
            return []

    def get_pending_renewals(self, year: int, month: int) -> list:
        if not (1 <= month <= 12): return []
        year_month_str = f"{year:04d}-{month:02d}"
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT m.client_name, m.phone, p.plan_name, t.end_date
                FROM transactions t
                JOIN members m ON t.member_id = m.member_id JOIN plans p ON t.plan_id = p.plan_id
                WHERE strftime('%Y-%m', t.end_date) = ? AND m.is_active = 1 AND t.transaction_type = 'Group Class'
                ORDER BY t.end_date ASC, m.client_name ASC;
            """
            cursor.execute(query, (year_month_str,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Database error fetching pending renewals for {year_month_str}: {e}", exc_info=True)
            return []

    def get_finance_report(self, year: int, month: int) -> float | None:
        if not (1 <= month <= 12): return None
        year_month_str = f"{year:04d}-{month:02d}"
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT SUM(amount) FROM transactions WHERE strftime('%Y-%m', transaction_date) = ?", (year_month_str,))
            result = cursor.fetchone()
            return float(result[0]) if result and result[0] is not None else 0.0
        except sqlite3.Error as e:
            logging.error(f"Database error for finance report {year_month_str}: {e}", exc_info=True)
            return None

    def get_member_by_phone(self, phone: str) -> tuple | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT member_id, client_name FROM members WHERE phone = ? AND is_active = 1", (phone,))
            return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"Database error fetching member by phone '{phone}': {e}", exc_info=True)
            return None

    def add_member_with_join_date(self, name: str, phone: str, join_date: str) -> int | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)", (name, phone, join_date))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError: # Phone likely exists
            return None
        except sqlite3.Error as e:
            logging.error(f"Database error adding member '{name}' with join date: {e}", exc_info=True)
            return None

    def get_plan_by_name_and_duration(self, name: str, duration: int) -> tuple | None: # Parameters renamed
        # duration_days = duration_months * 30 # Assuming duration is now directly in days as per schema
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                # Column names updated, is_active removed
                "SELECT id, name, duration, price, type FROM plans WHERE name = ? AND duration = ?",
                (name, duration) # Parameters match updated column names
            )
            return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"DB error fetching plan '{name}' dur {duration} days: {e}", exc_info=True) # Log updated
            return None

    def get_or_create_plan_id(self, name: str, duration: int, price: int, type_text: str) -> Optional[int]:
        """
        Retrieves the ID of an existing plan or creates a new one.

        The method first queries the database for a plan with the specified 'name'
        and 'duration'.
        - If a plan with the same name and duration is found, its ID is returned.
        - If no such plan exists, a new plan is created with the provided 'name',
          'duration', 'price', and 'type_text', and the ID of the new plan is returned.

        This approach helps prevent "UNIQUE constraint failed" errors when data migration
        or other processes attempt to add plans, assuming the relevant unique constraint
        involves at least 'name' and 'duration'.

        Args:
            name: The name of the plan.
            duration: The duration of the plan in days.
            price: The price of the plan. Used if creating a new plan.
            type_text: The type of the plan (e.g., 'GC', 'PT'). Used if creating a new plan.

        Returns:
            The ID of the existing or newly created plan, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        try:
            # Check if a plan with the same name and duration already exists
            cursor.execute("SELECT id FROM plans WHERE name = ? AND duration = ?", (name, duration))
            result = cursor.fetchone()
            if result:
                logging.debug(f"Found existing plan for name='{name}', duration={duration}. ID: {result[0]}")
                return result[0]
            else:
                # If it doesn't exist, insert the new plan
                logging.info(f"Creating new plan: name='{name}', duration={duration}, price={price}, type='{type_text}'")
                cursor.execute(
                    "INSERT INTO plans (name, duration, price, type) VALUES (?, ?, ?, ?)",
                    (name, duration, price, type_text)
                )
                self.conn.commit()
                new_plan_id = cursor.lastrowid
                logging.info(f"Created new plan with ID: {new_plan_id} (Name: '{name}', Duration: {duration} days)")
                return new_plan_id
        except sqlite3.IntegrityError as ie:
            # This specific catch can be useful if there's a race condition or
            # if the UNIQUE constraint is on something unexpected (e.g. name alone)
            # and the initial check passed.
            self.conn.rollback() # Rollback any pending transaction
            logging.error(f"Integrity error in get_or_create_plan_id for name='{name}', duration={duration}: {ie}. "
                          "This might indicate a conflict with an existing plan not caught by the initial check.", exc_info=True)
            # Attempt to fetch again, in case another process created it.
            # This is an optimistic recovery for race conditions.
            try:
                cursor.execute("SELECT id FROM plans WHERE name = ? AND duration = ?", (name, duration))
                result = cursor.fetchone()
                if result:
                    logging.warning(f"Found plan ID {result[0]} for name='{name}', duration={duration} after initial IntegrityError.")
                    return result[0]
                logging.error(f"Still no plan found for name='{name}', duration={duration} after IntegrityError and re-check.")
                return None
            except sqlite3.Error as final_e:
                logging.error(f"Further SQLite error after IntegrityError in get_or_create_plan_id for '{name}': {final_e}", exc_info=True)
                return None

        except sqlite3.Error as e:
            self.conn.rollback() # Rollback any pending transaction
            logging.error(f"General SQLite error in get_or_create_plan_id for name='{name}', duration={duration}: {e}", exc_info=True)
            return None

    def get_transactions_with_member_details(self, name_filter: str = None, phone_filter: str = None, join_date_filter: str = None) -> list:
        try:
            cursor = self.conn.cursor()
            query_params = []
            sql = """
                SELECT t.transaction_id, t.member_id, t.transaction_type, t.plan_id, t.transaction_date, t.start_date, t.end_date, t.amount, t.payment_method, t.sessions, m.client_name, m.phone, m.join_date, p.plan_name FROM transactions t JOIN members m ON t.member_id = m.member_id LEFT JOIN plans p ON t.plan_id = p.plan_id
            """
            conditions = []
            if name_filter: conditions.append("m.client_name LIKE ?"); query_params.append(f"%{name_filter}%")
            if phone_filter: conditions.append("m.phone LIKE ?"); query_params.append(f"%{phone_filter}%")
            if join_date_filter:
                try: datetime.strptime(join_date_filter, '%Y-%m-%d'); conditions.append("m.join_date = ?"); query_params.append(join_date_filter)
                except ValueError: logging.warning(f"Invalid join_date_filter format '{join_date_filter}'. Filter ignored.")
            if conditions: sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY t.transaction_id DESC"
            cursor.execute(sql, query_params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"DB error fetching transactions with member details: {e}", exc_info=True)
            return []

    def get_transactions_for_month(self, year: int, month: int) -> list:
        if not (1 <= month <= 12): return []
        year_str, month_str = str(year), f"{month:02d}"
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT t.transaction_id, m.client_name, t.transaction_date, t.start_date, t.end_date, t.amount, t.transaction_type,
                       CASE WHEN t.transaction_type = 'Group Class' THEN p.plan_name
                            WHEN t.transaction_type = 'Personal Training' THEN CAST(t.sessions AS TEXT) || ' sessions'
                            ELSE NULL END,
                       t.payment_method
                FROM transactions t JOIN members m ON t.member_id = m.member_id LEFT JOIN plans p ON t.plan_id = p.plan_id
                WHERE strftime('%Y', t.transaction_date) = ? AND strftime('%m', t.transaction_date) = ?
                ORDER BY t.transaction_date ASC, t.transaction_id ASC;
            """
            cursor.execute(query, (year_str, month_str))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"DB error in get_transactions_for_month for {year_str}-{month_str}: {e}", exc_info=True)
            return []

    def get_book_status(self, month_key: str) -> str: # YYYY-MM
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT status FROM monthly_book_status WHERE month_key = ?", (month_key,))
            result = cursor.fetchone()
            return "closed" if result and result[0] == "closed" else "open"
        except sqlite3.Error as e:
            logging.error(f"DB error fetching book status for {month_key}: {e}", exc_info=True)
            return "open" # Default to open on error

    def set_book_status(self, month_key: str, status: str) -> bool: # YYYY-MM
        if status not in ["open", "closed"]: return False
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO monthly_book_status (month_key, status) VALUES (?, ?)", (month_key, status))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"DB error setting book status for {month_key} to {status}: {e}", exc_info=True)
            return False

    def deactivate_member(self, member_id: int) -> Tuple[bool, str]:
        # TODO: Handle active transactions for the member (e.g., by updating their end dates or status) when deactivating.
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE members SET is_active = 0 WHERE member_id = ?", (member_id,))
            self.conn.commit()
            if cursor.rowcount > 0: return True, "Member deactivated successfully."
            return False, "Failed to deactivate member. Member not found."
        except sqlite3.Error as e:
            logging.error(f"DB error deactivating member {member_id}: {e}", exc_info=True)
            return False, f"Database error while deactivating member {member_id}: {e}"

    def delete_transaction(self, transaction_id: int) -> Tuple[bool, str]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT member_id, transaction_date FROM transactions WHERE transaction_id = ?", (transaction_id,))
            transaction_info = cursor.fetchone()
            if not transaction_info: return False, f"Transaction with ID {transaction_id} not found."

            # Existing code to get transaction_info...
            transaction_date_str = transaction_info[1] # Assuming transaction_date is at index 1
            transaction_month_key = datetime.strptime(transaction_date_str, '%Y-%m-%d').strftime('%Y-%m')
            if self.get_book_status(transaction_month_key) == "closed":
                return False, f"Cannot delete transaction. Books for {transaction_month_key} are closed."

            member_id_for_log, transaction_date_str_log = transaction_info # Renamed transaction_date_str to avoid conflict
            book_status_for_log, transaction_month_key_for_log = "open", "N/A"
            if transaction_date_str_log:
                try:
                    transaction_month_key_for_log = datetime.strptime(transaction_date_str_log, '%Y-%m-%d').strftime('%Y-%m')
                    # We already know the status if it was closed, this log is for other cases or if logic changes
                    book_status_for_log = self.get_book_status(transaction_month_key_for_log)
                except ValueError:
                    logging.warning(f"Invalid transaction_date format '{transaction_date_str_log}' for tx {transaction_id}. Cannot determine book status for logging.")

            cursor.execute("DELETE FROM transactions WHERE transaction_id = ?", (transaction_id,))
            self.conn.commit()

            if cursor.rowcount > 0:
                if book_status_for_log == "closed" and transaction_date_str:
                    logging.info(f"Transaction {transaction_id} (member_id: {member_id_for_log}) deleted from a closed period: {transaction_month_key_for_log}")
                return True, "Transaction deleted successfully."
            return False, f"Transaction with ID {transaction_id} not found or already deleted (zero rows affected)."
        except sqlite3.Error as e:
            logging.error(f"Database error deleting transaction {transaction_id}: {e}", exc_info=True)
            return False, f"Database error while deleting transaction {transaction_id}: {e}"

    def delete_plan(self, plan_id: int) -> tuple[bool, str]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM transactions WHERE plan_id = ? LIMIT 1", (plan_id,)) # Assuming plan_id in transactions still refers to id in plans
            if cursor.fetchone(): return False, "Plan is in use and cannot be deleted."

            cursor.execute("DELETE FROM plans WHERE id = ?", (plan_id,)) # Changed plan_id to id
            self.conn.commit()
            if cursor.rowcount > 0: return True, "Plan deleted successfully."
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

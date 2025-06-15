import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import os


class DatabaseManager:
    def __init__(self, db_path):
        """
        Initializes the DatabaseManager.

        Args:
            db_path (str): The path to the SQLite database file.
                           Assumes the path is relative to the 'kranos_reporter' directory.
        """
        # Construct the absolute path to the database file
        # Assuming this script is in kranos_reporter/app/
        # and the db is in kranos_reporter/db/
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_path)
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            # Potentially re-raise or handle more gracefully

    def _execute_query(self, query, params=None):
        """Helper function to execute a query and fetch all results."""
        if not self.conn:
            print("Database connection not established.")
            return None
        try:
            return pd.read_sql_query(query, self.conn, params=params)
        except sqlite3.Error as e:
            print(f"Error executing query: {e}")
            return None

    def generate_renewal_report(self, days_ahead):
        """
        Generates a report of members whose plans are due for renewal.

        Args:
            days_ahead (int): The number of days from today to look ahead for renewals.

        Returns:
            pandas.DataFrame: A DataFrame containing members' renewal information,
                              or None if an error occurs.
        """
        if not self.conn:
            print("Database connection not established.")
            return None

        today_date = datetime.now().date()
        future_date = today_date + timedelta(days=days_ahead)

        # This method assumes the following schema:
        # transactions table has:
        #   - end_date (TEXT, format 'YYYY-MM-DD')
        #   - type (TEXT, e.g., 'renewal', 'new_subscription')
        # members table has:
        #   - status (TEXT, e.g., 'active', 'inactive')

        query = """
            SELECT
                m.name AS member_name,
                m.phone AS member_phone,
                m.email AS member_email, -- ADDED member_email
                p.name AS plan_name,
                t.end_date AS plan_end_date
            FROM
                transactions t
            JOIN
                members m ON t.member_id = m.id
            JOIN
                plans p ON t.plan_id = p.id
            WHERE
                t.type = 'renewal'
                AND m.is_active = 1 -- UPDATED: Using is_active boolean column
                AND t.end_date >= ?
                AND t.end_date <= ?
            ORDER BY
                t.end_date ASC;
        """
        # Ensure dates are in 'YYYY-MM-DD' format for comparison with TEXT fields in SQLite
        today_str = today_date.strftime("%Y-%m-%d")
        future_date_str = future_date.strftime("%Y-%m-%d")

        try:
            df = pd.read_sql_query(
                query, self.conn, params=(today_str, future_date_str)
            )
            return df
        except sqlite3.Error as e:
            print(f"Error generating renewal report: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error

    def add_member(
        self, name, email, phone, membership_plan_id, join_date=None, is_active=True
    ):
        """
        Placeholder for adding a new member.
        (This will be implemented in a future task)
        """
        print(f"Placeholder: Adding member {name} (Not yet implemented).")
        # Example of how it might work:
        # query = """
        #     INSERT INTO members (name, email, phone, membership_plan_id, join_date, is_active)
        #     VALUES (?, ?, ?, ?, ?, ?)
        # """
        # params = (name, email, phone, membership_plan_id, join_date or datetime.now().date(), is_active)
        # try:
        #     cursor = self.conn.cursor()
        #     cursor.execute(query, params)
        #     self.conn.commit()
        #     return cursor.lastrowid
        # except sqlite3.Error as e:
        #     print(f"Error adding member: {e}")
        #     return None
        pass

    def add_member(
        self,
        name: str,
        email: str,
        phone: str,
        join_date: str,
        notes: str,
        is_active: bool = True,
    ):
        """Adds a new member to the database."""
        if not self.conn:
            print("Database connection not established.")
            return None
        if not name or not phone:  # Basic validation
            print("Error: Member name and phone cannot be empty.")
            raise ValueError("Member name and phone cannot be empty.")

        query = """
            INSERT INTO members (name, email, phone, join_date, notes, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (name, email, phone, join_date, notes, is_active)
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.lastrowid
        except (
            sqlite3.IntegrityError
        ) as e:  # E.g. if name were UNIQUE and a duplicate was added
            print(f"Error adding member due to integrity constraint: {e}")
            if self.conn:
                self.conn.rollback()
            # Potentially raise a custom exception or return a specific error indicator
            raise ValueError(f"Failed to add member: {e}")  # Raise so API can catch
        except sqlite3.Error as e:
            print(f"Error adding member: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    def get_plan_details(self, plan_id: int):
        """Fetches details (price, duration_days) for a specific plan."""
        if not self.conn:
            print("Database connection not established.")
            return None
        query = "SELECT price, duration_days FROM plans WHERE id = ?;"
        try:
            # Using a direct cursor execute for a single row result might be slightly more efficient
            # than pd.read_sql_query if we only need a few fields and one row.
            cursor = self.conn.cursor()
            cursor.execute(query, (plan_id,))
            plan_data = (
                cursor.fetchone()
            )  # Returns a tuple (price, duration_days) or None
            if plan_data:
                return {"price": plan_data[0], "duration_days": plan_data[1]}
            else:
                print(f"Plan ID {plan_id} not found.")
                return None
        except sqlite3.Error as e:
            print(f"Error fetching plan details for ID {plan_id}: {e}")
            return None

    def add_membership_transaction(
        self,
        member_id: int,
        plan_id: int,
        transaction_date_str: str,
        amount_paid: float,
        payment_method: str,
        notes: str,
        transaction_type: str = "new_subscription",
        recorded_by: str = "streamlit_app",
    ):
        """Adds a membership transaction and calculates start/end dates."""
        if not self.conn:
            print("Database connection not established.")
            raise ConnectionError(
                "Database connection not established."
            )  # Raise to inform API layer

        plan_details = self.get_plan_details(plan_id)
        if not plan_details:
            raise ValueError(f"Invalid plan_id: {plan_id} or plan details not found.")

        try:
            transaction_date_obj = datetime.strptime(
                transaction_date_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            raise ValueError(
                f"Invalid transaction_date format: {transaction_date_str}. Use YYYY-MM-DD."
            )

        start_date_obj = (
            transaction_date_obj  # Membership typically starts on transaction date
        )
        duration_days = plan_details.get("duration_days", 0)
        end_date_obj = start_date_obj + timedelta(days=duration_days)

        start_date_iso = start_date_obj.isoformat()
        end_date_iso = end_date_obj.isoformat()

        # Validate transaction_type against allowed values in DB schema
        allowed_types = [
            "renewal",
            "payment",
            "expense",
            "new_subscription",
            "membership_fee",
        ]
        if transaction_type not in allowed_types:
            # Default or raise error if type from UI isn't directly mappable
            # For now, let's assume 'new_subscription' if it's a common case from this method call
            # or require the caller (API) to ensure the type is valid.
            # The Streamlit form has "New Subscription", "Renewal", "Personal Training Session(s)", "Other Payment"
            # This mapping needs to be solid.
            # For now, if it's not in allowed_types, it will fail at DB level if not handled here.
            # Let's pass it through and let DB validate, or API layer should map it.
            # The task spec for add_transaction in DB layer does not include `type`.
            # This indicates `type` is part of the transaction data itself.
            pass

        query = """
            INSERT INTO transactions (member_id, plan_id, transaction_date, amount, type,
                                     notes, payment_method, start_date, end_date, recorded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            member_id,
            plan_id,
            transaction_date_str,
            amount_paid,
            transaction_type,
            notes,
            payment_method,
            start_date_iso,
            end_date_iso,
            recorded_by,
        )

        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding transaction: {e}")
            if self.conn:
                self.conn.rollback()
            raise ValueError(
                f"Failed to add transaction: {e}"
            )  # Propagate for API to handle

    def update_member(
        self,
        member_id: int,
        name: str,
        email: str,
        phone: str,
        join_date: str,
        notes: str,
        is_active: bool,
    ):
        """Updates an existing member in the database."""
        if not self.conn:
            print("Database connection not established.")
            return None  # Or raise an error
        if not name or not phone:  # Basic validation
            raise ValueError("Member name and phone cannot be empty.")

        query = """
            UPDATE members
            SET name = ?, email = ?, phone = ?, join_date = ?, notes = ?, is_active = ?
            WHERE id = ?
        """
        params = (name, email, phone, join_date, notes, is_active, member_id)
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.rowcount  # Number of rows updated
        except sqlite3.Error as e:
            print(f"Error updating member {member_id}: {e}")
            if self.conn:
                self.conn.rollback()
            # Propagate error for API layer to handle, or return specific error code/None
            raise ValueError(f"Failed to update member {member_id}: {e}")

    def set_member_active_status(self, member_id: int, is_active: bool):
        """Sets the active status of a member."""
        if not self.conn:
            print("Database connection not established.")
            return None  # Or raise an error

        query = "UPDATE members SET is_active = ? WHERE id = ?"
        params = (1 if is_active else 0, member_id)  # Store boolean as 1 or 0 in SQLite
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.rowcount  # Number of rows updated
        except sqlite3.Error as e:
            print(f"Error setting active status for member {member_id}: {e}")
            if self.conn:
                self.conn.rollback()
            raise ValueError(f"Failed to set active status for member {member_id}: {e}")

    def _parse_duration_str_to_days(self, duration_str):
        """
        Parses a duration string (e.g., "1 month", "30 days") into an integer number of days.
        Returns None if parsing fails.
        """
        if not duration_str or not isinstance(duration_str, str):
            return None

        duration_str = duration_str.lower().strip()
        parts = duration_str.split()

        if len(parts) != 2:
            return None

        value_str, unit = parts

        try:
            value = int(value_str)
        except ValueError:
            return None

        if unit in ["day", "days"]:
            return value
        elif unit in ["week", "weeks"]:
            return value * 7
        elif unit in ["month", "months"]:
            return value * 30  # Simplified assumption
        elif unit in ["year", "years"]:
            return value * 365  # Simplified assumption
        else:
            return None

    def add_plan(self, name, price, duration_str, type_str, is_active=True):
        """
        Adds a new plan to the database.
        Converts duration_str to days and maps type_str to DB schema values.

        Args:
            name (str): The name of the plan.
            price (int): The price of the plan.
            duration_str (str): The duration of the plan (e.g., "1 month", "30 days").
            type_str (str): The type of the plan (e.g., "Group Class", "Personal Training").
            is_active (bool): Whether the plan is active. Defaults to True.

        Returns:
            int: The ID of the newly added plan, or None if an error occurs.
        """
        if not self.conn:
            print("Database connection not established.")
            return None

        duration_days = self._parse_duration_str_to_days(duration_str)
        if duration_days is None:
            print(f"Error: Invalid duration string provided: {duration_str}")
            return None  # Or raise ValueError

        # Map frontend type_str to backend DB type
        db_plan_type = None
        if type_str == "Group Class":
            db_plan_type = "GC"
        elif type_str == "Personal Training":
            db_plan_type = "PT"
        # Add handling for 'Open Mat', 'Other' if DB schema is updated or map them if appropriate.
        # For now, if it's not GC or PT after mapping, it will likely fail DB check constraint.
        else:
            # Allowing direct 'GC' or 'PT' from API if already mapped, or other valid DB types
            if type_str in ["GC", "PT"]:
                db_plan_type = type_str
            else:
                print(
                    f"Error: Invalid plan type string provided: {type_str}. Must map to 'GC' or 'PT'."
                )
                return None  # Or raise ValueError

        query = """
            INSERT INTO plans (name, price, duration_days, type, is_active)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (name, price, duration_days, db_plan_type, is_active)
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding plan: {e}")
            # Rollback in case of error
            if self.conn:
                self.conn.rollback()
            return None

    def get_monthly_financial_report(self, month, year):
        """
        Fetches transactions for a specific month and year, and calculates total revenue.
        Assumes transaction types 'new_subscription', 'renewal', 'payment' contribute to revenue.
        """
        if not self.conn:
            print("Database connection not established.")
            return None

        # Construct date strings for the first and last day of the month
        # Ensure month and year are integers
        try:
            month = int(month)
            year = int(year)
            start_date_str = f"{year}-{month:02d}-01"
            # To find the last day, get the first day of the next month and subtract one day
            if month == 12:
                end_date_obj = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date_obj = datetime(year, month + 1, 1) - timedelta(days=1)
            end_date_str = end_date_obj.strftime("%Y-%m-%d")
        except ValueError:
            print(f"Invalid month or year for monthly report: {month}, {year}")
            return None

        query = """
            SELECT
                t.transaction_date,
                m.name AS member_name,
                p.name AS plan_name,
                t.amount AS amount_paid
            FROM
                transactions t
            JOIN
                members m ON t.member_id = m.id
            LEFT JOIN  -- Use LEFT JOIN for plans in case a payment isn't tied to a specific plan (e.g., 'Other Payment')
                plans p ON t.plan_id = p.id
            WHERE
                t.transaction_date >= ? AND
                t.transaction_date <= ? AND
                t.type IN ('new_subscription', 'renewal', 'payment') -- Revenue generating transactions
            ORDER BY
                t.transaction_date ASC;
        """

        total_revenue_query = """
            SELECT SUM(t.amount)
            FROM transactions t
            WHERE
                t.transaction_date >= ? AND
                t.transaction_date <= ? AND
                t.type IN ('new_subscription', 'renewal', 'payment');
        """

        try:
            transactions_df = pd.read_sql_query(
                query, self.conn, params=(start_date_str, end_date_str)
            )

            # Fetch total revenue
            cursor = self.conn.cursor()
            cursor.execute(total_revenue_query, (start_date_str, end_date_str))
            total_revenue_result = cursor.fetchone()
            total_revenue = (
                total_revenue_result[0]
                if total_revenue_result and total_revenue_result[0] is not None
                else 0.0
            )

            return {
                "transactions": transactions_df.to_dict(orient="records"),
                "total_revenue": total_revenue,
            }
        except sqlite3.Error as e:
            print(f"Error generating monthly financial report for {month}-{year}: {e}")
            return None  # Or an empty structure: {"transactions": [], "total_revenue": 0.0}
        except Exception as e:  # Catch other potential errors
            print(
                f"An unexpected error occurred while generating monthly report for {month}-{year}: {e}"
            )
            return None

    def update_plan(self, plan_id, name, price, duration_str, type_str):
        """
        Updates an existing plan in the database.
        Converts duration_str to days and maps type_str.
        Does not update is_active status (handled separately).
        """
        if not self.conn:
            print("Database connection not established.")
            return None

        duration_days = self._parse_duration_str_to_days(duration_str)
        if duration_days is None:
            print(f"Error: Invalid duration string provided: {duration_str}")
            # Return a specific value or raise error to distinguish in API layer
            raise ValueError(f"Invalid duration string: {duration_str}")

        db_plan_type = None
        if type_str == "Group Class":
            db_plan_type = "GC"
        elif type_str == "Personal Training":
            db_plan_type = "PT"
        elif type_str in ["GC", "PT"]:  # Allow direct GC/PT
            db_plan_type = type_str
        else:
            # This path should ideally be caught by API validation first,
            # but as a safeguard in db_manager:
            print(f"Error: Invalid plan type string for update: {type_str}")
            raise ValueError(
                f"Invalid plan type: {type_str}. Must map to 'GC' or 'PT'."
            )

        query = """
            UPDATE plans
            SET name = ?, price = ?, duration_days = ?, type = ?
            WHERE id = ?
        """
        # Note: is_active is NOT updated here.
        params = (name, price, duration_days, db_plan_type, plan_id)
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.rowcount  # Returns the number of rows updated
        except sqlite3.Error as e:
            print(f"Error updating plan {plan_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return None  # Indicates a database error (e.g. UNIQUE constraint)

    def delete_plan(self, plan_id):
        """
        Deletes a plan from the database.
        """
        if not self.conn:
            print("Database connection not established.")
            return None  # Indicates an issue like DB connection not available

        query = "DELETE FROM plans WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, (plan_id,))
            self.conn.commit()
            return cursor.rowcount  # Number of rows deleted
        except sqlite3.Error as e:
            print(f"Error deleting plan {plan_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return None  # Indicates a database error

    def set_plan_active_status(self, plan_id, is_active):
        """
        Sets the active status of a plan.
        """
        if not self.conn:
            print("Database connection not established.")
            return None

        query = "UPDATE plans SET is_active = ? WHERE id = ?"
        params = (is_active, plan_id)
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.rowcount  # Number of rows updated
        except sqlite3.Error as e:
            print(f"Error setting active status for plan {plan_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    def get_all_plans_details(self):
        """
        Fetches all plans with full details.
        Maps 'type' from DB ('GC', 'PT') to user-friendly strings.
        Returns 'duration_days' as is.
        """
        if not self.conn:
            print("Database connection not established.")
            return pd.DataFrame()  # Return empty DataFrame

        query = "SELECT id, name, price, duration_days, type, is_active FROM plans ORDER BY name ASC;"
        try:
            df = pd.read_sql_query(query, self.conn)

            # Map 'type' to user-friendly strings
            type_mapping = {"GC": "Group Class", "PT": "Personal Training"}
            df["type"] = (
                df["type"].map(type_mapping).fillna(df["type"])
            )  # Keep original if no mapping

            # Ensure is_active is boolean (pandas might make it 0/1 from SQLite)
            if "is_active" in df.columns:
                df["is_active"] = df["is_active"].astype(bool)
            return df
        except sqlite3.Error as e:
            print(f"Error fetching all plan details: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"An unexpected error occurred while fetching all plan details: {e}")
            return pd.DataFrame()

    def get_filtered_members(self, search_term=None, plan_type=None, status=None):
        """
        Fetches members based on provided filter criteria.

        Args:
            search_term (str, optional): Term to search for in member names.
            plan_type (str, optional): Filter by plan type (e.g., 'GC', 'PT'). 'All' means no filter.
            status (str, optional): Filter by member status ('Active', 'Inactive'). 'All' means no filter.

        Returns:
            pandas.DataFrame: A DataFrame containing filtered member data,
                              or an empty DataFrame if an error occurs or no members match.
        """
        if not self.conn:
            print("Database connection not established.")
            return pd.DataFrame()

        query_params = []
        # Base query joining members and plans table
        # Assuming members table has current_plan_id that is a FOREIGN KEY to plans.id
        # members table now has is_active (BOOLEAN stored as 0 or 1)
        base_query = """
            SELECT
                m.id AS member_id,
                m.name AS client_name, -- Changed to client_name to match streamlit expectations
                m.email AS email,
                m.phone AS phone,
                m.join_date,
                m.is_active, -- This will be 0 or 1
                m.notes, -- Added notes
                p.name AS plan_name,
                p.type AS plan_type,
                p.price AS plan_price,
                p.duration_days AS plan_duration
            FROM
                members m
            LEFT JOIN -- Assuming members.current_plan_id links to plans.id; if not, this join needs review
                plans p ON m.current_plan_id = p.id -- TODO: Verify members table has current_plan_id
        """

        conditions = []

        if search_term:
            # Search in name, email, or phone for flexibility
            conditions.append("(m.name LIKE ? OR m.email LIKE ? OR m.phone LIKE ?)")
            term = f"%{search_term}%"
            query_params.extend([term, term, term])

        if plan_type and plan_type.lower() != "all":
            # Map frontend plan type to DB plan type if necessary, e.g., "Group Class" to "GC"
            # For now, assuming plan_type is passed as 'GC' or 'PT' if filtered
            conditions.append("p.type = ?")
            query_params.append(plan_type)

        if status and status.lower() != "all":
            # Frontend sends "Active" or "Inactive"
            # DB stores is_active as 1 (True) or 0 (False)
            is_active_value = 1 if status.lower() == "active" else 0
            conditions.append("m.is_active = ?")
            query_params.append(is_active_value)
        # If status is 'All', no condition on is_active is added, so all members are fetched regardless of status.

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += " ORDER BY m.name ASC;"

        try:
            df = pd.read_sql_query(base_query, self.conn, params=tuple(query_params))
            return df
        except sqlite3.Error as e:
            print(f"Error fetching filtered members: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
        except Exception as e:  # Catch other potential errors, e.g. with pandas
            print(f"An unexpected error occurred while fetching filtered members: {e}")
            return pd.DataFrame()

    def get_member_details(self, member_id):
        """
        Fetches all details for a specific member.

        Args:
            member_id (int): The ID of the member.

        Returns:
            pandas.Series: A Series containing the member's details,
                           or None if an error occurs or member not found.
        """
        if not self.conn:
            print("Database connection not established.")
            return None

        # Fetch member details, including current_plan_id
        # The actual plan name can be fetched separately if needed or joined here
        query = """
            SELECT
                m.id AS member_id,
                m.name AS member_name,
                m.email,
                m.phone,
                m.join_date,
                m.current_plan_id,
                m.is_active,
                p.name AS plan_name
            FROM
                members m
            LEFT JOIN -- Assuming members.current_plan_id links to plans.id
                plans p ON m.current_plan_id = p.id -- TODO: Verify members table has current_plan_id field
            WHERE
                m.id = ?;
        """
        try:
            df = pd.read_sql_query(query, self.conn, params=(member_id,))
            if not df.empty:
                # Convert is_active to boolean for the Series
                member_series = df.iloc[
                    0
                ].copy()  # Use .copy() to avoid SettingWithCopyWarning
                if "is_active" in member_series:
                    member_series["is_active"] = bool(member_series["is_active"])
                return member_series
            else:
                return None
        except sqlite3.Error as e:
            print(f"Error fetching member details for ID {member_id}: {e}")
            return None
        except Exception as e:  # Catch other potential errors
            print(
                f"An unexpected error occurred while fetching member details for ID {member_id}: {e}"
            )
            return None

    def get_all_plans_for_selection(self):
        """
        Fetches all active plans for display in a selection widget.

        Returns:
            list: A list of tuples (plan_id, plan_name),
                  or an empty list if an error occurs or no active plans found.
        """
        if not self.conn:
            print("Database connection not established.")
            return []

        query = "SELECT id, name FROM plans WHERE is_active = 1 ORDER BY name ASC;"
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            plans = cursor.fetchall()  # Returns list of tuples
            return plans
        except sqlite3.Error as e:
            print(f"Error fetching plans for selection: {e}")
            return []
        except Exception as e:
            print(
                f"An unexpected error occurred while fetching plans for selection: {e}"
            )
            return []

    def get_member_transaction_history(self, member_id):
        """
        Fetches the transaction history for a specific member.

        Args:
            member_id (int): The ID of the member.

        Returns:
            pandas.DataFrame: A DataFrame containing the member's transaction history,
                              or an empty DataFrame if an error occurs or no transactions found.
        """
        if not self.conn:
            print("Database connection not established.")
            return pd.DataFrame()

        query = """
            SELECT
                t.id AS transaction_id,
                t.transaction_date,
                t.type AS transaction_type,
                p.name AS plan_name,
                t.amount,
                t.payment_method,
                t.start_date,
                t.end_date
            FROM
                transactions t
            JOIN
                plans p ON t.plan_id = p.id
            WHERE
                t.member_id = ?
            ORDER BY
                t.transaction_date DESC;
        """
        try:
            df = pd.read_sql_query(query, self.conn, params=(member_id,))
            return df
        except sqlite3.Error as e:
            print(f"Error fetching transaction history for member ID {member_id}: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(
                f"An unexpected error occurred while fetching transaction history for member ID {member_id}: {e}"
            )
            return pd.DataFrame()

    def get_filtered_transactions(
        self,
        start_date=None,
        end_date=None,
        member_name_search=None,
        transaction_type=None,
    ):
        """
        Fetches transactions based on provided filter criteria.

        Args:
            start_date (str, optional): Start date for filtering (YYYY-MM-DD).
            end_date (str, optional): End date for filtering (YYYY-MM-DD).
            member_name_search (str, optional): Term to search for in member names.
            transaction_type (str, optional): Filter by transaction type (e.g., 'New Subscription', 'Renewal').

        Returns:
            pandas.DataFrame: A DataFrame containing filtered transaction data,
                              or an empty DataFrame if an error occurs or no transactions match.
        """
        if not self.conn:
            print("Database connection not established.")
            return pd.DataFrame()

        query_params = []
        base_query = """
            SELECT
                t.id AS transaction_id,
                m.name AS member_name,
                p.name AS plan_name,
                t.transaction_date,
                t.amount,
                t.type AS transaction_type,
                t.payment_method,
                t.start_date AS membership_start_date,
                t.end_date AS membership_end_date
            FROM
                transactions t
            JOIN
                members m ON t.member_id = m.id
            JOIN
                plans p ON t.plan_id = p.id
        """
        conditions = []

        if start_date:
            conditions.append("t.transaction_date >= ?")
            query_params.append(start_date)
        if end_date:
            conditions.append("t.transaction_date <= ?")
            query_params.append(end_date)
        if member_name_search:
            conditions.append("m.name LIKE ?")
            query_params.append(f"%{member_name_search}%")
        if transaction_type and transaction_type.lower() != "all":
            conditions.append("t.type = ?")
            query_params.append(transaction_type)

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += " ORDER BY t.transaction_date DESC;"

        try:
            df = pd.read_sql_query(base_query, self.conn, params=tuple(query_params))
            return df
        except sqlite3.Error as e:
            print(f"Error fetching filtered transactions: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(
                f"An unexpected error occurred while fetching filtered transactions: {e}"
            )
            return pd.DataFrame()

    def perform_book_closing(self, month, year):
        """
        Placeholder for performing the book closing operations for a given month and year.
        Actual financial logic for summarizing transactions, generating reports,
        or marking a period as closed would go here.

        Args:
            month (int): The month (1-12) for which to close books.
            year (int): The year for which to close books.

        Returns:
            bool: True if the operation was notionally successful, False otherwise.
        """
        if not self.conn:
            print("Database connection not established.")
            return False

        print(f"Attempting to close books for {month:02d}-{year}.")
        # In a real implementation, this would involve:
        # 1. Querying transactions for the given month and year.
        # 2. Calculating summaries (total revenue, new members, renewals, etc.).
        # 3. Storing these summaries in a dedicated table (e.g., monthly_financial_summary).
        # 4. Potentially marking transactions as "closed" or "accounted_for".
        # 5. Error handling and transaction management (commit/rollback).

        # For this placeholder, we'll just log the action.
        # We could simulate creating a dummy record or performing a simple check.
        try:
            # Example: Log to a hypothetical table or just print
            # cursor = self.conn.cursor()
            # cursor.execute("INSERT INTO monthly_closures (year, month, status) VALUES (?, ?, ?)", (year, month, 'CLOSED'))
            # self.conn.commit()
            print(
                f"Successfully closed books for {month:02d}-{year} (Placeholder Action)."
            )
            return True
        except sqlite3.Error as e:
            print(f"Error during book closing for {month:02d}-{year}: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        except Exception as e:
            print(
                f"An unexpected error occurred during book closing for {month:02d}-{year}: {e}"
            )
            return False

    def add_renewal_transaction(
        self, member_id, plan_id, transaction_date, amount, payment_method
    ):
        """
        Placeholder for adding a renewal transaction.
        (This will be implemented in a future task)
        """
        print(
            f"Placeholder: Adding renewal for member_id {member_id} (Not yet implemented)."
        )
        # Example of how it might work:
        # query = """
        #     INSERT INTO transactions (member_id, plan_id, transaction_date, amount, payment_method)
        #     VALUES (?, ?, ?, ?, ?)
        # """
        # params = (member_id, plan_id, transaction_date, amount, payment_method)
        # try:
        #     cursor = self.conn.cursor()
        #     cursor.execute(query, params)
        #     self.conn.commit()
        #     return cursor.lastrowid
        # except sqlite3.Error as e:
        #     print(f"Error adding transaction: {e}")
        #     return None
        pass

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            print("Database connection closed.")


# Example Usage (for testing purposes, can be removed or commented out later)
if __name__ == "__main__":
    # This assumes kranos_gym.db is in ../db/ relative to this file
    # Adjust the path if your structure is different or if you run this from another location.
    db_manager = DatabaseManager(db_path="db/kranos_gym.db")

    if db_manager.conn:
        print("Successfully connected to the database.")

        # Example: Generate a report for renewals in the next 30 days
        renewal_report_df = db_manager.generate_renewal_report(days_ahead=30)
        if renewal_report_df is not None:
            print("\\nRenewal Report (next 30 days):")
            if renewal_report_df.empty:
                print("No upcoming renewals found.")
            else:
                print(renewal_report_df.to_string())

        db_manager.close()
    else:
        print("Failed to connect to the database.")

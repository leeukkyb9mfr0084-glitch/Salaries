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
                AND m.status = 'active'
                AND t.end_date >= ?
                AND t.end_date <= ?
            ORDER BY
                t.end_date ASC;
        """
        # Ensure dates are in 'YYYY-MM-DD' format for comparison with TEXT fields in SQLite
        today_str = today_date.strftime('%Y-%m-%d')
        future_date_str = future_date.strftime('%Y-%m-%d')

        try:
            df = pd.read_sql_query(query, self.conn, params=(today_str, future_date_str))
            return df
        except sqlite3.Error as e:
            print(f"Error generating renewal report: {e}")
            return pd.DataFrame() # Return empty DataFrame on error


    def add_member(self, name, email, phone, membership_plan_id, join_date=None, is_active=True):
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

    def add_plan(self, name, price, duration_days, type, is_active=True):
        """
        Adds a new plan to the database.

        Args:
            name (str): The name of the plan.
            price (int): The price of the plan.
            duration_days (int): The duration of the plan in days.
            type (str): The type of the plan (e.g., 'GC', 'PT').
            is_active (bool): Whether the plan is active. Defaults to True.

        Returns:
            int: The ID of the newly added plan, or None if an error occurs.
        """
        if not self.conn:
            print("Database connection not established.")
            return None

        query = """
            INSERT INTO plans (name, price, duration_days, type, is_active)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (name, price, duration_days, type, is_active)
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
        # Assuming members table has is_active (INTEGER/BOOLEAN) and plans table has type (TEXT)
        base_query = """
            SELECT
                m.id AS member_id,
                m.name AS member_name,
                m.email AS member_email,
                m.phone AS member_phone,
                m.join_date,
                m.is_active,
                p.name AS plan_name,
                p.type AS plan_type,
                p.price AS plan_price,
                p.duration_days AS plan_duration
            FROM
                members m
            LEFT JOIN
                plans p ON m.current_plan_id = p.id
        """

        conditions = []

        if search_term:
            conditions.append("m.name LIKE ?")
            query_params.append(f"%{search_term}%")

        if plan_type and plan_type.lower() != 'all':
            conditions.append("p.type = ?")
            query_params.append(plan_type)

        if status and status.lower() != 'all':
            if status.lower() == 'active':
                conditions.append("m.is_active = 1")
            elif status.lower() == 'inactive':
                conditions.append("m.is_active = 0")
            # No else needed, if status is something else and not 'all', it's ignored.
            # Or, you could add validation for status values.

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += " ORDER BY m.name ASC;"

        try:
            df = pd.read_sql_query(base_query, self.conn, params=tuple(query_params))
            return df
        except sqlite3.Error as e:
            print(f"Error fetching filtered members: {e}")
            return pd.DataFrame() # Return empty DataFrame on error
        except Exception as e: # Catch other potential errors, e.g. with pandas
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
            LEFT JOIN
                plans p ON m.current_plan_id = p.id
            WHERE
                m.id = ?;
        """
        try:
            df = pd.read_sql_query(query, self.conn, params=(member_id,))
            if not df.empty:
                return df.iloc[0]  # Return the first row as a Series
            else:
                return None
        except sqlite3.Error as e:
            print(f"Error fetching member details for ID {member_id}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while fetching member details for ID {member_id}: {e}")
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
            plans = cursor.fetchall() # Returns list of tuples
            return plans
        except sqlite3.Error as e:
            print(f"Error fetching plans for selection: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred while fetching plans for selection: {e}")
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
            print(f"An unexpected error occurred while fetching transaction history for member ID {member_id}: {e}")
            return pd.DataFrame()

    def get_filtered_transactions(self, start_date=None, end_date=None, member_name_search=None, transaction_type=None):
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
        if transaction_type and transaction_type.lower() != 'all':
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
            print(f"An unexpected error occurred while fetching filtered transactions: {e}")
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
            print(f"Successfully closed books for {month:02d}-{year} (Placeholder Action).")
            return True
        except sqlite3.Error as e:
            print(f"Error during book closing for {month:02d}-{year}: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        except Exception as e:
            print(f"An unexpected error occurred during book closing for {month:02d}-{year}: {e}")
            return False

    def add_renewal_transaction(self, member_id, plan_id, transaction_date, amount, payment_method):
        """
        Placeholder for adding a renewal transaction.
        (This will be implemented in a future task)
        """
        print(f"Placeholder: Adding renewal for member_id {member_id} (Not yet implemented).")
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
if __name__ == '__main__':
    # This assumes kranos_gym.db is in ../db/ relative to this file
    # Adjust the path if your structure is different or if you run this from another location.
    db_manager = DatabaseManager(db_path='db/kranos_gym.db')

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

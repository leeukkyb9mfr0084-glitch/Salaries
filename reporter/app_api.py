from .database_manager import DatabaseManager
from typing import Tuple, Optional, List, Any, Dict  # Added List, Any, Dict
import sqlite3  # Required for type hinting Connection


class AppAPI:
    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initializes the AppAPI with a database connection.

        Args:
            db_connection: An active sqlite3.Connection object.
        """
        self.db_manager = DatabaseManager(db_connection)

    # --- Member Methods ---
    def get_all_members(self) -> List[tuple]:
        """
        Retrieves all active members.

        Returns:
            A list of tuples, where each tuple represents a member
            (member_id, client_name, phone, join_date, is_active).
        """
        return self.db_manager.get_all_members()

    def search_members(self, query: str) -> List[tuple]:
        """
        Searches for members by name or phone number.

        Args:
            query: The search query (name or phone number).

        Returns:
            A list of matching member tuples.
        """
        num_digits = sum(c.isdigit() for c in query)
        if num_digits > len(query) / 2 and len(query) >= 7:
            return self.db_manager.get_all_members(phone_filter=query)
        else:
            return self.db_manager.get_all_members(name_filter=query)

    def add_member(
        self, name: str, phone: str, join_date: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Adds a new member to the database.

        Args:
            name: The name of the member.
            phone: The phone number of the member (must be unique).
            join_date: The date the member joined (YYYY-MM-DD). Optional.

        Returns:
            A tuple (success_status, message).
        """
        return self.db_manager.add_member_to_db(name, phone, join_date)

    def add_member_with_join_date(
        self, name: str, phone: str, join_date: str
    ) -> Optional[int]:
        """
        Adds a new member with a specific join date.

        Args:
            name: The name of the member.
            phone: The phone number of the member.
            join_date: The date the member joined (YYYY-MM-DD).

        Returns:
            The ID of the newly added member, or None if an error occurred (e.g., phone exists).
        """
        return self.db_manager.add_member_with_join_date(name, phone, join_date)

    def deactivate_member(self, member_id: int) -> Tuple[bool, str]:
        """
        Deactivates a member in the database.

        Args:
            member_id: The ID of the member to deactivate.

        Returns:
            A tuple (success_status, message).
        """
        return self.db_manager.deactivate_member(member_id)

    def get_member_by_phone(self, phone: str) -> Optional[tuple]:
        """
        Retrieves a member by their phone number.

        Args:
            phone: The phone number to search for.

        Returns:
            A tuple representing the member (member_id, client_name) if found, else None.
        """
        return self.db_manager.get_member_by_phone(phone)

    def get_member_by_id(self, member_id: int) -> Optional[tuple]:
        """
        Retrieves a specific member by their ID.
        The member tuple includes: (member_id, client_name, phone, join_date, is_active (bool)).

        Args:
            member_id: The ID of the member.

        Returns:
            A tuple representing the member if found, else None.
        """
        return self.db_manager.get_member_by_id(member_id)

    def update_member(
        self, member_id: int, name: str, phone: str, join_date: str, is_active: bool
    ) -> Tuple[bool, str]:
        """
        Updates an existing member's details.

        Args:
            member_id: The ID of the member to update.
            name: The new name for the member.
            phone: The new phone number for the member.
            join_date: The new join date for the member (YYYY-MM-DD).
            is_active: The new active status for the member (True or False).

        Returns:
            A tuple (success_status, message).
        """
        return self.db_manager.update_member(member_id, name, phone, join_date, is_active)

    def get_filtered_members(
        self, name_query: Optional[str] = None, status: Optional[str] = None
    ) -> List[tuple]:
        """
        Retrieves members, optionally filtered by name and status.

        Args:
            name_query: Optional partial name to filter by.
            status: Optional status to filter by ("Active" or "Inactive").

        Returns:
            A list of member tuples (member_id, client_name, phone, join_date, is_active (bool)).
        """
        return self.db_manager.get_filtered_members(name_query, status)

    # --- Plan Methods ---
    def get_all_plans(self) -> List[tuple]:
        """
        Retrieves all plans from the database, including their active status.
        Each plan is a tuple: (id, name, duration, price, type, is_active).

        Returns:
            A list of tuples representing all plans.
        """
        return self.db_manager.get_all_plans()

    def add_plan(
        self, name: str, duration_days: int, price: int, type_text: str
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Adds a new plan by calling the DatabaseManager.

        Args:
            name: The name of the plan.
            duration_days: The duration of the plan in days.
            price: The price of the plan.
            type_text: The type or category of the plan (e.g., 'GC', 'PT').

        Returns:
            A tuple mirroring DatabaseManager.add_plan's return:
            - bool: True if successful, False otherwise.
            - str: Success or error message.
            - Optional[int]: The new plan's ID if successful, else None.
        """
        return self.db_manager.add_plan(name, duration_days, price, type_text)

    def update_plan(
        self, plan_id: int, name: str, duration_days: int, price: int, type_text: str, is_active: Optional[bool] = None
    ) -> Tuple[bool, str]:
        """
        Updates an existing plan.

        Args:
            plan_id: The ID of the plan to update.
            name: The new name for the plan.
            duration_days: The new duration in days.
            price: The new price for the plan.
            type_text: The new type for the plan.
            is_active: Optional. The new active status for the plan (True or False).

        Returns:
            A tuple (success_status, message).
        """
        return self.db_manager.update_plan(
            plan_id, name, duration_days, price, type_text, is_active
        )

    def get_plan_by_id(self, plan_id: int) -> Optional[tuple]:
        """
        Retrieves a specific plan by its ID.
        The plan tuple includes: (id, name, duration, price, type, is_active).

        Args:
            plan_id: The ID of the plan.

        Returns:
            A tuple representing the plan if found, else None.
        """
        return self.db_manager.get_plan_by_id(plan_id)

    def delete_plan(self, plan_id: int) -> Tuple[bool, str]:
        """
        Deletes a plan from the database.

        Args:
            plan_id: The ID of the plan to delete.

        Returns:
            A tuple (success_status, message).
        """
        return self.db_manager.delete_plan(plan_id)

    # --- Transaction Methods ---
    def add_transaction(
        self,
        transaction_type: str,
        member_id: int,
        start_date: str,
        amount_paid: float,
        plan_id: Optional[int] = None,
        sessions: Optional[int] = None,
        payment_method: Optional[str] = None,
        payment_date: Optional[str] = None,  # This is the transaction_date
        end_date: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Adds a new transaction.

        Args:
            transaction_type: Type of transaction (e.g., 'new_subscription', 'renewal', 'payment', 'expense').
            member_id: ID of the member associated with the transaction.
            start_date: Start date of the service or subscription (YYYY-MM-DD).
            amount_paid: The amount paid for the transaction.
            plan_id: Optional ID of the plan, if applicable.
            sessions: Optional number of sessions, if applicable (e.g. for some types of plans or legacy data).
            payment_method: Optional method of payment.
            payment_date: Optional date of payment (YYYY-MM-DD). If None, start_date is used. This is treated as transaction_date.
            end_date: Optional end date of the service or subscription (YYYY-MM-DD). Calculated if not provided for new_subscription/renewal with a plan.

        Returns:
            A tuple (success_status, message).
        """
        return self.db_manager.add_transaction(
            transaction_type=transaction_type,
            member_id=member_id,
            start_date=start_date,
            amount=amount_paid,  # Renamed argument
            plan_id=plan_id,
            sessions=sessions,
            payment_method=payment_method,
            transaction_date=payment_date,  # Renamed argument
            end_date=end_date,
        )

    def get_all_activity_for_member(self, member_id: int) -> List[tuple]:
        """
        Retrieves all transaction activities for a specific member.
        Each activity is a tuple: (transaction_id, transaction_type, description,
        transaction_date, start_date, end_date, amount, plan_name, payment_method, sessions).

        Args:
            member_id: The ID of the member.

        Returns:
            A list of tuples representing member activities.
        """
        return self.db_manager.get_all_activity_for_member(member_id)

    def get_transactions_with_member_details(
        self,
        name_filter: Optional[str] = None,
        phone_filter: Optional[str] = None,
        join_date_filter: Optional[str] = None,
    ) -> List[tuple]:
        """
        Retrieves transactions joined with member details, with optional filters.

        Args:
            name_filter: Optional filter for member name (case-insensitive, partial match).
            phone_filter: Optional filter for member phone (partial match).
            join_date_filter: Optional filter for member join date (exact match YYYY-MM-DD).

        Returns:
            A list of tuples, each representing a transaction with member details.
        """
        return self.db_manager.get_transactions_with_member_details(
            name_filter, phone_filter, join_date_filter
        )

    def get_transactions_for_month(self, year: int, month: int) -> List[tuple]:
        """
        Retrieves all transactions for a specific month and year.
        Each transaction tuple includes: (transaction_id, client_name, transaction_date,
        start_date, end_date, amount, transaction_type, description, plan_name,
        payment_method, sessions).

        Args:
            year: The year (e.g., 2023).
            month: The month (1-12).

        Returns:
            A list of transaction tuples for the specified month.
        """
        return self.db_manager.get_transactions_for_month(year, month)

    def delete_transaction(self, transaction_id: int) -> Tuple[bool, str]:
        """
        Deletes a transaction.

        Args:
            transaction_id: The ID of the transaction to delete.

        Returns:
            A tuple (success_status, message).
        """
        return self.db_manager.delete_transaction(transaction_id)

    def get_member_id_from_transaction(self, transaction_id: int) -> Optional[int]:
        """
        Retrieves the member_id associated with a given transaction_id.

        Args:
            transaction_id: The ID of the transaction.

        Returns:
            The member_id if found, else None.
        """
        return self.db_manager.get_member_id_from_transaction(transaction_id)

    def get_transactions_filtered(
        self,
        member_id: Optional[int] = None,
        plan_id: Optional[int] = None,
        start_date_filter: Optional[str] = None,
        end_date_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[tuple]:
        """
        Retrieves transactions with optional filters.

        Args:
            member_id: Optional member ID to filter by.
            plan_id: Optional plan ID to filter by.
            start_date_filter: Optional start date for transaction date range (YYYY-MM-DD).
            end_date_filter: Optional end date for transaction date range (YYYY-MM-DD).
            limit: Maximum number of transactions to return.

        Returns:
            A list of transaction tuples.
            Each tuple: (transaction_id, transaction_date, member_name, plan_name, amount, payment_method, description, start_date, end_date)
        """
        return self.db_manager.get_transactions_filtered(
            member_id, plan_id, start_date_filter, end_date_filter, limit
        )

    # --- Reporting & Book Status Methods ---
    def get_pending_renewals(self, year: int, month: int) -> List[tuple]:
        """
        Retrieves pending renewals for a specific month and year.
        Each renewal is a tuple: (client_name, phone, plan_name, end_date).

        Args:
            year: The year.
            month: The month (1-12).

        Returns:
            A list of tuples representing pending renewals.
        """
        return self.db_manager.get_pending_renewals(year, month)

    def get_finance_report(self, year: int, month: int) -> Optional[float]:
        """
        Calculates the total income for a specific month and year.

        Args:
            year: The year.
            month: The month (1-12).

        Returns:
            The total income as a float, or None if an error occurs. Returns 0.0 if no transactions.
        """
        return self.db_manager.get_finance_report(year, month)

    def get_book_status(self, month_key: str) -> str:
        """
        Gets the booking status for a given month.

        Args:
            month_key: The month key in 'YYYY-MM' format.

        Returns:
            'open' or 'closed'. Defaults to 'open' on error.
        """
        return self.db_manager.get_book_status(month_key)

    def set_book_status(self, month_key: str, status: str) -> bool:
        """
        Sets the booking status for a given month.

        Args:
            month_key: The month key in 'YYYY-MM' format.
            status: The status to set ('open' or 'closed').

        Returns:
            True if successful, False otherwise.
        """
        return self.db_manager.set_book_status(month_key, status)

    # --- Helper/Utility Methods (already in DB manager, exposing via API if needed) ---
    # Example: get_or_create_plan_id might be useful if UI wants to dynamically manage plans.
    # For now, keeping API surface minimal and adding as needed.
    # def get_or_create_plan_id(self, plan_name: str, duration_days: int):
    #     return self.db_manager.get_or_create_plan_id(plan_name, duration_days)

# Added List, Any to typing imports.
# Corrected AppAPI.update_plan signature and call.
# Added docstrings and type hints to all methods in AppAPI.
# Confirmed no specific PT-related API endpoints to remove.
# The 'sessions' parameter in add_transaction is passed through; its deprecation is a broader issue.
# The 'is_active' flag for plans is handled in DBManager and data flows to AppAPI.
# Parameter name mismatches between AppAPI.add_transaction and DBManager.add_transaction call were fixed.
# Corrected INSERT statement in DBManager.add_transaction to include payment_method and sessions.
# Refactored queries in DBManager (get_all_activity_for_member, get_transactions_for_month, get_pending_renewals)
# to remove outdated 'Group Class'/'Personal Training' transaction_type logic and use t.description or p.name.
# Corrected join conditions from p.plan_id to p.id in DBManager queries.
# Updated DBManager.get_plan_by_id and get_all_plans to select is_active from plans table.
# Removed PT-specific validation and logic from DBManager.add_transaction.
# Standardized transaction_type handling in DBManager.add_transaction.
# Generalized end_date calculation in DBManager.add_transaction.

import sqlite3
from datetime import datetime, timedelta

def create_membership(db_path: str, member_id: int, plan_id: int, transaction_amount: float, start_date_str: str) -> Tuple[bool, str]:
    """
    Creates a new membership, deactivates existing ones, and records the transaction.

    Args:
        db_path: Path to the SQLite database file.
        member_id: The ID of the member.
        plan_id: The ID of the plan.
        transaction_amount: The amount paid for the transaction.
        start_date_str: The start date of the membership (YYYY-MM-DD).

    Returns:
        A tuple (success_status, message).
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Fetch plan duration
        cursor.execute("SELECT duration FROM plans WHERE id = ?", (plan_id,))
        plan_row = cursor.fetchone()
        if not plan_row:
            return False, "Plan not found."
        plan_duration_days = plan_row[0]

        # 2. Determine transaction_type
        cursor.execute("SELECT 1 FROM memberships WHERE member_id = ? AND is_active = 1", (member_id,))
        existing_active_membership = cursor.fetchone()
        transaction_type = 'Renewal' if existing_active_membership else 'New'

        # 3. Deactivate existing active memberships for this member
        cursor.execute("UPDATE memberships SET is_active = 0 WHERE member_id = ? AND is_active = 1", (member_id,))

        # 4. Calculate end_date
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = start_date + timedelta(days=plan_duration_days)
        end_date_str = end_date.strftime("%Y-%m-%d")

        # 5. Insert into memberships table
        cursor.execute(
            """
            INSERT INTO memberships (member_id, plan_id, start_date, end_date, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (member_id, plan_id, start_date_str, end_date_str),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return False, "Failed to create new membership entry."

        # 6. Insert into transactions table
        # transaction_date is the start_date_str for new memberships/renewals
        cursor.execute(
            """
            INSERT INTO transactions (member_id, plan_id, transaction_type, amount, transaction_date, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (member_id, plan_id, transaction_type, transaction_amount, start_date_str, start_date_str, end_date_str),
        )
        if cursor.rowcount == 0:
            conn.rollback() # Rollback if transaction insert fails
            return False, "Failed to create transaction entry."

        conn.commit()
        return True, f"Membership created successfully. Type: {transaction_type}."

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        return False, f"Database error: {e}"
    except ValueError as e: # For date parsing errors
        return False, f"Date error: {e}"
    finally:
        if conn:
            conn.close()

def update_membership(db_path: str, membership_id: int, start_date_str: str, end_date_str: str, is_active_bool: bool) -> Tuple[bool, str]:
    """
    Updates an existing membership's start date, end date, and active status.

    Args:
        db_path: Path to the SQLite database file.
        membership_id: The ID of the membership to update.
        start_date_str: The new start date (YYYY-MM-DD).
        end_date_str: The new end date (YYYY-MM-DD).
        is_active_bool: The new active status (True or False).

    Returns:
        A tuple (success_status, message).
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Validate date strings format (optional, but good practice)
        try:
            datetime.strptime(start_date_str, "%Y-%m-%d")
            datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            return False, "Invalid date format. Please use YYYY-MM-DD."

        is_active_int = 1 if is_active_bool else 0

        cursor.execute(
            "UPDATE memberships SET start_date = ?, end_date = ?, is_active = ? WHERE id = ?",
            (start_date_str, end_date_str, is_active_int, membership_id)
        )
        conn.commit()

        if cursor.rowcount > 0:
            return True, "Membership updated successfully."
        else:
            return False, "Membership not found or no changes made."

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        return False, f"Database error: {e}"
    finally:
        if conn:
            conn.close()

def delete_membership(db_path: str, membership_id: int) -> Tuple[bool, str]:
    """
    Deactivates a membership (soft delete).

    Args:
        db_path: Path to the SQLite database file.
        membership_id: The ID of the membership to deactivate.

    Returns:
        A tuple (success_status, message).
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("UPDATE memberships SET is_active = 0 WHERE id = ?", (membership_id,))
        conn.commit()

        if cursor.rowcount > 0:
            return True, "Membership deactivated successfully."
        else:
            return False, "Membership not found."

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        return False, f"Database error: {e}"
    finally:
        if conn:
            conn.close()

def get_all_memberships_for_view(
    db_path: str,
    name_filter: Optional[str] = None,
    phone_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves memberships joined with member and plan details, with optional filters.
    Returns data as a list of dictionaries for UI display.

    Args:
        db_path: Path to the SQLite database file.
        name_filter: Optional filter for member name (case-insensitive, partial match).
        phone_filter: Optional filter for member phone (partial match).
        status_filter: Optional status to filter by ("Active" or "Inactive").

    Returns:
        A list of dictionaries, each representing a membership view record.
    """
    conn = None
    results = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        cursor = conn.cursor()

        base_query = """
            SELECT
                ms.id as membership_id,
                m.client_name,
                m.phone,
                p.name AS plan_name,
                ms.start_date,
                ms.end_date,
                ms.is_active
            FROM
                members m
                JOIN memberships ms ON m.member_id = ms.member_id
                JOIN plans p ON ms.plan_id = p.id
        """

        conditions = []
        params = []

        if name_filter:
            conditions.append("m.client_name LIKE ?")
            params.append(f"%{name_filter}%")

        if phone_filter:
            conditions.append("m.phone LIKE ?")
            params.append(f"%{phone_filter}%")

        if status_filter:
            if status_filter.lower() == "active":
                conditions.append("ms.is_active = 1")
            elif status_filter.lower() == "inactive":
                conditions.append("ms.is_active = 0")
            # If status_filter is something else, it's ignored

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += " ORDER BY ms.start_date DESC" # Show recent ones first

        cursor.execute(base_query, params)
        rows = cursor.fetchall()

        for row in rows:
            results.append(
                {
                    "membership_id": row["membership_id"],
                    "client_name": row["client_name"],
                    "phone": row["phone"],
                    "plan_name": row["plan_name"],
                    "start_date": row["start_date"],
                    "end_date": row["end_date"],
                    "status": "Active" if row["is_active"] == 1 else "Inactive",
                }
            )

    except sqlite3.Error as e:
        print(f"Database error in get_all_memberships_for_view: {e}")
        # Optionally, re-raise or handle more gracefully
    finally:
        if conn:
            conn.close()
    return results

def get_active_members_for_dropdown(db_path: str) -> List[Tuple[int, str]]:
    """
    Retrieves active members (ID and name) for dropdown population.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A list of tuples, where each tuple is (member_id, client_name).
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Fetches members that are marked as active
        cursor.execute("SELECT member_id, client_name FROM members WHERE is_active = 1 ORDER BY client_name ASC")
        members = cursor.fetchall()
        return members
    except sqlite3.Error as e:
        print(f"Database error in get_active_members_for_dropdown: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_active_plans_for_dropdown(db_path: str) -> List[Tuple[int, str]]:
    """
    Retrieves active plans (ID and name) for dropdown population.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A list of tuples, where each tuple is (plan_id, plan_name).
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Fetches plans that are marked as active
        cursor.execute("SELECT id, name FROM plans WHERE is_active = 1 ORDER BY name ASC")
        plans = cursor.fetchall()
        return plans
    except sqlite3.Error as e:
        print(f"Database error in get_active_plans_for_dropdown: {e}")
        return []
    finally:
        if conn:
            conn.close()

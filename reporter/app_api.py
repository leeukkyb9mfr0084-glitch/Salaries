from .database_manager import DatabaseManager

import sqlite3 # Required for type hinting Connection

class AppAPI:
    def __init__(self, db_connection: sqlite3.Connection):
        # The DatabaseManager now correctly receives a connection object.
        self.db_manager = DatabaseManager(db_connection)

    # --- Member Methods ---
    def get_all_members(self):
        return self.db_manager.get_all_members()

    def search_members(self, query: str):
        # Basic heuristic: if query is mostly digits (and possibly +,-,()), assume phone search
        # This can be improved with regex or more sophisticated checks if needed.
        num_digits = sum(c.isdigit() for c in query)

        # Example: if more than half the characters are digits, and length is reasonable for a phone number
        if num_digits > len(query) / 2 and len(query) >= 7:
            return self.db_manager.get_all_members(phone_filter=query)
        else:
            return self.db_manager.get_all_members(name_filter=query)

    def add_member(self, name: str, phone: str, join_date: str = None):
        # Note: DatabaseManager.add_member_to_db returns Tuple[bool, str]
        # AppAPI can choose to return this directly or adapt it.
        # For now, returning directly.
        return self.db_manager.add_member_to_db(name, phone, join_date)

    def add_member_with_join_date(self, name: str, phone: str, join_date: str):
        # DatabaseManager.add_member_with_join_date returns int | None
        return self.db_manager.add_member_with_join_date(name, phone, join_date)

    def deactivate_member(self, member_id: int):
        # DatabaseManager.deactivate_member returns Tuple[bool, str]
        return self.db_manager.deactivate_member(member_id)

    def get_member_by_phone(self, phone: str):
        # DatabaseManager.get_member_by_phone returns tuple | None
        return self.db_manager.get_member_by_phone(phone)

    # --- Plan Methods ---
    def get_all_plans(self): # Active plans
        return self.db_manager.get_all_plans()

    def add_plan(self, name: str, duration_days: int, price: int, type_text: str) -> Tuple[bool, str, Optional[int]]:
        """
        Adds a new plan by calling the DatabaseManager.

        Args:
            name: The name of the plan.
            duration_days: The duration of the plan in days.
            price: The price of the plan.
            type_text: The type or category of the plan.

        Returns:
            A tuple mirroring DatabaseManager.add_plan's return:
            - bool: True if successful, False otherwise.
            - str: Success or error message.
            - Optional[int]: The new plan's ID if successful, else None.
        """
        # The is_active parameter was removed as it's no longer in DatabaseManager.add_plan.
        return self.db_manager.add_plan(name, duration_days, price, type_text)

    def update_plan(self, plan_id: int, name: str, duration_days: int):
        # DatabaseManager.update_plan returns Tuple[bool, str]
        return self.db_manager.update_plan(plan_id, name, duration_days)

    def get_plan_by_id(self, plan_id: int):
        # DatabaseManager.get_plan_by_id returns Optional[tuple]
        return self.db_manager.get_plan_by_id(plan_id)

    def delete_plan(self, plan_id: int):
        # DatabaseManager.delete_plan returns tuple[bool, str]
        return self.db_manager.delete_plan(plan_id)

    # --- Transaction Methods ---
    def add_transaction(self, transaction_type: str, member_id: int, start_date: str,
                        amount_paid: float, plan_id: int = None, sessions: int = None,
                        payment_method: str = None, payment_date: str = None, end_date: str = None):
        # DatabaseManager.add_transaction returns Tuple[bool, str]
        return self.db_manager.add_transaction(
            transaction_type, member_id, start_date, amount_paid, plan_id,
            sessions, payment_method, payment_date, end_date
        )

    def get_all_activity_for_member(self, member_id: int):
        # DatabaseManager.get_all_activity_for_member returns list
        return self.db_manager.get_all_activity_for_member(member_id)

    def get_transactions_with_member_details(self, name_filter: str = None,
                                             phone_filter: str = None,
                                             join_date_filter: str = None):
        # DatabaseManager.get_transactions_with_member_details returns list
        return self.db_manager.get_transactions_with_member_details(
            name_filter, phone_filter, join_date_filter
        )

    def get_transactions_for_month(self, year: int, month: int):
        # DatabaseManager.get_transactions_for_month returns list
        return self.db_manager.get_transactions_for_month(year, month)

    def delete_transaction(self, transaction_id: int):
        # DatabaseManager.delete_transaction returns Tuple[bool, str]
        return self.db_manager.delete_transaction(transaction_id)

    def get_member_id_from_transaction(self, transaction_id: int):
        # DatabaseManager.get_member_id_from_transaction returns Optional[int]
        return self.db_manager.get_member_id_from_transaction(transaction_id)

    # --- Reporting & Book Status Methods ---
    def get_pending_renewals(self, year: int, month: int):
        # DatabaseManager.get_pending_renewals returns list
        return self.db_manager.get_pending_renewals(year, month)

    def get_finance_report(self, year: int, month: int):
        # DatabaseManager.get_finance_report returns float | None
        return self.db_manager.get_finance_report(year, month)

    def get_book_status(self, month_key: str): # YYYY-MM
        # DatabaseManager.get_book_status returns str
        return self.db_manager.get_book_status(month_key)

    def set_book_status(self, month_key: str, status: str): # YYYY-MM
        # DatabaseManager.set_book_status returns bool
        return self.db_manager.set_book_status(month_key, status)

    # --- Helper/Utility Methods (already in DB manager, exposing via API if needed) ---
    # Example: get_or_create_plan_id might be useful if UI wants to dynamically manage plans.
    # For now, keeping API surface minimal and adding as needed.
    # def get_or_create_plan_id(self, plan_name: str, duration_days: int):
    #     return self.db_manager.get_or_create_plan_id(plan_name, duration_days)

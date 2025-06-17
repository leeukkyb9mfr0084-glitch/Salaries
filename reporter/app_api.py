from typing import Any, Dict, List, Optional

from database_manager import DatabaseManager


class AppAPI:
    """
    API layer for the Kranos MMA Reporter application.
    Acts as a bridge between the UI and Business Logic layers.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initializes the AppAPI with a DatabaseManager instance.

        Args:
            db_manager: An instance of the DatabaseManager.
        """
        self.db_manager: DatabaseManager = db_manager

    # Member operations
    def add_member(self, name: str, phone: str, email: Optional[str] = None) -> Optional[int]:
        return self.db_manager.add_member(name, phone, email)

    def update_member(self, member_id: int, name: Optional[str] = None, phone: Optional[str] = None, email: Optional[str] = None, is_active: Optional[bool] = None) -> bool:
        return self.db_manager.update_member(member_id, name, phone, email, is_active)

    def get_all_members(self) -> List[Dict]:
        return self.db_manager.get_all_members()

    def delete_member(self, member_id: int) -> bool:
        return self.db_manager.delete_member(member_id)

    def get_active_members(self) -> List[Dict[str, Any]]:
        members = self.db_manager.get_active_members()
        return members if members is not None else []

    # Group Plan operations
    def add_group_plan(self, name: str, duration_days: int, default_amount: float) -> Optional[int]:
        return self.db_manager.add_group_plan(name, duration_days, default_amount)

    def get_all_group_plans(self) -> List[Dict]:
        return self.db_manager.get_all_group_plans()

    def update_group_plan(self, plan_id: int, name: Optional[str] = None, duration_days: Optional[int] = None, default_amount: Optional[float] = None, is_active: Optional[bool] = None) -> bool:
        return self.db_manager.update_group_plan(plan_id, name, duration_days, default_amount, is_active)

    def delete_group_plan(self, plan_id: int) -> bool:
        return self.db_manager.delete_group_plan(plan_id)

    def get_group_plan_by_display_name(self, display_name: str) -> Optional[Dict]:
        return self.db_manager.get_group_plan_by_display_name(display_name)

    # Group Class Membership operations
    def create_group_class_membership(self, member_id: int, plan_id: int, start_date_str: str, amount_paid: float, payment_method: Optional[str] = None, notes: Optional[str] = None) -> Optional[int]:
        return self.db_manager.create_group_class_membership(member_id, plan_id, start_date_str, amount_paid, payment_method, notes)

    def get_all_group_class_memberships_for_view(self, name_filter: Optional[str] = None, phone_filter: Optional[str] = None, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        records = self.db_manager.get_all_group_class_memberships_for_view(name_filter, phone_filter, status_filter)
        return records if records is not None else []

    def update_group_class_membership_record(self, membership_id: int, member_id: int, plan_id: int, plan_duration_days: int, amount_paid: float, start_date: str, is_active: bool) -> bool:
        # Note: The signature for update_group_class_membership_record in DatabaseManager takes individual fields.
        # This API function might need to adapt if it was expecting a 'data' dict.
        # For now, assuming direct pass-through of parameters as per DatabaseManager.
        return self.db_manager.update_group_class_membership_record(membership_id, member_id, plan_id, plan_duration_days, amount_paid, start_date, is_active)

    def delete_group_class_membership_record(self, membership_id: int) -> bool:
        success, message = self.db_manager.delete_group_class_membership_record(membership_id)
        return success # Or handle message if needed

    # Personal Training (PT) Membership operations
    def create_pt_membership(self, member_id: int, purchase_date: str, amount_paid: float, sessions_purchased: int, notes: Optional[str] = None) -> Optional[int]:
        return self.db_manager.add_pt_membership(member_id, purchase_date, amount_paid, sessions_purchased, notes)

    def get_all_pt_memberships(self) -> List[Dict[str, Any]]:
        records = self.db_manager.get_all_pt_memberships()
        return records if records is not None else []

    def delete_pt_membership(self, membership_id: int) -> bool:
        return self.db_manager.delete_pt_membership(membership_id)

    # Report generation
    def generate_financial_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        data = self.db_manager.generate_financial_report_data(start_date, end_date)
        return data if data is not None else {"summary": {"total_revenue": 0.0}, "details": []}

    def generate_renewal_report(self) -> List[Dict[str, Any]]:
        """
        Generates data for the renewal report.
        Refers to group class memberships.

        Returns:
            A list of dictionaries representing renewal data. Returns an empty
            list if no data is available or an error occurs.
        """
        data = self.db_manager.generate_renewal_report_data()
        return data if data is not None else []

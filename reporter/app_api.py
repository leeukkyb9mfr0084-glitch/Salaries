import sqlite3 # Added
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, date
from .database_manager import DatabaseManager
from .models import MemberView, GroupPlanView, GroupClassMembershipView, PTMembershipView
from .database import DB_FILE # Added


class AppAPI:
    """
    API layer for the Kranos MMA Reporter application.
    Acts as a bridge between the UI and Business Logic layers.
    """

    def __init__(self) -> None:
        """
        Initializes the AppAPI and creates its own DatabaseManager instance.
        """
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.db_manager: DatabaseManager = DatabaseManager(connection=conn)

    # Member operations
    def add_member(self, name: str, phone: str, email: Optional[str] = None) -> Optional[int]:
        return self.db_manager.add_member(name, phone, email)

    def update_member(self, member_id: int, name: Optional[str] = None, phone: Optional[str] = None, email: Optional[str] = None, is_active: Optional[bool] = None) -> bool:
        return self.db_manager.update_member(member_id, name, phone, email, is_active)

    def get_all_members_for_view(self) -> List[MemberView]:
        return self.db_manager.get_all_members_for_view()

    def delete_member(self, member_id: int) -> bool:
        return self.db_manager.delete_member(member_id)

    # Group Plan operations
    def add_group_plan(self, name: str, duration_days: int, default_amount: float) -> Optional[int]:
        return self.db_manager.add_group_plan(name, duration_days, default_amount)

    def get_all_group_plans_for_view(self) -> List[GroupPlanView]:
        return self.db_manager.get_all_group_plans_for_view()

    def update_group_plan(self, plan_id: int, name: Optional[str] = None, duration_days: Optional[int] = None, default_amount: Optional[float] = None, is_active: Optional[bool] = None) -> bool:
        return self.db_manager.update_group_plan(plan_id, name, duration_days, default_amount, is_active)

    def delete_group_plan(self, plan_id: int) -> bool:
        return self.db_manager.delete_group_plan(plan_id)

    def get_group_plan_by_display_name(self, display_name: str) -> Optional[GroupPlanView]: # Changed return type
        return self.db_manager.get_group_plan_by_display_name(display_name)

    # Group Class Membership operations
    def create_group_class_membership(self, member_id: int, plan_id: int, start_date_str: str, amount_paid: float, payment_method: Optional[str] = None, notes: Optional[str] = None) -> Optional[int]:
        plan_details = self.db_manager.get_group_plan_details(plan_id)
        if not plan_details or plan_details.duration_days is None:
            return None # Plan not found or duration not set
        plan_duration_days = plan_details.duration_days

        try:
            start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date_obj = start_date_obj + timedelta(days=plan_duration_days -1 if plan_duration_days > 0 else 0)
            end_date_str_calculated = end_date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return None # Invalid start_date_str format

        existing_memberships = self.db_manager.get_memberships_for_member(member_id)
        membership_type_determined = "Renewal" if existing_memberships else "New"

        return self.db_manager.create_group_class_membership(
            member_id,
            plan_id,
            start_date_str,
            end_date_str_calculated,
            amount_paid,
            membership_type_determined,
            payment_method,
            notes
        )

    def get_all_group_class_memberships_for_view(self, name_filter: Optional[str] = None, status_filter: Optional[str] = None) -> List[GroupClassMembershipView]:
        records = self.db_manager.get_all_group_class_memberships_for_view(name_filter=name_filter, status_filter=status_filter)
        return records

    def update_group_class_membership_record(self, membership_id: int, member_id: int, plan_id: int, start_date_str: str, amount_paid: float) -> bool:
        plan_details = self.db_manager.get_group_plan_details(plan_id)
        if not plan_details or plan_details.duration_days is None:
            return False # Plan not found or duration not set
        plan_duration_days = plan_details.duration_days

        try:
            start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date_obj = start_date_obj + timedelta(days=plan_duration_days -1 if plan_duration_days > 0 else 0)
            end_date_str_calculated = end_date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return False # Invalid start_date_str format

        success, _ = self.db_manager.update_group_class_membership_record(
            membership_id,
            member_id,
            plan_id,
            start_date_str, # Use the input parameter which is the start_date string
            end_date_str_calculated,
            amount_paid
        )
        return success

    def delete_group_class_membership_record(self, membership_id: int) -> bool:
        success, _ = self.db_manager.delete_group_class_membership_record(membership_id)
        return success

    # Personal Training (PT) Membership operations
    # Parameter `sessions_purchased` here maps to `sessions_total` in the database.
    # `sessions_remaining` is initialized to `sessions_total` in `db_manager.add_pt_membership`.
    def create_pt_membership(self, member_id: int, purchase_date: str, amount_paid: float, sessions_purchased: int) -> Optional[int]:
        return self.db_manager.add_pt_membership(member_id, purchase_date, amount_paid, sessions_purchased)

    def get_all_pt_memberships_for_view(self) -> List[PTMembershipView]:
        records = self.db_manager.get_all_pt_memberships_for_view()
        return records

    def delete_pt_membership(self, membership_id: int) -> bool:
        return self.db_manager.delete_pt_membership(membership_id)

    def update_pt_membership(self, membership_id: int, purchase_date: Optional[str] = None, amount_paid: Optional[float] = None, sessions_purchased: Optional[int] = None) -> bool:
        """
        Updates an existing Personal Training (PT) membership record.
        Passes arguments directly to the DatabaseManager.
        """
        return self.db_manager.update_pt_membership(membership_id, purchase_date, amount_paid, sessions_purchased)

    # Report generation
    def generate_financial_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        raw_transactions = self.db_manager.generate_financial_report_data(start_date, end_date)

        total_revenue = 0.0
        processed_details = []

        for trans in raw_transactions:
            item_name = "Unknown Item"
            if trans.get('type') == 'group':
                # For group, item_name could be the plan_name
                item_name = trans.get('plan_name', 'Group Plan')
            elif trans.get('type') == 'pt':
                # For PT, item_name could be "{sessions_total} PT Sessions"
                sessions = trans.get('sessions_total', 'N/A')
                item_name = f"{sessions} PT Sessions"

            processed_details.append({
                "purchase_date": trans.get('purchase_date'),
                "amount_paid": trans.get('amount_paid'),
                "type": trans.get('type'),
                "member_name": trans.get('member_name'),
                "item_name": item_name
            })
            total_revenue += trans.get('amount_paid', 0.0)

        return {
            "summary": {"total_revenue": total_revenue},
            "details": processed_details
        }

    def generate_renewal_report(self) -> List[Dict[str, Any]]:
        """
        Generates data for the renewal report.
        Refers to group class memberships.

        Returns:
            A list of dictionaries representing renewal data. Returns an empty
            list if no data is available or an error occurs.
        """
        current_date_str = date.today().strftime("%Y-%m-%d")
        thirty_days_later_obj = date.today() + timedelta(days=30)
        thirty_days_later_str = thirty_days_later_obj.strftime("%Y-%m-%d")

        data = self.db_manager.generate_renewal_report_data(current_date_str, thirty_days_later_str)
        return data

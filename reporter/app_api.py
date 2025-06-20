import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from . import models  # Direct import of models module
from .database import DB_FILE
from .database_manager import DatabaseManager


class AppAPI:
    """
    API layer for the Kranos MMA Reporter application.
    Acts as a bridge between the UI and Business Logic layers.
    """

    def __init__(self) -> None:
        """
        Initializes the AppAPI and creates its own DatabaseManager instance.
        """
        conn = sqlite3.connect(
            DB_FILE, check_same_thread=False
        )  # check_same_thread for web apps
        self.db_manager: DatabaseManager = DatabaseManager(connection=conn)

    # Member operations
    def add_member(
        self, name: str, email: str, phone: str, join_date: str
    ) -> Optional[models.Member]:
        """
        Adds a new member.
        """
        # join_date is expected as "YYYY-MM-DD" string by models.Member and db_manager
        new_member = models.Member(
            id=None,
            name=name,
            email=email,
            phone=phone,
            join_date=join_date,  # Ensure this is "YYYY-MM-DD"
            is_active=True,
        )
        return self.db_manager.add_member(new_member)

    def update_member(
        self,
        member_id: int,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        join_date: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """
        Updates an existing member.
        db_manager.update_member handles None for fields that are not being updated.
        """
        member_to_update = models.Member(
            id=member_id,
            name=name,
            phone=phone,
            email=email,
            join_date=join_date,  # Pass join_date through if provided
            is_active=is_active,
        )
        return self.db_manager.update_member(member_to_update)

    def get_all_members_for_view(self) -> List[models.MemberView]:
        # Assumes db_manager.get_all_members_for_view() returns List[models.MemberView]
        return self.db_manager.get_all_members_for_view()

    def delete_member(self, member_id: int) -> bool:
        return self.db_manager.delete_member(member_id)

    # Group Plan operations
    def add_group_plan(
        self,
        name: str,
        duration_days: int,
        default_amount: float,
        is_active: bool = True,
    ) -> Optional[models.GroupPlan]:
        """
        Adds a new group plan.
        """
        new_plan = models.GroupPlan(
            id=None,
            name=name,
            duration_days=duration_days,
            default_amount=default_amount,
            display_name=None,  # db_manager will generate this if None
            is_active=is_active,
        )
        return self.db_manager.add_group_plan(new_plan)

    def get_all_group_plans_for_view(self) -> List[models.GroupPlanView]:
        # Assumes db_manager.get_all_group_plans_for_view() returns List[models.GroupPlanView]
        return self.db_manager.get_all_group_plans_for_view()

    def update_group_plan(
        self,
        plan_id: int,
        name: Optional[str] = None,
        duration_days: Optional[int] = None,
        default_amount: Optional[float] = None,
        display_name: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """
        Updates an existing group plan.
        db_manager.update_group_plan handles None for fields not being updated and regenerates display_name if needed.
        """
        plan_to_update = models.GroupPlan(
            id=plan_id,
            name=name,
            duration_days=duration_days,
            default_amount=default_amount,
            display_name=display_name,  # Pass through, db_manager might regenerate it
            is_active=is_active,
        )
        return self.db_manager.update_group_plan(plan_to_update)

    def delete_group_plan(self, plan_id: int) -> bool:
        return self.db_manager.delete_group_plan(plan_id)

    def get_group_plan_by_display_name(
        self, display_name: str
    ) -> Optional[models.GroupPlanView]:
        # db_manager.get_group_plan_by_display_name returns models.GroupPlan
        # We need to map to models.GroupPlanView if it's different.
        # models.GroupPlan and models.GroupPlanView are different.
        db_plan = self.db_manager.get_group_plan_by_display_name(display_name)
        if db_plan:
            return models.GroupPlanView(
                id=db_plan.id,  # Ensure db_plan.id is not None
                name=db_plan.name,
                display_name=(
                    db_plan.display_name
                    if db_plan.display_name
                    else f"{db_plan.name} - {db_plan.duration_days} days"
                ),
                is_active=db_plan.is_active,
                default_amount=db_plan.default_amount,
                duration_days=db_plan.duration_days,
            )
        return None

    # Group Class Membership operations
    def create_group_class_membership(
        self,
        member_id: int,
        plan_id: int,
        start_date: str,
        amount_paid: float,
        purchase_date: str,
        payment_method: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[models.GroupClassMembership]:
        """
        Creates a new group class membership.
        """
        plan_details = self.db_manager.get_group_plan_by_id(plan_id)
        if not plan_details:
            # Log error or raise? For now, return None as per original logic flow.
            return None

        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            duration = (
                int(plan_details.duration_days)
                if plan_details
                and hasattr(plan_details, "duration_days")
                and plan_details.duration_days is not None
                else 0
            )
            # Ensure end_date calculation is correct: if duration is 30 days, it ends 29 days after start.
            end_date_obj = start_date_obj + timedelta(
                days=duration - 1 if duration > 0 else 0
            )
            end_date_str_calculated = end_date_obj.strftime("%Y-%m-%d")
        except ValueError:  # Catches strptime errors or issues with duration conversion
            return None

        # Determine membership_type
        # db_manager.get_group_class_memberships_by_member_id returns List[models.GroupClassMembership]
        existing_memberships = self.db_manager.get_group_class_memberships_by_member_id(
            member_id
        )
        membership_type_determined = "Renewal" if existing_memberships else "New"

        new_membership = models.GroupClassMembership(
            id=None,
            member_id=member_id,
            plan_id=plan_id,
            start_date=start_date,  # Expected "YYYY-MM-DD"
            end_date=end_date_str_calculated,  # Expected "YYYY-MM-DD"
            amount_paid=amount_paid,
            purchase_date=purchase_date,  # Expected "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
            membership_type=membership_type_determined,
            is_active=True,
            payment_method=payment_method,  # Stored on model, not in DB table via current db_manager
            notes=notes,  # Stored on model, not in DB table via current db_manager
        )
        return self.db_manager.add_group_class_membership(new_membership)

    def get_all_group_class_memberships_for_view(
        self, name_filter: Optional[str] = None, status_filter: Optional[str] = None
    ) -> List[models.GroupClassMembershipView]:
        # Assumes db_manager.get_all_group_class_memberships_for_view returns List[models.GroupClassMembershipView]
        return self.db_manager.get_all_group_class_memberships_for_view(
            name_filter=name_filter, status_filter=status_filter
        )

    def update_group_class_membership(
        self,
        membership_id: int,
        member_id: int,
        plan_id: int,
        start_date: str,
        amount_paid: float,
        purchase_date: Optional[str] = None,
        membership_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        payment_method: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Updates an existing group class membership.
        db_manager.update_group_class_membership takes a full GroupClassMembership object and updates all fields.
        AppAPI must construct this object. Caller should provide current values for fields not being changed if they are part of this signature.
        """
        plan_details = self.db_manager.get_group_plan_by_id(plan_id)
        if not plan_details:
            return False  # Or raise error

        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            duration = (
                int(plan_details.duration_days)
                if plan_details
                and hasattr(plan_details, "duration_days")
                and plan_details.duration_days is not None
                else 0
            )
            end_date_obj = start_date_obj + timedelta(
                days=duration - 1 if duration > 0 else 0
            )
            end_date_str_calculated = end_date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return False

        # Construct the full object. If optional fields are None, they might be set to NULL in DB
        # or cause issues if DB columns are NOT NULL without defaults.
        # The GroupClassMembership model has defaults for purchase_date=None, is_active=True, payment_method=None, notes=None.
        # However, these defaults apply if the fields are omitted at creation, not if None is passed for them.
        # Let's be explicit.

        membership_to_update = models.GroupClassMembership(
            id=membership_id,
            member_id=member_id,
            plan_id=plan_id,
            start_date=start_date,
            end_date=end_date_str_calculated,
            amount_paid=amount_paid,
            purchase_date=purchase_date,  # If None, db_manager will try to set it to NULL.
            membership_type=(
                membership_type if membership_type is not None else "New"
            ),  # Provide a default if None
            is_active=(
                is_active if is_active is not None else True
            ),  # Provide a default if None
            payment_method=payment_method,
            notes=notes,
        )
        return self.db_manager.update_group_class_membership(membership_to_update)

    def delete_group_class_membership_record(self, membership_id: int) -> bool:
        # Renamed in db_manager to delete_group_class_membership
        return self.db_manager.delete_group_class_membership(membership_id)

    # Personal Training (PT) Membership operations
    def create_pt_membership(
        self,
        member_id: int,
        purchase_date: str,
        amount_paid: float,
        sessions_total: int,
    ) -> Optional[models.PTMembership]:
        """
        Creates a new PT membership.
        """
        new_pt_membership = models.PTMembership(
            id=None,
            member_id=member_id,
            purchase_date=purchase_date,  # Expected "YYYY-MM-DD"
            amount_paid=amount_paid,
            sessions_total=sessions_total,
            sessions_remaining=sessions_total,  # Initialize sessions_remaining to sessions_total
        )
        return self.db_manager.add_pt_membership(new_pt_membership)

    def get_all_pt_memberships_for_view(self) -> List[models.PTMembershipView]:
        # Assumes db_manager.get_all_pt_memberships_for_view returns List[models.PTMembershipView]
        return self.db_manager.get_all_pt_memberships_for_view()

    def delete_pt_membership(self, membership_id: int) -> bool:
        return self.db_manager.delete_pt_membership(membership_id)

    def update_pt_membership(
        self,
        membership_id: int,
        member_id: int,
        purchase_date: str,
        amount_paid: float,
        sessions_total: int,
        sessions_remaining: int,
    ) -> bool:
        """
        Updates an existing Personal Training (PT) membership record.
        db_manager.update_pt_membership takes a full PTMembership object.
        All fields for PTMembership model must be provided here.
        The 'member_id' is part of the model and required, though it's not typically changed in an update.
        """
        # PTMembership model requires: id, member_id, purchase_date, amount_paid, sessions_total, sessions_remaining.
        # All are non-optional in the model.
        pt_membership_to_update = models.PTMembership(
            id=membership_id,
            member_id=member_id,  # Must be provided by caller
            purchase_date=purchase_date,
            amount_paid=amount_paid,
            sessions_total=sessions_total,
            sessions_remaining=sessions_remaining,
        )
        return self.db_manager.update_pt_membership(pt_membership_to_update)

    # Report generation
    def generate_financial_report(
        self, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        # This function's logic seems mostly okay but relies on db_manager returning specific dict keys.
        # No changes specified for this in the task, so keeping as is, assuming db_manager.generate_financial_report_data is stable.
        raw_transactions = self.db_manager.generate_financial_report_data(
            start_date, end_date
        )

        total_revenue = 0.0
        processed_details = []

        for trans in raw_transactions:  # trans is a dict
            item_name = "Unknown Item"
            if trans.get("type") == "group":
                item_name = trans.get("plan_name", "Group Plan")
            elif trans.get("type") == "pt":
                sessions = trans.get("sessions_total", "N/A")
                item_name = f"{sessions} PT Sessions"

            processed_details.append(
                {
                    "purchase_date": trans.get("purchase_date"),
                    "amount_paid": trans.get("amount_paid"),
                    "type": trans.get("type"),
                    "member_name": trans.get("member_name"),
                    "item_name": item_name,
                }
            )
            total_revenue += trans.get("amount_paid", 0.0)

        return {
            "summary": {"total_revenue": total_revenue},
            "details": processed_details,
        }

    def generate_renewal_report(self) -> List[Dict[str, Any]]:
        """
        Generates data for the renewal report.
        No changes specified for this in the task.
        """
        current_date_str = date.today().strftime("%Y-%m-%d")
        thirty_days_later_obj = date.today() + timedelta(
            days=30
        )  # original was 30, not 29
        thirty_days_later_str = thirty_days_later_obj.strftime("%Y-%m-%d")

        # db_manager.generate_renewal_report_data expects start and end for the window
        data = self.db_manager.generate_renewal_report_data(
            current_date_str, thirty_days_later_str
        )
        return data


# Example of how to get a GroupPlan by ID (not directly part of AppAPI methods but useful for context)
# def get_group_plan_details_example(db_manager: DatabaseManager, plan_id: int) -> Optional[models.GroupPlan]:
#     return db_manager.get_group_plan_by_id(plan_id)

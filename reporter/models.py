from dataclasses import dataclass
from typing import Optional

@dataclass
class MemberView:
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    join_date: Optional[str] = None # Assuming YYYY-MM-DD
    status: Optional[str] = None # e.g., Active, Inactive, Frozen
    membership_type: Optional[str] = None # e.g., Group, PT, Both
    payment_status: Optional[str] = None # e.g., Paid, Due, Overdue
    notes: Optional[str] = None

@dataclass
class GroupPlanView:
    id: int
    name: str
    price: Optional[float] = None
    duration_days: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = None # e.g., Active, Discontinued

@dataclass
class GroupClassMembershipView:
    id: int
    member_id: int
    member_name: str # Denormalized for easy display
    plan_id: int
    plan_name: str # Denormalized for easy display
    start_date: str # Assuming YYYY-MM-DD
    end_date: str # Assuming YYYY-MM-DD
    status: str # e.g., Active, Expired, Cancelled
    auto_renewal_enabled: Optional[bool] = None
    amount_paid: Optional[float] = None
    # Added due to common column names observed in database_manager.py later
    member_display_name: Optional[str] = None
    plan_display_name: Optional[str] = None


@dataclass
class PTMembershipView:
    id: int
    member_id: int
    member_name: str # Denormalized for easy display
    plan_id: int # Assuming PT plans might be structured differently or share a table
    plan_name: str # Denormalized for easy display
    start_date: str # Assuming YYYY-MM-DD
    status: str # e.g., Active, Completed, Cancelled
    end_date: Optional[str] = None # PT might be session-based, end_date might be flexible
    sessions_total: Optional[int] = None
    sessions_remaining: Optional[int] = None
    amount_paid: Optional[float] = None
    # Added due to common column names observed in database_manager.py later
    member_display_name: Optional[str] = None
    plan_display_name: Optional[str] = None

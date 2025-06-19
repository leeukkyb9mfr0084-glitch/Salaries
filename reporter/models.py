from dataclasses import dataclass
from typing import Optional

@dataclass
class MemberView:
    id: int
    name: str
    phone: str  # Assuming phone is stored as str, adjust if it's int
    email: str
    join_date: str
    is_active: bool

@dataclass
class GroupPlanView:
    id: int
    name: str
    display_name: str
    is_active: bool # Moved before fields with defaults
    default_amount: float
    duration_days: int

@dataclass
class GroupClassMembershipView:
    id: int
    member_id: int
    member_name: str # Denormalized for easy display
    plan_id: int
    plan_name: str # Denormalized for easy display
    start_date: str # Assuming YYYY-MM-DD
    end_date: str # Assuming YYYY-MM-DD
    purchase_date: str
    membership_type: str
    is_active: bool
    # Fields with defaults come after non-default fields
    amount_paid: Optional[float] = None


@dataclass
class PTMembershipView:
    membership_id: int
    member_id: int
    member_name: str
    purchase_date: str
    sessions_total: int
    sessions_remaining: int
    amount_paid: float

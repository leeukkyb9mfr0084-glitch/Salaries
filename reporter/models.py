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
class Member:
    id: Optional[int]
    name: str
    phone: str
    email: Optional[str]
    join_date: Optional[str] # Assuming YYYY-MM-DD
    is_active: bool

@dataclass
class GroupPlan:
    id: Optional[int]
    name: str
    duration_days: int
    default_amount: float
    display_name: Optional[str] = None # Will be auto-generated if None
    is_active: bool = True

@dataclass
class GroupPlanView:
    id: int
    name: str
    display_name: str
    is_active: bool # Moved before fields with defaults
    default_amount: float
    duration_days: int

@dataclass
class GroupClassMembership:
    id: Optional[int]
    member_id: int
    plan_id: int
    start_date: str # Assuming YYYY-MM-DD
    end_date: str # Assuming YYYY-MM-DD
    amount_paid: float
    purchase_date: Optional[str] = None # Should be set on creation
    membership_type: str
    is_active: bool = True
    # These fields are not in the DB table but were in function params
    payment_method: Optional[str] = None
    notes: Optional[str] = None

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
class PTMembership:
    id: Optional[int]
    member_id: int
    purchase_date: str # Assuming YYYY-MM-DD
    amount_paid: float
    sessions_total: int
    sessions_remaining: int # Should typically be initialized to sessions_total

@dataclass
class PTMembershipView:
    membership_id: int # This likely maps to PTMembership.id
    member_id: int
    member_name: str
    purchase_date: str
    sessions_total: int
    sessions_remaining: int
    amount_paid: float

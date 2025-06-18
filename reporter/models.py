from dataclasses import dataclass
from typing import Optional

@dataclass
class MemberView:
    id: int
    name: str
    phone: str  # Assuming phone is stored as str, adjust if it's int
    email: str
    join_date: str
    is_active: int # Assuming is_active is stored as int (0 or 1)

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


@dataclass
class PTMembershipView:
    membership_id: int
    member_id: int
    member_name: str
    purchase_date: str
    sessions_total: int
    sessions_remaining: int
    notes: str

import pytest
from datetime import date, datetime, timedelta # Added datetime, timedelta
from reporter.app_api import AppAPI
from reporter.database_manager import DatabaseManager
from reporter.database import create_database
from reporter.models import Member, GroupPlan, GroupClassMembership # Required models

@pytest.fixture
def db_manager_mm() -> DatabaseManager: # Renamed to avoid conflict
    conn = create_database(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    manager = DatabaseManager(connection=conn)
    return manager

@pytest.fixture
def app_api_mm_instance(db_manager_mm: DatabaseManager) -> AppAPI: # Renamed fixture
    api = AppAPI()
    api.db_manager = db_manager_mm
    return api

def test_app_api_create_group_class_membership_success(app_api_mm_instance: AppAPI, db_manager_mm: DatabaseManager):
    # 1. Setup: Create a member and a group plan first
    member_join_date = date.today().strftime("%Y-%m-%d")
    # Use the actual signature of db_manager_mm.add_member: name, phone, email, join_date (optional)
    member_id = db_manager_mm.add_member(
        name="Test Member for GC",
        phone="1230009999", # Unique phone
        email="gc_member@test.com",
        join_date=member_join_date
    )
    assert member_id is not None

    # Use the actual signature of db_manager_mm.add_group_plan: name, duration_days, default_amount, is_active (optional)
    plan_id = db_manager_mm.add_group_plan(
        name="GC Test Plan",
        duration_days=30,
        default_amount=50.0,
        is_active=True
    )
    assert plan_id is not None

    start_date_str = "2024-03-01"
    purchase_date_str = "2024-02-28"
    amount_paid = 50.0

    # 2. Call the AppAPI method to create GC membership
    created_gc_membership = app_api_mm_instance.create_group_class_membership(
        member_id=member_id,
        plan_id=plan_id,
        start_date=start_date_str,
        amount_paid=amount_paid,
        purchase_date=purchase_date_str
    )

    # 3. Assertions on the returned model
    assert created_gc_membership is not None
    assert created_gc_membership.id is not None
    assert created_gc_membership.member_id == member_id
    assert created_gc_membership.plan_id == plan_id
    assert created_gc_membership.start_date == start_date_str
    assert created_gc_membership.amount_paid == amount_paid
    assert created_gc_membership.purchase_date == purchase_date_str
    assert created_gc_membership.is_active is True

    expected_end_date_obj = (datetime.strptime(start_date_str, "%Y-%m-%d") + timedelta(days=30-1))
    expected_end_date_str = expected_end_date_obj.strftime("%Y-%m-%d")
    assert created_gc_membership.end_date == expected_end_date_str
    assert created_gc_membership.membership_type == "New"

    # Verify directly in DB
    cursor = db_manager_mm.conn.cursor()
    cursor.execute(
        "SELECT member_id, plan_id, start_date, end_date, purchase_date, amount_paid, membership_type, is_active FROM group_class_memberships WHERE id = ?",
        (created_gc_membership.id,),
    )
    db_row = cursor.fetchone()
    assert db_row is not None
    assert db_row[0] == member_id
    assert db_row[1] == plan_id
    assert db_row[2] == start_date_str
    assert db_row[3] == expected_end_date_str
    assert db_row[4] == purchase_date_str
    assert db_row[5] == amount_paid
    assert db_row[6] == "New"
    assert db_row[7] == 1 # is_active

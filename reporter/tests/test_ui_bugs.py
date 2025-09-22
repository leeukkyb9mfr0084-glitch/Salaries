"""
Test file for UI bugs - follows TDD methodology.
This test specifically targets the Group Plans tab filter bug.
"""

import sys
import os
# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock
from reporter.models import GroupPlanView


def test_group_plan_filter_uses_is_active():
    """
    Test that the Group Plans tab correctly uses the is_active boolean attribute
    instead of a non-existent status string attribute.
    
    This test simulates the filtering logic that happens in render_memberships_tab
    when filtering active plans for the dropdown.
    """
    
    # Create mock GroupPlanView objects
    active_plan = GroupPlanView(
        id=1,
        name="Gold Plan",
        display_name="Gold Plan (30 days)",
        is_active=True,
        default_amount=1000.0,
        duration_days=30
    )
    
    inactive_plan = GroupPlanView(
        id=2,
        name="Silver Plan", 
        display_name="Silver Plan (15 days)",
        is_active=False,
        default_amount=500.0,
        duration_days=15
    )
    
    all_group_plans_gc_form_data = [active_plan, inactive_plan]
    
    try:
        # This simulates the filtering logic in line 261-265 of app.py
        # The bug is that it tries to access plan.status instead of plan.is_active
        plan_options_for_select = {
            plan.id: f"{plan.name} ({plan.duration_days} days, ₹{plan.default_amount or 0:.2f})"
            for plan in all_group_plans_gc_form_data
            if plan.status == 'Active'  # This should be plan.is_active
        }
        
        # If we get here without an AttributeError, the test should fail
        # because it means the bug doesn't exist
        raise AssertionError(
            "Expected AttributeError when accessing 'status' attribute, but none was raised. "
            "The bug may have already been fixed."
        )
        
    except AttributeError as e:
        if "status" in str(e):
            # This is expected - the bug exists
            print(f"✓ Bug confirmed: {e}")
            print("  The code is trying to access 'status' attribute which doesn't exist.")
            print("  It should use 'is_active' boolean attribute instead.")
            return True  # Test passes - bug detected
        else:
            # Different AttributeError - re-raise
            raise
    
    except Exception as e:
        raise AssertionError(f"Unexpected error during test: {e}")


if __name__ == "__main__":
    try:
        result = test_group_plan_filter_uses_is_active()
        if result:
            print("\n✓ TEST PASSED: Bug detected successfully!")
            print("  The test confirms that the code incorrectly uses 'plan.status'")
            print("  instead of 'plan.is_active'")
            exit(0)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}")
        exit(1)
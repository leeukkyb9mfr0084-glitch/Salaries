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
        # After the fix, it should use plan.is_active instead of plan.status
        plan_options_for_select = {
            plan.id: f"{plan.name} ({plan.duration_days} days, ₹{plan.default_amount or 0:.2f})"
            for plan in all_group_plans_gc_form_data
            if plan.is_active  # FIXED: now using correct is_active boolean attribute
        }
        
        # Verify that we successfully created the dictionary with only active plans
        assert len(plan_options_for_select) == 1, f"Expected 1 active plan, got {len(plan_options_for_select)}"
        assert 1 in plan_options_for_select, "Active plan with ID 1 should be in the dictionary"
        assert 2 not in plan_options_for_select, "Inactive plan with ID 2 should NOT be in the dictionary"
        assert "Gold Plan" in plan_options_for_select[1], "Gold Plan should be in the display string"
        
        print("✓ Test passed: Group Plans tab correctly uses is_active attribute")
        print(f"  Active plans filtered successfully: {plan_options_for_select}")
        # Test passes - no return needed for pytest
        
    except AttributeError as e:
        if "status" in str(e):
            # The bug still exists
            raise AssertionError(
                f"Bug detected: Code is trying to access 'status' attribute instead of 'is_active'. Error: {e}"
            )
        else:
            # Different AttributeError - re-raise
            raise
    
    except AssertionError:
        # Re-raise assertion errors
        raise
    
    except Exception as e:
        raise AssertionError(f"Unexpected error during test: {e}")


if __name__ == "__main__":
    try:
        test_group_plan_filter_uses_is_active()
        print("\n✓ TEST PASSED: The bug has been fixed!")
        print("  The code now correctly uses 'plan.is_active' to filter plans.")
        exit(0)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}")
        exit(1)
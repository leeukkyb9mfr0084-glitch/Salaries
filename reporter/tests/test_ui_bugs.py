"""
Test file for UI bugs - specifically testing the Group Plans tab filter issue.
This test directly examines the source code to detect the bug.
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from reporter.models import GroupPlanView


def test_group_plan_filter_uses_is_active():
    """
    Test that the Group Plans tab correctly uses the is_active boolean attribute
    instead of a non-existent status string attribute when filtering plans.
    
    This test:
    1. Reads the app.py source code
    2. Checks if it contains the buggy pattern (plan.status == 'Active')
    3. Verifies that GroupPlanView objects work with the correct attribute
    """
    
    print("=" * 70)
    print("TEST: Group Plan Filter - Checking for plan.status vs plan.is_active bug")
    print("=" * 70)
    
    # Step 1: Check the source code for the bug
    app_file_path = "/workspace/reporter/streamlit_ui/app.py"
    print(f"\n1. Examining source code in {app_file_path}...")
    
    with open(app_file_path, 'r') as f:
        source_code = f.read()
    
    # Look for the buggy pattern
    buggy_pattern = "plan.status == 'Active'"
    correct_pattern = "plan.is_active"
    
    has_bug = False
    if buggy_pattern in source_code:
        print(f"\n✗ BUG FOUND: Source code contains '{buggy_pattern}'")
        print("   This will cause an AttributeError at runtime!")
        has_bug = True
        
        # Find the line number
        lines = source_code.split('\n')
        for i, line in enumerate(lines, 1):
            if buggy_pattern in line:
                print(f"   Location: Line {i}")
                print(f"   Code: {line.strip()}")
    else:
        print(f"\n✓ No bug found: Code does not contain '{buggy_pattern}'")
        
        # Check if the correct pattern is used
        if correct_pattern in source_code:
            print(f"✓ Correct pattern '{correct_pattern}' is being used")
            
            # Find instances of correct usage
            lines = source_code.split('\n')
            found_correct = False
            for i, line in enumerate(lines, 1):
                if correct_pattern in line and "for plan in" in line:
                    if not found_correct:
                        print(f"\n   Example of correct usage:")
                    print(f"   Line {i}: {line.strip()}")
                    found_correct = True
                    if found_correct:
                        break  # Just show one example
    
    # Step 2: Verify that GroupPlanView has the correct attribute
    print("\n2. Verifying GroupPlanView attributes...")
    
    # Create a test GroupPlanView object
    test_plan = GroupPlanView(
        id=1,
        name="Test Plan",
        display_name="Test Plan (30 days)",
        is_active=True,
        default_amount=1000.0,
        duration_days=30
    )
    
    # Check that is_active exists
    try:
        is_active_value = test_plan.is_active
        print(f"✓ GroupPlanView.is_active exists and = {is_active_value}")
    except AttributeError:
        print("✗ GroupPlanView.is_active does not exist!")
        has_bug = True
    
    # Check that status does NOT exist
    try:
        status_value = test_plan.status
        print(f"✗ GroupPlanView.status exists (it shouldn't!) = {status_value}")
        has_bug = True
    except AttributeError:
        print("✓ GroupPlanView.status does not exist (as expected)")
    
    # Step 3: Simulate what would happen with the bug
    print("\n3. Simulating runtime behavior...")
    
    plans = [test_plan]
    
    if has_bug:
        print("\n   With the BUG (plan.status == 'Active'):")
        try:
            # This simulates the buggy code
            filtered = [p for p in plans if p.status == 'Active']
            print("   ✗ ERROR: Should have raised AttributeError but didn't!")
        except AttributeError as e:
            print(f"   ✓ AttributeError raised as expected: {e}")
    
    print("\n   With the FIX (plan.is_active):")
    try:
        # This simulates the correct code
        filtered = [p for p in plans if p.is_active]
        print(f"   ✓ Filtering works correctly! Found {len(filtered)} active plan(s)")
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
        has_bug = True
    
    return not has_bug  # Return True if no bug, False if bug exists


if __name__ == "__main__":
    print("\nRunning test for Group Plan filter bug...")
    print("-" * 70)
    
    test_passed = test_group_plan_filter_uses_is_active()
    
    print("\n" + "=" * 70)
    if not test_passed:
        print("TEST FAILED: Bug detected! ✗")
        print("\nThe code incorrectly uses 'plan.status == \"Active\"'")
        print("It should be fixed to use 'plan.is_active' instead.")
        print("\nTo fix: Replace 'if plan.status == \"Active\"' with 'if plan.is_active'")
        exit(1)  # Exit with error code to indicate test failure
    else:
        print("TEST PASSED: No bug detected! ✓")
        print("\nThe code correctly uses 'plan.is_active'")
        exit(0)  # Exit successfully
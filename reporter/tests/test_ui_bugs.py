import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from streamlit.testing.v1 import AppTest
from reporter.models import GroupPlanView, MemberView
from reporter.database import initialize_database # Added import

@patch("sqlite3.connect")
@patch("reporter.database_manager.DatabaseManager")
@patch("reporter.app_api.AppAPI")
def test_group_plan_filter_uses_is_active(MockAppAPIClass_Source, MockDBManagerClass_Source, mock_sqlite_connect_std):
    """
    Tests that the app now runs WITHOUT an AttributeError related to 'plan.status'
    after the fix has been applied in app.py.
    """
    mock_app_api_instance = MockAppAPIClass_Source.return_value

    mock_plans_data = [
        GroupPlanView(id=1, name="Active Plan", display_name="Active Plan Display", default_amount=100.0, duration_days=30, is_active=True),
        GroupPlanView(id=2, name="Inactive Plan", display_name="Inactive Plan Display", default_amount=50.0, duration_days=30, is_active=False),
    ]

    def print_and_return_mock_plans(*args, **kwargs):
        print("PYTHON_TEST_PRINT: Mocked get_all_group_plans_for_view WAS CALLED", flush=True)
        return mock_plans_data

    mock_app_api_instance.get_all_group_plans_for_view = MagicMock(side_effect=print_and_return_mock_plans)

    mock_members_data = [
        MemberView(id=1, name="Test Member Active", phone="123", email="a@b.com", join_date="2023-01-01", is_active=True),
    ]
    mock_app_api_instance.get_all_members_for_view.return_value = mock_members_data
    mock_app_api_instance.get_all_group_class_memberships_for_view.return_value = []
    mock_app_api_instance.get_all_pt_memberships_for_view.return_value = []
    mock_app_api_instance.generate_financial_report.return_value = {"summary": {}, "details": []}
    mock_app_api_instance.generate_renewal_report.return_value = []

    mock_sqlite_connect_std.return_value = MagicMock()
    MockDBManagerClass_Source.return_value = MagicMock()

    initialize_database() # Initialize database before running the app

    at = AppTest.from_file("reporter/streamlit_ui/app.py", default_timeout=60)
    at.run() # Initial run.

    # Run the Memberships tab to ensure the relevant code paths are executed.
    # Forms in Members and Group Plans tabs are currently commented out in app.py.
    # The `st.button in form` error in Memberships tab might still occur if not fixed.
    if len(at.tabs) > 2:
        at.tabs[2].run()
    else:
        # This assertion itself could cause the test to fail if tabs aren't loaded.
        # If the goal is to check for the *absence* of the AttributeError, this is okay.
        assert False, f"Tabs not loaded correctly or not enough tabs found. Found tabs: {len(at.tabs)}"


    # Assertions for a PASSING test (i.e., bug is fixed and no other major errors occur):
    if at.exception:
        actual_exception = at.exception
        exc_type = type(actual_exception).__name__
        exc_message = str(actual_exception)
        # Explicitly check if the old bug (AttributeError) is still somehow present
        if exc_type == "AttributeError" and "'GroupPlanView' object has no attribute 'status'" in exc_message:
            assert False, f"BUG STILL PRESENT: Test failed with UNHANDLED AttributeError: {exc_type} - {exc_message}"
        # Check for the st.button in form error, which is a known potential issue
        elif exc_type == "StreamlitAPIException" and "`st.button()` can't be used in an `st.form()`" in exc_message:
            assert False, f"App run failed with 'st.button in form' error in Memberships tab: {exc_message}"
        # Fail for any other unexpected unhandled exception
        assert False, f"App run failed with an unexpected UNHANDLED exception: {exc_type} - {exc_message}"

    if at.error: # Should be None if no script errors were wrapped by AppTest (like ElementList error)
        error_type = type(at.error).__name__
        error_message = str(at.error)
        assert False, f"App run resulted in at.error being set to: {error_type} - {error_message}. Expected no errors for a clean run."

    # Check st.error messages specifically for the old bug being caught by app's try-except
    error_messages = [m.value for m in at.markdown if m.type == "error"]
    found_bug_related_st_error = False
    for msg in error_messages:
        if "Error fetching group plans" in msg and "GroupPlanView' object has no attribute 'status'" in msg:
            found_bug_related_st_error = True
            break
    assert not found_bug_related_st_error, \
        f"BUG STILL PRESENT: App displayed st.error for AttributeError: {error_messages}"

    # If all checks pass, the test function completes without an assert False, indicating success.
    print("PYTHON_TEST_PRINT: Test confirmed: No AttributeError related to plan.status occurred, and no other critical errors blocked execution.", flush=True)

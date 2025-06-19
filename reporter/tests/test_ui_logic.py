import unittest.mock
from reporter.streamlit_ui.app import AppAPI
from reporter.models import GroupPlanView
from streamlit.testing.v1 import AppTest
from reporter.database import initialize_database # Added import

def test_ui_filters_for_active_plans():
    """
    Tests that the UI correctly uses plan.is_active to filter plans.
    """
    # 1. Mock the API to avoid real database calls
    mock_api = unittest.mock.MagicMock(spec=AppAPI)
    mock_api.get_all_group_plans_for_view.return_value = [
        GroupPlanView(id=1, name="Active Plan", display_name="Active Plan (30 days)", is_active=True, default_amount=100.0, duration_days=30),
        GroupPlanView(id=2, name="Inactive Plan", display_name="Inactive Plan (30 days)", is_active=False, default_amount=100.0, duration_days=30)
    ]

    # 2. Patch the API instance in the app's namespace
    with unittest.mock.patch('reporter.streamlit_ui.app.api', new=mock_api):
        initialize_database() # Initialize database
        # 3. Initialize the AppTest on the UI file
        at = AppTest.from_file("reporter/streamlit_ui/app.py").run()

        # 4. Navigate to the Group Plans tab
        at.tabs[1].run()

        # 5. Assert that only the active plan is shown in the selectbox
        assert len(at.selectbox) > 0 # Ensure the selectbox is present
        assert "Active Plan" in at.selectbox(key="group_plan_select_widget").options[1]
        assert "Inactive Plan" not in str(at.selectbox(key="group_plan_select_widget").options)
        assert at.error == [] # Ensure no errors were thrown


def test_ui_displays_correct_plan_amount():
    """
    Tests that the UI correctly uses plan.default_amount to display the price.
    """
    mock_api = unittest.mock.MagicMock(spec=AppAPI)
    mock_api.get_all_group_plans_for_view.return_value = [
        GroupPlanView(id=1, name="Test Plan", display_name="Test Plan (30 days)", is_active=True, default_amount=1234.56, duration_days=30)
    ]

    with unittest.mock.patch('reporter.streamlit_ui.app.api', new=mock_api):
        initialize_database() # Initialize database
        at = AppTest.from_file("reporter/streamlit_ui/app.py").run()
        at.tabs[1].run() # Navigate to Group Plans tab

        # Select the plan to populate the edit form
        at.selectbox(key="group_plan_select_widget").select(1).run()

        # Assert that the number_input for the amount shows the correct value
        assert at.number_input(key="group_plan_form_amount").value == 1234.56
        assert at.error == []

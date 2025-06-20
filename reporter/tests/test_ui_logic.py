import datetime  # Added datetime
import unittest.mock

from streamlit.testing.v1 import AppTest

from reporter.database import initialize_database  # Added import
from reporter.models import GroupPlanView, MemberView  # Added MemberView
from reporter.streamlit_ui.app import AppAPI


def test_ui_filters_for_active_plans():
    """
    Tests that the UI correctly uses plan.is_active to filter plans.
    """
    # 1. Mock the API to avoid real database calls
    mock_api = unittest.mock.MagicMock(spec=AppAPI)
    mock_api.get_all_group_plans_for_view.return_value = [
        GroupPlanView(
            id=1,
            name="Active Plan",
            display_name="Active Plan (30 days)",
            is_active=True,
            default_amount=100.0,
            duration_days=30,
        ),
        GroupPlanView(
            id=2,
            name="Inactive Plan",
            display_name="Inactive Plan (30 days)",
            is_active=False,
            default_amount=100.0,
            duration_days=30,
        ),
    ]

    # 2. Patch the API instance in the app's namespace
    with unittest.mock.patch("reporter.streamlit_ui.app.api", new=mock_api):
        initialize_database()  # Initialize database
        # 3. Initialize the AppTest on the UI file
        at = AppTest.from_file("reporter/streamlit_ui/app.py").run()

        # 4. Navigate to the Group Plans tab
        at.tabs[1].run()

        # 5. Assert that only the active plan is shown in the selectbox
        assert len(at.selectbox) > 0  # Ensure the selectbox is present
        assert "Active Plan" in at.selectbox(key="group_plan_select_widget").options[1]
        assert "Inactive Plan" not in str(
            at.selectbox(key="group_plan_select_widget").options
        )
        assert at.error == []  # Ensure no errors were thrown


def test_ui_displays_correct_plan_amount():
    """
    Tests that the UI correctly uses plan.default_amount to display the price.
    """
    mock_api = unittest.mock.MagicMock(spec=AppAPI)
    mock_api.get_all_group_plans_for_view.return_value = [
        GroupPlanView(
            id=1,
            name="Test Plan",
            display_name="Test Plan (30 days)",
            is_active=True,
            default_amount=1234.56,
            duration_days=30,
        )
    ]

    with unittest.mock.patch("reporter.streamlit_ui.app.api", new=mock_api):
        initialize_database()  # Initialize database
        at = AppTest.from_file("reporter/streamlit_ui/app.py").run()
        at.tabs[1].run()  # Navigate to Group Plans tab

        # Select the plan to populate the edit form
        at.selectbox(key="group_plan_select_widget").select(1).run()

        # Assert that the number_input for the amount shows the correct value
        assert at.number_input(key="group_plan_form_amount").value == 1234.56
        assert at.error == []


def test_ui_create_new_group_class_membership():
    """
    Tests the creation of a new group class membership via the UI.
    """
    mock_api = unittest.mock.MagicMock(spec=AppAPI)

    sample_member = MemberView(
        id=1,
        name="Test Member",
        phone="1234567890",
        email="test@example.com",
        join_date="2024-01-01",
        is_active=True,
    )
    sample_plan = GroupPlanView(
        id=1,
        name="Gold Plan",
        display_name="Gold Plan (30 days)",
        is_active=True,
        default_amount=100.0,
        duration_days=30,
    )

    mock_api.get_all_members_for_view.return_value = [sample_member]
    mock_api.get_all_group_plans_for_view.return_value = [sample_plan]
    mock_api.create_group_class_membership.return_value = 99  # Mocked new membership ID

    with unittest.mock.patch("reporter.streamlit_ui.app.api", new=mock_api):
        initialize_database()
        at = AppTest.from_file("reporter/streamlit_ui/app.py").run()

        # Navigate to Memberships Tab
        at.tabs[2].run()  # Members, Group Plans, Memberships, Reporting

        # Ensure Group Class Memberships mode is selected (it's default, this confirms)
        assert (
            at.radio(key="membership_mode_selector").value == "Group Class Memberships"
        )

        # Click "Add New Group Class Membership" button
        # This button sets session_state.selected_gc_membership_id = "add_new"
        # which should make the correct form appear.
        add_new_button = at.button(key="gc_add_new_button")
        assert add_new_button is not None
        add_new_button.click().run()

        # Verify the subheader changed, indicating the form for adding is likely active
        # This is a proxy for checking st.session_state.selected_gc_membership_id == "add_new"
        assert "Add New Group Class Membership" in [h.value for h in at.subheader]

        # Interact with the form elements
        # The form key is dynamic (st.session_state.gc_membership_form_key),
        # so we assume it's the first (and only active) form after clicking "Add New".
        form = at.form[0]
        form.selectbox(key="gc_form_member_id_select").select(
            option=sample_member.id
        ).run()
        form.selectbox(key="gc_form_plan_id_select").select(option=sample_plan.id).run()

        test_start_date = datetime.date(2024, 7, 1)
        form.date_input(key="gc_form_start_date").set_value(test_start_date).run()

        test_amount_paid = 150.0
        form.number_input(key="gc_form_amount_paid").set_value(test_amount_paid).run()

        # Submit the form
        form.submit().run()

        # Assertions
        mock_api.create_group_class_membership.assert_called_once_with(
            member_id=sample_member.id,
            plan_id=sample_plan.id,
            start_date_str=test_start_date.strftime("%Y-%m-%d"),
            amount_paid=test_amount_paid,
        )

        # Check for success message (optional, but good)
        assert len(at.success) > 0
        assert "Group Class Membership created with ID: 99" in at.success[0].value
        assert at.error == []

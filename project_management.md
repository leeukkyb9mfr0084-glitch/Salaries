### **Overall Objective for Jules**

Your goal is to align the application's source code with the corrected documentation. This involves updating the Data Transfer Objects (DTOs) and the Streamlit UI code. Finally, you will create new UI-level tests to verify these changes.

---

### **Phase 1: Align the Data Model (DTO)**

**>> COMMAND:** Update the `GroupPlanView` DTO to use the correct attribute for price, matching the specification.

**>> FILE:** `reporter/models.py`

**>> INSTRUCTION:** Find the `@dataclass class GroupPlanView` and replace its entire definition with the following corrected version.

**>> REPLACE WITH:**
```python
@dataclass
class GroupPlanView:
    id: int
    name: str
    display_name: str
    is_active: bool # Moved before fields with defaults
    default_amount: float
    duration_days: int
```

---

### **Phase 2: Correct the UI Logic**

**>> COMMAND:** Update the Streamlit UI to use the corrected DTO attributes. This will fix the runtime bugs.

**>> FILE:** `reporter/streamlit_ui/app.py`

**>> INSTRUCTION 1 of 2:** Search through the entire file for any instance where the code checks `plan.status == 'Active'`. Replace this with a check for the boolean `plan.is_active`. This will primarily affect the `render_group_plans_tab` and `render_memberships_tab` functions.

**>> INSTRUCTION 2 of 2:** Search through the entire file for any instance where the code accesses `plan.price`. Replace this with `plan.default_amount`. This will primarily affect the `render_group_plans_tab` and `render_memberships_tab` functions.

---

### **Phase 3: Implement UI Verification Tests**

**>> COMMAND:** Create a new test file and add specific tests for the UI logic using Streamlit's `AppTest` framework. This will confirm the fixes from Phase 2 are working correctly.

**>> INSTRUCTION 1 of 3: Create the new test file.**
* Create a new, empty file at this exact path: `reporter/tests/test_ui_logic.py`.

**>> INSTRUCTION 2 of 3: Add a test for the active plan filter.**
* In `reporter/tests/test_ui_logic.py`, add the following Python code. This test will mock the API and verify that the UI correctly filters for active plans.

**>> ADD THE FOLLOWING CODE:**
```python
import unittest.mock
from reporter.streamlit_ui.app import AppAPI
from reporter.models import GroupPlanView
from streamlit.testing.v1 import AppTest

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
        # 3. Initialize the AppTest on the UI file
        at = AppTest.from_file("reporter/streamlit_ui/app.py").run()
        
        # 4. Navigate to the Group Plans tab
        at.tabs[1].run()

        # 5. Assert that only the active plan is shown in the selectbox
        assert len(at.selectbox) > 0 # Ensure the selectbox is present
        assert "Active Plan" in at.selectbox(key="group_plan_select_widget").options[1]
        assert "Inactive Plan" not in str(at.selectbox(key="group_plan_select_widget").options)
        assert at.error == [] # Ensure no errors were thrown
```

**>> INSTRUCTION 3 of 3: Add a test for the correct amount display.**
* In `reporter/tests/test_ui_logic.py`, add the following Python code. This test verifies the UI uses `default_amount`.

**>> ADD THE FOLLOWING CODE:**
```python
def test_ui_displays_correct_plan_amount():
    """
    Tests that the UI correctly uses plan.default_amount to display the price.
    """
    mock_api = unittest.mock.MagicMock(spec=AppAPI)
    mock_api.get_all_group_plans_for_view.return_value = [
        GroupPlanView(id=1, name="Test Plan", display_name="Test Plan (30 days)", is_active=True, default_amount=1234.56, duration_days=30)
    ]

    with unittest.mock.patch('reporter.streamlit_ui.app.api', new=mock_api):
        at = AppTest.from_file("reporter/streamlit_ui/app.py").run()
        at.tabs[1].run() # Navigate to Group Plans tab
        
        # Select the plan to populate the edit form
        at.selectbox(key="group_plan_select_widget").select(1).run()

        # Assert that the number_input for the amount shows the correct value
        assert at.number_input(key="group_plan_form_amount").value == 1234.56
        assert at.error == []
```

---

### **Final Verification Step**

**>> COMMAND:** Run the entire test suite to ensure all existing and new tests pass.

**>> INSTRUCTION:** Execute the `pytest` command from the root directory of the project. Confirm that all tests complete successfully with no errors or failures.
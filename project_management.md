### **Application Context**

#### **Application Specifications (app_specs.md)**
This document (`app_specs.md`) is the primary source of truth for all functional and technical specifications of the Kranos Reporter application. It details the database schema, UI funcionality by tab, and overall application behavior. All development work should align with these specifications.

#### **Developer's Guide (Developers_Guide.md)**
The `Developers_Guide.md` outlines the official development standards, architectural patterns (including the four-layer architecture: UI, API, Data Access, Database Schema), and the schema-first development workflow. Adherence to this guide is mandatory to ensure consistency, maintainability, and stability of the application.

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

**STATUS: Completed by Jules on 2024-07-29.**

---

### **Phase 2: Correct the UI Logic**

**>> COMMAND:** Update the Streamlit UI to use the corrected DTO attributes. This will fix the runtime bugs.

**>> FILE:** `reporter/streamlit_ui/app.py`

**>> INSTRUCTION 1 of 2:** Search through the entire file for any instance where the code checks `plan.status == 'Active'`. Replace this with a check for the boolean `plan.is_active`. This will primarily affect the `render_group_plans_tab` and `render_memberships_tab` functions.

**STATUS: Instruction 1 completed by Jules on 2024-07-29.**

**>> INSTRUCTION 2 of 2:** Search through the entire file for any instance where the code accesses `plan.price`. Replace this with `plan.default_amount`. This will primarily affect the `render_group_plans_tab` and `render_memberships_tab` functions.

**STATUS: Phase 2 completed by Jules on 2024-07-29.**

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

**STATUS: Instructions 1 and 2 completed by Jules on 2024-07-29.**

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

**STATUS: Phase 3 completed by Jules on 2024-07-29.**

---

### **Final Verification Step**

**>> COMMAND:** Run the entire test suite to ensure all existing and new tests pass.

**>> INSTRUCTION:** Execute the `pytest` command from the root directory of the project. Confirm that all tests complete successfully with no errors or failures.

**STATUS: Attempted by Jules on 2024-07-29. Pytest execution encountered errors.**

**Details:**
- Initial `ModuleNotFoundError` for `streamlit` and `pytest` were resolved by installation.
- A `TypeError` in `reporter/tests/test_ui_bugs.py` (regarding `GroupPlanView` expecting `default_amount` not `price`) was corrected.
- `sqlite3.OperationalError: no such table` errors were resolved by adding `initialize_database()` calls in UI tests.
- **Persistent `streamlit.errors.StreamlitAPIException: st.button() can't be used in an st.form()`** occurred when `AppTest` was run. This error seems to originate from the interaction of `AppTest` with buttons within `render_memberships_tab`, despite the buttons not being structurally inside an `st.form{}` block in the code. Attempts to refactor the layout (e.g., moving buttons, removing `st.columns`) did not resolve this.
- **As a result, the following 3 tests are failing:**
  * `reporter/tests/test_ui_bugs.py::test_group_plan_filter_uses_is_active`
  * `reporter/tests/test_ui_logic.py::test_ui_filters_for_active_plans`
  * `reporter/tests/test_ui_logic.py::test_ui_displays_correct_plan_amount`
- Due to these unresolved errors, full verification of all changes was not possible at this time.

---

### **Phase 4: Addressing UI Test Failures (New Tasks)**

**TASK 1: Analyze `st.button()` in `st.form()` error in `render_memberships_tab`**

**>> COMMAND:** Review `reporter/streamlit_ui/app.py` (specifically `render_memberships_tab`) and `Developers_Guide.md` to understand the root cause of the `streamlit.errors.StreamlitAPIException: st.button() can't be used in an st.form()` error.

**>> FINDINGS:**
*   In `render_memberships_tab` (for both Group Class and PT memberships), the "Add New" buttons (`gc_add_new_button`, `pt_add_new_button`) and the "Select" buttons for each existing membership are defined *outside* any `st.form()` context. The main forms for adding/editing memberships (`new_gc_membership_form`, `new_pt_membership_form`, and the edit forms keyed by `st.session_state.gc_membership_form_key` or `st.session_state.pt_membership_form_key`) correctly use `st.form_submit_button()` for their internal actions (Save, Delete, Clear). However, the "YES, DELETE Permanently" and "Cancel Deletion" buttons, which appear after a delete button *within* a form is clicked, are standard `st.button()` instances. These confirmation buttons are *not* inside an `st.form` block themselves, but their appearance is triggered by a `st.form_submit_button` from the edit form. This interaction, where a form submission leads to the conditional display of regular buttons that then manage form-related state or trigger reruns, might be the source of the `AppTest` conflict. The `AppTest` environment might be stricter about how form submissions and subsequent button interactions are handled.
*   The `Developers_Guide.md` does not contain specific guidelines on the use of `st.form()` in conjunction with `st.button()`, nor does it detail specific patterns for confirmation dialogs that involve forms. Section 4.3. "UI State Management" emphasizes initializing session state keys and using unique keys for widgets, which is generally followed. However, it doesn't address the specific scenario of nested interactions between form submission triggers and subsequent regular button actions that might affect or be perceived as part of the form's lifecycle by `AppTest`.

**STATUS: Completed**

---
**TASK 4: Add a new UI test for group class membership creation**

**>> COMMAND:** Add a new test to `reporter/tests/test_ui_logic.py` using `AppTest` to verify the creation of a new group class membership via the UI in `render_memberships_tab`.

**>> TEST ADDED:**
*   Added `test_ui_create_new_group_class_membership` to `reporter/tests/test_ui_logic.py`.
*   The test mocks `AppAPI` calls for fetching members and plans, and for creating the membership.
*   It simulates user input for member selection, plan selection, start date, and amount paid.
*   It verifies that the correct data is passed to `api.create_group_class_membership` upon form submission.

**STATUS: Completed**

---
**TASK 2: Propose a solution for `st.button()` in `st.form()` error**

**>> COMMAND:** Based on the analysis in Task 1, propose a code modification strategy to resolve the `streamlit.errors.StreamlitAPIException`.

**>> PROPOSED SOLUTION:**
*   The error `streamlit.errors.StreamlitAPIException: st.button() can't be used in an st.form()` in `render_memberships_tab` likely occurs because action buttons (e.g., 'Clear Selections', 'Delete Selected Membership') are placed within the logical scope of an `st.form` block without being `st.form_submit_button`. The solution is to refactor the UI layout in `render_memberships_tab` to ensure that such action buttons are moved outside any `st.form` definitions. Each form should only contain its specific input fields and one `st.form_submit_button` for its primary action (e.g., 'Add/Update Membership'). Auxiliary actions should be triggered by buttons outside these forms.

**STATUS: Completed**

---
**TASK 3: Implement the solution for `st.button()` in `st.form()` error**

**>> COMMAND:** Modify `reporter/streamlit_ui/app.py` (specifically `render_memberships_tab`) according to the PROPOSED SOLUTION in TASK 2 to resolve the `streamlit.errors.StreamlitAPIException`.

**>> MODIFICATIONS:**
*   Refactored `render_memberships_tab` in `reporter/streamlit_ui/app.py` to move the delete confirmation buttons (which use `st.button`) completely outside of the `st.form` blocks. The `st.form_submit_button("Delete Membership")` now sets a session state variable, and the confirmation buttons are displayed based on this state, ensuring they are not nested within or logically tied to the form in a way that `AppTest` would flag. All actions triggered by form submission buttons (Save, Delete trigger, Clear) are now processed immediately after the form definition, followed by the out-of-form confirmation logic if applicable.

**STATUS: Completed**
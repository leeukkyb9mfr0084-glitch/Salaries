Of course. Here is the updated project management plan with checkboxes for tracking progress.

***

# Kranos Reporter v2.0 - Remaining Tasks

**Developer:** Junior Developer
**Date:** 2025-06-15
**Objective:** Address critical bugs, complete the remaining UI features as per the application specifications, and validate the final product.

---

### **Phase 1: Critical Bug Fixes & Test Suite Alignment**

*Goal: Create a stable foundation by fixing blocking errors and refactoring the tests to match the current Streamlit architecture.*

* [ ] **Task 1.1: Fix Application Startup `NameError`**
    * **Context:** The Streamlit app crashes on startup due to a `NameError` because the type hint `Tuple` is used without being imported in `reporter/app_api.py`.
    * **Instructions:**
        1.  Open the file `reporter/app_api.py`.
        2.  At the top of the file, add the following import statement: `from typing import Tuple, Optional`.
        3.  This will make the `Tuple` and `Optional` type hints available, resolving the error.

* [ ] **Task 1.2: Update Project Dependencies**
    * **Context:** The test logs show a `ModuleNotFoundError` for `openpyxl`, which is required for generating Excel reports. This dependency is missing from the project's requirements file.
    * **Instructions:**
        1.  Open the `requirements.txt` file.
        2.  Add the line `openpyxl` to the file.
        3.  This ensures that the dependency is installed when setting up the environment, allowing the report generation features to function correctly.

* [ ] **Task 1.3: Refactor Test Suite Imports**
    * **Context:** The `test_results.log` indicates that `test_book_closing.py`, `test_gui_flows.py`, and `test_main.py` are failing because they try to import `reporter.gui`, a module that does not exist. The UI is now handled by Streamlit. These tests need to be refactored to test the business logic directly, not a defunct UI.
    * **Instructions:**
        1.  Go through each of the failing test files (`test_book_closing.py`, `test_gui_flows.py`, `test_main.py`).
        2.  Remove any `import` statements related to `reporter.gui`.
        3.  Modify the tests to call the `AppAPI` or `DatabaseManager` methods directly instead of simulating GUI interactions from the old Flet app. The goal is to validate the backend logic, not the UI, with these scripts.

---

### **Phase 2: UI Feature Completion**

*Goal: Implement the remaining user interface tabs and features as detailed in the `app_specs.md` document.*

* [ ] **Task 2.1: Implement "Members" Tab Actions**
    * **Context:** The main layout of the "Members" tab is done, but the action buttons for each row ("History", "Edit", "Delete") are not fully functional.
    * **Instructions:**
        1.  **Edit Button:** Wire the "Edit" button to populate the "Add/Edit Member" form with the data from the selected row.
        2.  **Delete Button:** Wire the "Delete" button to call the `api.deactivate_member` function, passing the correct `member_id`.
        3.  **History Modal:** On clicking the "History" button, implement the logic to open a modal window that displays the full transaction history for the selected member, including a calculated total amount paid.

* [ ] **Task 2.2: Build "Memberships" Tab**
    * **Context:** This tab is currently a placeholder and needs to be built out.
    * **Instructions:**
        1.  Implement the two-column layout as per the spec.
        2.  On the left, build the "Add Membership" form. This form should allow selecting a member and a plan, and inputting payment details.
        3.  On the right, display a filterable list of recent transactions.
        4.  At the bottom, add the "Close Books for Month" section with the month/year selection and the "Close Books" button.

* [ ] **Task 2.3: Build "Plans" Tab**
    * **Context:** This tab needs to be implemented to allow for plan management.
    * **Instructions:**
        1.  Create the specified two-column layout.
        2.  On the left, build the "Add/Edit Plan" form. This should handle both creating new plans and updating existing ones.
        3.  On the right, display a list of all existing plans. Each row must include an "Active" checkbox and "Edit"/"Delete" buttons, and their functionality must be implemented.

* [ ] **Task 2.4: Build "Reporting" Tab**
    * **Context:** This tab needs to be implemented to display financial and renewal reports.
    * **Instructions:**
        1.  Create the two vertical sections as per the spec.
        2.  Implement the "Monthly Report" section, which should fetch and display a table of transactions for a selected month and year.
        3.  Implement the "Upcoming Renewals" section, which should display a table of memberships due for renewal in a selected month.

---

### **Phase 3: Final Validation & Testing**

*Goal: Perform comprehensive testing to ensure all features work correctly and the application is stable.*

* [ ] **Task 3.1: CRUD Testing**
    * **Context:** Once the UI and bug fixes are complete, we need to test all Create, Read, Update, and Delete operations.
    * **Instructions:**
        1.  **Members:** Thoroughly test adding, editing, searching, filtering, and deactivating members.
        2.  **Plans:** Test adding, editing, deleting, and activating/deactivating plans.
        3.  **Memberships:** Test adding and deleting membership transactions for members.

* [ ] **Task 3.2: Functionality Testing**
    * **Context:** Key application features need to be validated to ensure they work as expected.
    * **Instructions:**
        1.  Verify the member "History" modal displays correct data.
        2.  Verify the "Close Books" functionality correctly prevents further transactions in a closed month.
        3.  Verify both reports on the "Reporting" tab generate accurate data based on the transactions in the database.

* [ ] **Task 3.3: Final Code Review**
    * **Context:** A final code review is needed to ensure the codebase is clean, maintainable, and free of any dead code or unnecessary comments from previous versions.
    * **Instructions:**
        1.  Perform a full review of the project's Python files.
        2.  Remove any old, commented-out code blocks.
        3.  Ensure all code adheres to the standards outlined in the `Developers_Guide.md`.
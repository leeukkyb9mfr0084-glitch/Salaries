**Objective:** To refactor the application to be fully functional and bug-free. Follow these instructions precisely to build the required functionality.

### **Phase 1: Align Database Schema & Data Models**
*This phase is the foundation. We are making our database and data models match the required application structure.*

* **Task 1.1: Update `pt_memberships` Table** - DONE
    * **File:** `reporter/database.py`
    * **Context:** We are simplifying the personal training data model by removing unused fields.
    * **Instruction:** Find the `CREATE TABLE pt_memberships` SQL statement and delete the entire line containing the `notes TEXT,` definition.

* **Task 1.2: Align `group_class_memberships` Table** - DONE
    * **File:** `reporter/database.py`
    * **Context:** To ensure complete and accurate tracking of time-based memberships, we need a precise table structure.
    * **Instruction:** Modify the `CREATE TABLE group_class_memberships` statement to ensure it contains exactly these columns in this order: `id`, `member_id`, `plan_id`, `start_date`, `end_date`, `amount_paid`, `purchase_date`, `membership_type`, and `is_active`.

* **Task 1.3: Verify `group_plans` Table** - DONE
    * **File:** `reporter/database.py`
    * **Context:** The `group_plans` table defines the templates for all group memberships, and its structure must be exact for consistency.
    * **Instruction:** Ensure the `group_plans` table schema in `database.py` exactly matches the following structure: `id` (INTEGER, PK), `name` (TEXT), `duration_days` (INTEGER), `default_amount` (REAL), `display_name` (TEXT, UNIQUE), `is_active` (BOOLEAN).

* **Task 1.4: Update `PTMembershipView` DTO - DONE**
    * **File:** `reporter/models.py`
    * **Context:** To fix a critical data bug where the "amount paid" was being lost during UI edits, and to match our simplified database, we need to update the `PTMembershipView` DTO.
    * **Instruction:** In the `@dataclass class PTMembershipView`, delete the `notes: str` attribute. Then, add a new attribute: `amount_paid: float`.

* **Task 1.5: Standardize `is_active` Flag in DTOs - DONE**
    * **File:** `reporter/models.py`
    * **Context:** We are implementing a project-wide standard for consistency. This ensures we handle active/inactive records the same way everywhere.
    * **Instruction:** For all "View" DTOs in this file (`MemberView`, `GroupPlanView`, `GroupClassMembershipView`), you must replace any `status: str` attribute with `is_active: bool`.

* **Task 1.6: Final Schema-DTO Verification - DONE**
    * **Files:** `reporter/database.py`, `reporter/models.py`
    * **Context:** This step is a crucial quality check to ensure data flows predictably between the database and the application.
    * **Instruction:** Perform a final visual check. For every column in each table in `database.py`, confirm that a matching attribute with the correct Python type exists in the corresponding DTO in `models.py`.

### **Phase 2: Refactor the Data Access Layer**
*This phase ensures our code communicates correctly with the updated database.*

* **Task 2.1: Correct All `get` Queries - DONE**
    * **File:** `reporter/database_manager.py`
    * **Context:** The queries are currently broken because they refer to old column names. They must be updated to correctly populate our new DTOs from Phase 1.
    * **Instruction:** Review every function that fetches data for a "View" (e.g., `get_all_pt_memberships_for_view`). Modify its SQL `SELECT` statement to use the corrected column names (`is_active` instead of `status`) and to fetch all fields required by the updated DTOs (like `amount_paid` for `PTMembershipView`).

* **Task 2.2: Fix `add_pt_membership` Logic - DONE**
    * **File:** `reporter/database_manager.py`
    * **Context:** We are moving the business logic for new PT packages into the data layer to make it more robust and reliable.
    * **Instruction:** Modify the `add_pt_membership` function so it automatically sets the remaining sessions.
        1.  Remove the `notes` and `sessions_remaining` parameters from the function signature.
        2.  In the `INSERT` statement, use the `sessions_purchased` value passed into the function for *both* the `sessions_total` and `sessions_remaining` columns.

* **Task 2.3: Remove Redundant Function - DONE**
    * **File:** `reporter/database_manager.py`
    * **Context:** To simplify our backend and reduce redundant code, we are removing this function. The new, cleaner pattern is to filter data in the UI layer.
    * **Instruction:** Delete the entire `get_active_members_for_view` function.

### **Phase 3: Synchronize the API Layer**
*This phase ensures the API provides a clean, correct interface to the UI.*

* **Task 3.1: Fix `create_pt_membership` Signature - DONE**
    * **File:** `reporter/app_api.py`
    * **Context:** The API layer must always stay in sync with the Data Access Layer it calls.
    * **Instruction:** Find the `create_pt_membership` function. Update its signature to match the changes from Phase 2. Remove the `notes` and `sessions_remaining` parameters from the function signature and from the call to the database manager.

* **Task 3.2: Verify All API Signatures - DONE**
    * **File:** `reporter/app_api.py`
    * **Context:** This is a quality check to ensure data consistency across the application layers.
    * **Instruction:** Briefly review all other functions in this file. Ensure the arguments they accept and the DTOs they return are consistent with the updated functions in `database_manager.py` and the DTOs in `models.py`.

### **Phase 4: Realign the User Interface**
*This phase implements the required user experience.*

* **Task 4.1: Restructure the `Memberships` Tab Layout - DONE**
    * **File:** `reporter/streamlit_ui/app.py`
    * **Context:** We are redesigning the Memberships tab for a more intuitive workflow, with creation/editing on the left and viewing/selection on the right.
    * **Instruction:** In the `render_memberships_tab` function:
        1.  Define a two-column layout: `left_col, right_col = st.columns([1, 2])`.
        2.  Move the entire `st.form` for creating and editing a membership into the `with left_col:` block.
        3.  In the `with right_col:` block, add widgets to display a list of all existing memberships. This list needs a selection mechanism (e.g., a "Select" button for each row) that, when clicked, populates the form on the left for editing. Use `st.session_state` to pass the ID of the selected record.

* **Task 4.2: Remove "Notes" Field from UI**
    * **File:** `reporter/streamlit_ui/app.py`
    * **Context:** Notes are no longer part of the PT membership data model and must be removed from the UI.
    * **Instruction:** From the PT membership form you just refactored, find and delete the `st.text_area("Notes", ...)` widget.

* **Task 4.3: Fix PT Membership Edit Bug**
    * **File:** `reporter/streamlit_ui/app.py`
    * **Context:** This fixes a critical data corruption bug where the amount paid could be reset to zero upon editing.
    * **Instruction:** When a PT membership is selected for editing, ensure the `amount_paid` value from its DTO (`selected_pt_data.amount_paid`) is used to populate the `value` of the "Amount Paid (₹)" `st.number_input` in the form.

* **Task 4.4: Implement UI-Side Filtering**
    * **File:** `reporter/streamlit_ui/app.py`
    * **Context:** We are adopting a new, standard pattern for filtering data in the UI to simplify the backend.
    * **Instruction:** Find all UI dropdowns that need to be populated with only *active* members or plans. Change them to fetch all items using `get_all_..._for_view()` and then filter the list in your UI code before displaying it.
        * **Example Pattern:**
            ```python
            all_members = api.get_all_members_for_view()
            active_members = [m for m in all_members if m.is_active]
            # ... now use the 'active_members' list to populate the st.selectbox
            ```

### **Phase 5: Update Verification & Data Migration**
*This final development phase ensures our application is correct and our tests are reliable.*

* **Task 5.1: Update Data Migration Script**
    * **File:** `reporter/migrate_historical_data.py`
    * **Context:** The migration script is broken because our function signatures have changed.
    * **Instruction:** Find the line that calls `create_pt_membership` and update the function call to use the new, simpler signature from Phase 3.

* **Task 5.2: Rewrite Database & Logic Tests**
    * **Files:** `reporter/tests/test_database_manager.py`, `reporter/tests/test_pt_memberships.py`
    * **Context:** Our tests are our safety net and must be updated to reflect the new code logic. These tests must not involve the UI.
    * **Instruction:** Go through these files test by test. Each test must follow this pattern: 1. Create a temporary in-memory database. 2. Call the `database_manager` function being tested. 3. Use `cursor.execute('SELECT ...')` to check if the data was written to the database correctly according to the new schemas.

* **Task 5.3: Run the Full Test Suite**
    * **Context:** This is the final quality gate before the work is considered complete.
    * **Instruction:** Open your command line terminal, navigate to the project's root directory, and run the command `pytest`. All tests must pass with no errors or failures.
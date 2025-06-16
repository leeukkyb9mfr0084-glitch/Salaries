
# Project Remediation and Cleanup Plan

**Objective:** To align the entire application with the `app_specs.md` and `Developers_Guide.md`, fix critical bugs, and establish a stable, testable, and maintainable codebase.

**Instructions for Developer:**
- Follow the phases in order, from 1 to 4. Do not skip steps.
- Mark the checkbox `[x]` as you complete each task.
- The `app_specs.md` is our single source of truth. When in doubt, refer to it.

---

### Phase 1: Foundation and Schema Alignment (The Great Cleanup)

*Goal: Establish a single, correct database schema and remove all outdated code, tests, and documentation that contradict the `app_specs.md`. This is the most critical phase.*

- [x] **1.1: Align `plans` Table with Spec**
  - **Why:** The spec states that a plan's duration is flexible and should be decided when a membership is created, not fixed to the plan itself. The `default_duration` column contradicts this fundamental requirement.
  - **Action:** In `reporter/database.py`, find the `create_plans_table` function. Delete the line that adds the `default_duration` column to the SQL `CREATE TABLE` statement.

- [x] **1.2: Delete Outdated Project Documentation**
  - **Why:** The old `project_management.md` contains outdated information about a `transactions` table that confuses the project's direction.
  - **Action:** Delete the old `project_management.md` file from the project. This new file is its replacement.

- [x] **1.3: Update Core Documentation**
  - **Why:** The `README.md` is the first thing a new developer sees. It must reflect the current architecture.
  - **Action:** In `README.md`, read through the file and remove any sentences or sections that talk about a `transactions` table. Ensure it correctly refers to the `memberships` table as the core data store.

- [x] **1.4: Fix Broken Data Migration Script**
  - **Why:** This script is essential for loading initial data, but it's completely broken because it's trying to write to a `transactions` table that doesn't exist.
  - **Action:** In `reporter/migrate_data.py`, modify the script. Change all SQL queries that `INSERT` into or `DELETE` from the `transactions` table to target the `memberships` table instead. You will also need to adjust the columns in the `INSERT` statement to match the columns in the `memberships` table.

- [x] **1.5: Delete Unusable Tests**
  - **Why:** These tests are worse than useless; they are misleading. They test for functionality and tables that no longer exist and cannot be salvaged.
  - **Action:** Delete the following three test files entirely:
    - `reporter/tests/test_book_closing.py`
    - `reporter/tests/test_business_logic.py`
    - `reporter/tests/test_migrate_data.py`

---

### Phase 2: Fix Core Business Logic

*Goal: Ensure the API, business logic, and UI are correctly wired together and handle data as expected.*

- [ ] **2.1: Fix API Function Signature Mismatch**
  - **Why:** The UI (`streamlit_ui/app.py`) calls the API with a single dictionary object, but the business logic layer (`database_manager.py`) expects multiple, separate arguments. This will cause a `TypeError` and crash the application. The API layer must correctly translate requests from the client.
  - **Action:** In `reporter/database_manager.py`, modify the `create_membership_record` function signature. Change it from `def create_membership_record(self, member_id, plan_id, ...)` to `def create_membership_record(self, data)`. Then, inside the function, unpack the dictionary to get your variables (e.g., `member_id = data['member_id']`, `plan_id = data['plan_id']`, etc.).

- [ ] **2.2: Add Missing Dependency**
  - **Why:** The `reporter/main.py` file imports the `flet` library, but this is not declared in `requirements.txt`. The application will fail to start in any new environment where dependencies are installed from this file.
  - **Action:** Open the `requirements.txt` file and add `flet` on a new line.

---

### Phase 3: Align User Interface with Specs

*Goal: Correct the UI workflows to match the `app_specs.md` precisely.*

- [ ] **3.1: Fix Membership Selection**
  - **Why:** The `app_specs.md` requires a more intuitive workflow where users click directly on a table row to select it for editing or deletion. The current dropdown is less user-friendly and violates the spec.
  - **Action:** In `reporter/streamlit_ui/app.py`, remove the `st.selectbox` currently used for selecting a membership to edit/delete. The goal is to make the rows of the main membership dataframe selectable. You will need to find a method to capture a click event on the dataframe to get the ID of the selected row and store it in the session state for the `EDIT` and `DELETE` buttons to use.

- [ ] **3.2: Correct Renewals Report Logic**
  - **Why:** The spec requires a dynamic, rolling 30-day view of upcoming renewals, which is more useful for proactive management. The current monthly view is static and doesn't meet this requirement. The backend logic is already correct; the UI just needs to use it properly.
  - **Action:** In `reporter/streamlit_ui/app.py`, go to the "Reporting" tab's "Renewals Report" section. Remove the date and month selector widgets. Modify the logic so that the `api.generate_renewal_report_data()` function is called *without* any date arguments. This will allow the backend to correctly use its default logic of finding renewals in the next 30 days.

---

### Phase 4: Re-establish Testing Foundation

*Goal: Create a baseline of useful tests that reflect the current, correct state of the application.*

- [ ] **4.1: Write New `test_database_manager.py`**
  - **Why:** Having deleted the old, broken tests, we now have zero test coverage for our core business logic. We need to create new tests to ensure the `DatabaseManager` functions work correctly with the proper `memberships` schema. This is critical for preventing future bugs.
  - **Action:** Create a new file: `reporter/tests/test_database_manager.py`. In this file, write new `pytest` functions that specifically test the main business logic: `create_membership_record`, `generate_financial_report_data`, and `generate_renewal_report_data`. Use `pytest` fixtures to manage a temporary test database.

- [ ] **4.2: Write New `test_plan_management.py`**
  - **Why:** We need to ensure that the basic operations for managing plans are working correctly after our schema changes in Phase 1.
  - **Action:** In the existing file `reporter/tests/test_plan_management.py`, review and update the tests to align with the corrected schema (i.e., no `default_duration`). Add simple tests to verify the creation and retrieval of plans.

```
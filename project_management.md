### Kranos Reporter: Development Plan v6.0

**Objective:** Refactor the application to support both Group Class (GC) memberships and Personal Training (PT) memberships within a unified interface. This involves schema changes, backend logic updates, and a UI overhaul with consistent naming conventions.

---
**Phase 1: Database Schema Update**
* **Task:** `[PENDING]` Update `reporter/database.py` to implement the new, approved schema.
* **Instructions:**
    1.  In `create_database()`, rename the `plans` table to `group_plans`. Update its `CREATE TABLE` statement.
    2.  Rename the `memberships` table to `group_class_memberships`. Ensure its foreign key (`plan_id`) correctly references the `id` column of `group_plans`.
    3.  Add the new `pt_memberships` table. The schema must be:
        ```sql
        CREATE TABLE IF NOT EXISTS pt_memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            purchase_date TEXT,
            amount_paid REAL,
            sessions_purchased INTEGER,
            sessions_remaining INTEGER,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );
        ```
    4.  Update the `seed_initial_plans()` function to insert data into the `group_plans` table.

---
**Phase 2: Backend Logic Refactoring**
* **Task:** `[PENDING]` Update `reporter/database_manager.py` to manage the new tables.
* **Instructions:**
    1.  Rename functions related to `plans` to specify `group_plans` (e.g., `add_plan` -> `add_group_plan`).
    2.  Rename functions related to the old `memberships` table to specify `group_class_memberships` (e.g., `create_membership` -> `create_group_class_membership`).
    3.  Create a new set of CRUD functions for Personal Training: `add_pt_membership`, `get_all_pt_memberships`, and `delete_pt_membership`.
    4.  Update `generate_financial_report_data`. Its logic must now query **both** the `group_class_memberships` table and the `pt_memberships` table.
    5.  Confirm that `generate_renewal_report_data` **only** queries the `group_class_memberships` table.

---
**Phase 3: API Layer Update**
* **Task:** `[PENDING]` Update `reporter/app_api.py` to expose the new backend logic.
* **Instructions:**
    1.  Reflect all function name changes from the `DatabaseManager` (e.g., `create_membership` -> `create_group_class_membership`).
    2.  Add new pass-through functions for the PT logic (`create_pt_membership`, `get_all_pt_memberships`, etc.) that call the corresponding methods in the `DatabaseManager`.

---
**Phase 4: UI Implementation**
* **Task:** `[PENDING]` Overhaul `reporter/streamlit_ui/app.py` to match the new functional design.
* **Instructions:**
    1.  **`Members` Tab:** Ensure this tab only contains Member CRUD functionality.
    2.  **`Memberships` Tab:** This tab will now handle both membership types.
        * Add a `st.radio` selector at the top for "Group Class Memberships" and "Personal Training Memberships".
        * Use an `if/else` block based on the selector.
        * **If "Group Class Memberships" is selected:** Render the UI for creating and viewing records from the `group_class_memberships` table. Call the appropriate `...group_class...` functions from the API.
        * **If "Personal Training Memberships" is selected:** Render the UI for creating and viewing records from the `pt_memberships` table. Call the appropriate `...pt_membership...` functions from the API.

---
**Phase 5: Testing and Final Migration**
* **Task:** `[PENDING]` Update the test suite and create the final data migration script.
* **Instructions:**
    1.  **Update Tests:** Go through all files in `reporter/tests/` and update them to reflect the new table names (`group_class_memberships`, `pt_memberships`) and all associated function names.
    2.  **Create PT Tests:** Add a new test file, `test_pt_memberships.py`, to test the CRUD operations for the `pt_memberships` table.
    3.  **Create Migration Script:** Create the `reporter/migrate_historical_data.py` script. This script will perform the one-time data import from the old CSV files into the new `members`, `group_plans`, `group_class_memberships`, and `pt_memberships` tables.
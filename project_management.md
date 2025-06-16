**Phase 2: Database Schema Migration**
* **Task:** [DONE] Modify `reporter/database.py` to reflect the new data model.
    * **Instructions:**
        1.  In the `create_tables` function, modify the SQL `CREATE TABLE` statement for the `plans` table.
            * **Remove** the `price` and `type` columns.
            * **Add** `duration_days` (INTEGER), `default_amount` (REAL), and `display_name` (TEXT, UNIQUE).
        2.  Verify the `members` table schema matches the spec, ensuring the `phone` column has a `UNIQUE` constraint.
        3.  The `memberships` table schema remains unchanged. Do not modify it.

---
**Phase 3: Backend Business Logic**
* **Task:** Refactor the business logic in `reporter/database_manager.py`.
    * **Instructions:**
        1.  **Cleanup:** Delete or comment out any existing high-level functions related to the old membership creation process.
        2.  **Implement Member CRUD:**
            * Create functions: `add_member`, `update_member`, `get_all_members`, `delete_member`.
            * The `add_member` function must validate that the member's phone number does not already exist.
        3.  **Implement Plan CRUD:**
            * Create functions: `add_plan`, `update_plan`, `get_all_plans`, `delete_plan`.
            * The `add_plan` function must automatically generate the `display_name` by combining plan name and duration, then validate its uniqueness before committing.
        4.  **Implement Membership Creation:**
            * Create a `create_membership` function that accepts `member_id`, `plan_id`, `start_date`, etc., and correctly calculates the `end_date` before saving a new record to the `memberships` table.

---
**Phase 4: User Interface Implementation**
* **Task:** Overhaul the Streamlit front-end in `reporter/streamlit_ui/app.py`.
    * **Instructions:**
        1.  **Cleanup:** Remove all UI code related to the old two-panel layout for creating memberships.
        2.  **Restructure:** The main UI should now have four primary tabs: `Members`, `Plans`, `Memberships`, `Reporting`.
        3.  **Build `Members` Tab:** Implement the two-panel UI from the whiteboard sketch for full Member CRUD.
        4.  **Build `Plans` Tab:** Implement the two-panel UI for full Plan CRUD.
        5.  **Update `Memberships` Tab:**
            * In the `Members` tab, add a **"Create Membership"** button that appears when a member is selected.
            * This button will trigger a form to select a plan and create a new transaction in the `memberships` table.
            * The `Memberships` tab itself will now primarily be for viewing the complete history of all membership transactions.
        6.  **Verify `Reporting` Tab:** The code for this tab should remain. Ensure it still functions correctly.

---
**Phase 5: Testing and Validation**
* **Task:** Update the test suite in `reporter/tests/` to reflect all backend changes.
    * **Instructions:**
        1.  **Cleanup:** Delete obsolete test files. `test_business_logic.py` is likely outdated and should be removed.
        2.  **Update `test_database.py`:** Ensure tests pass with the new table schemas.
        3.  **Create `test_member_management.py`:** Write unit tests for the new Member CRUD functions.
        4.  **Create `test_plan_management.py`:** Write unit tests for the new Plan CRUD functions, including the `display_name` uniqueness check.
        5.  Review and update any data migration tests in `test_migrate_data.py` to align with the new structure.

---
**Phase 6: Final Cleanup**
* **Task:** Remove all obsolete files from the repository.
    * **Instructions:**
        1.  Delete any old `.csv` or `.xlsx` data files that were used for the previous version's data migration (e.g., `Kranos MMA Members.xlsx - GC.csv`).
        2.  Review all scripts and utilities to ensure no code is left that references the old data structures.

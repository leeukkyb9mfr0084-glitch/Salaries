Here is the project management task list. It includes previously completed work and the new pending tasks for implementing full CRUD functionality across the app.

---

### **Task 1: Fix `display_name` in `group_plans` for Migrated Data - DONE**

* **Objective:** Ensure the `display_name` is correctly populated by the migration script.
* **File to Modify:** `reporter/database_manager.py`
* **Instructions:** Completed as per original task. Logic to generate and save `display_name` was added to `find_or_create_group_plan`.

---

### **Task 2: Make `is_active` Status for Group Memberships a Runtime Calculation - DONE**

* **Objective:** Remove the stored `is_active` column and calculate it dynamically.
* **Files Modified:** `reporter/database.py`, `reporter/database_manager.py`, `reporter/app_api.py`, `reporter/migrate_historical_data.py`
* **Instructions:** Completed. The `is_active` column was removed from the schema and all related create/update logic. The `get_all_group_class_memberships_for_view` function now calculates `status` at runtime.

---

### **Task 3: Refine `join_date` Logic for New Members - DONE**

* **Objective:** Set a member's `join_date` to their first-ever membership start date during migration.
* **Files Modified:** `reporter/database_manager.py`, `reporter/migrate_historical_data.py`
* **Instructions:** Completed. The `add_member` function was updated to accept an optional `join_date`.

---

### **Task 4: Simplify `pt_memberships` Table - DONE**

* **Objective:** Remove unused columns from the `pt_memberships` table and associated logic.
* **Files Modified:** `reporter/database.py`, `reporter/database_manager.py`, `reporter/app_api.py`, `reporter/streamlit_ui/app.py`, `reporter/migrate_historical_data.py`
* **Instructions:** Completed. The `sessions_remaining` and `notes` columns were removed from the `pt_memberships` table and all related backend/UI code.

---

### **Task 5: Refactor Group Class Membership Editing - PENDING**

* **Objective:** Implement a full CRUD interface for Group Class Memberships, replacing the current separate Create and Delete forms with a unified system.

* **Phase 5.1: Refactor Backend Update Logic**
    * **File to Modify:** `reporter/database_manager.py`
    * **Instructions:**
        1.  Locate the `update_group_class_membership_record` function.
        2.  Modify its signature. Remove the `plan_duration_days` and `is_active` parameters. The function should only accept `membership_id` and the fields that can be changed: `member_id`, `plan_id`, `start_date`, `amount_paid`.
        3.  Inside the function, fetch the `duration_days` from the `group_plans` table using the provided `plan_id` to calculate the `end_date`.
        4.  Remove all logic related to the old `is_active` parameter.
    * **File to Modify:** `reporter/app_api.py`
    * **Instructions:**
        1.  Find the `update_group_class_membership_record` function.
        2.  Update its signature to match the changes made in the `DatabaseManager`. Remove the `plan_duration_days` parameter.

* **Phase 5.2: Implement UI for Editing**
    * **File to Modify:** `reporter/streamlit_ui/app.py`
    * **Instructions:**
        1.  In `render_memberships_tab`, under the `if membership_mode == 'Group Class Memberships':` block, remove the existing UI for displaying and deleting memberships (the `st.dataframe` and the `st.selectbox` for deletion).
        2.  Implement the standard two-column CRUD layout (similar to the Members tab).
        3.  **Left Column:** Use `st.selectbox` to list all existing group class memberships for selection, including an "Add New" option.
        4.  **Right Column:** Use a single form (`st.form`) for both adding and editing.
        5.  When a membership is selected from the left, populate the form on the right with its data. When "Add New" is selected, the form should be blank.
        6.  The form's "Save" button should call `api.create_group_class_membership` for new records or the updated `api.update_group_class_membership_record` for existing ones.

---

### **Task 6: Implement Full CRUD for Personal Training Memberships - PENDING**

* **Objective:** Add `Update` functionality to Personal Training (PT) memberships and refactor the UI to be consistent with other tabs.

* **Phase 6.1: Add Backend Update Logic**
    * **File to Modify:** `reporter/database_manager.py`
    * **Instructions:**
        1.  Create a new function: `update_pt_membership`.
        2.  It should accept `membership_id` and optional parameters for fields that can be changed: `purchase_date`, `amount_paid`, `sessions_purchased`.
        3.  Implement the `UPDATE` SQL query to save the changes.
    * **File to Modify:** `reporter/app_api.py`
    * **Instructions:**
        1.  Create a new function: `update_pt_membership` that calls the corresponding new function in the `DatabaseManager`.

* **Phase 6.2: Implement UI for Editing**
    * **File to Modify:** `reporter/streamlit_ui/app.py`
    * **Instructions:**
        1.  In `render_memberships_tab`, find the `elif membership_mode == 'Personal Training Memberships':` block.
        2.  Remove the current UI for displaying the dataframe and the separate delete selectbox.
        3.  Replicate the standard two-column CRUD layout here.
        4.  The form's "Save" button should call `api.create_pt_membership` for new records and the new `api.update_pt_membership` for existing records.
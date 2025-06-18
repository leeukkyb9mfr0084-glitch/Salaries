Understood. Here is a phase-wise task list to resolve the identified codebase issues. These instructions are for a junior full-stack engineer.

-----

### **Phase 1: Solidify the Foundation (Database & Models)**

**Objective:** Align the database schema and the Data Transfer Objects (DTOs). This is the most critical phase.

| Task ID | File | Instructions |
| :--- | :--- | :--- |
| **1.1** | `reporter/database.py` | **Update the `pt_memberships` table.** Add the `notes` and `sessions_remaining` columns. The `sessions_purchased` column should be renamed to `sessions_total` for clarity. \<br\> **Action:** Modify the `CREATE TABLE pt_memberships` SQL statement. |
| **1.2** | `reporter/models.py` | **Synchronize `PTMembershipView` DTO.** Update the fields to match the `pt_memberships` and `members` tables. It should contain fields populated by a JOIN query. \<br\> **Action:** Replace the existing `PTMembershipView` with: `python @dataclass class PTMembershipView: membership_id: int member_id: int member_name: str purchase_date: str sessions_total: int sessions_remaining: int notes: str` |
| **1.3** | `reporter/models.py` | **Fix `MemberView` DTO.** The `status`, `membership_type`, and `payment_status` fields do not exist in the database and are too complex to calculate in a simple view. Remove them for now. \<br\> **Action:** Simplify the `MemberView` DTO to only include fields that are directly in the `members` table. |
| **1.4** | `reporter/models.py` | **Clean up `GroupClassMembershipView` DTO.** The `member_display_name` and `plan_display_name` fields are redundant. \<br\> **Action:** Remove these two fields. Use the existing `member_name` and `plan_name` fields in the UI. |

-----

### **Phase 2: Align Backend Logic (Data Access Layer)**

**Objective:** Update the `DatabaseManager` to work with the corrected schema and DTOs.

| Task ID | File | Instructions |
| :--- | :--- | :--- |
| **2.1** | `reporter/database_manager.py` | **Fix `get_all_pt_memberships_for_view`.** The SQL query is broken. It must be rewritten to `JOIN` the `members` and `pt_memberships` tables to get the data required for the updated `PTMembershipView` DTO. \<br\> **Action:** Rewrite the SQL query inside the function. Ensure you select `pt.id as membership_id`, `m.name as member_name`, etc., and correctly instantiate and return a `List[PTMembershipView]`. |
| **2.2** | `reporter/database_manager.py` | **Fix `get_all_members_for_view`.** The SQL query tries to select columns that do not exist. \<br\> **Action:** Simplify the `SELECT` statement to only pull columns that are present in the `members` table, matching the simplified `MemberView` DTO from Task 1.3. |
| **2.3** | `reporter/database_manager.py` | **Fix `get_all_group_class_memberships_for_view`.** The query is missing the `amount_paid` column, which the UI needs for editing. \<br\> **Action:** Add `gcm.amount_paid` to the `SELECT` statement and add the corresponding `amount_paid: float` field to the `GroupClassMembershipView` DTO in `models.py`. |
| **2.4** | `reporter/database_manager.py` | **Update `create_pt_membership`.** The function needs to handle the new `notes` field. \<br\> **Action:** Add a `notes: str` parameter to the function signature and include it in the `INSERT` statement. |

-----

### **Phase 3: Synchronize the API Layer**

**Objective:** Ensure the API layer correctly passes data to and from the updated `DatabaseManager`.

| Task ID | File | Instructions |
| :--- | :--- | :--- |
| **3.1** | `reporter/app_api.py` | **Update `create_pt_membership` signature.** The API function needs to match the new `database_manager` function. \<br\> **Action:** Add the `notes: str` parameter to the function signature and pass it to `self.db_manager.create_pt_membership`. |
| **3.2** | `reporter/app_api.py` | **No other changes needed.** This layer is a simple pass-through. Verify that all other function signatures still match their counterparts in `database_manager.py`. |

-----

### **Phase 4: Fix the User Interface**

**Objective:** Make the Streamlit UI consume the corrected DTOs and call the updated API functions.

| Task ID | File | Instructions |
| :--- | :--- | :--- |
| **4.1** | `reporter/streamlit_ui/app.py` | **Fix PT Memberships Display.** The PT tab will be broken. Update the code that displays the PT memberships DataFrame to use the correct attribute names from the new `PTMembershipView` DTO (`membership_id`, `member_name`, `sessions_total`, `sessions_remaining`). \<br\> **Action:** Modify the `render_memberships_tab` function where it iterates through `pt_memberships`. |
| **4.2** | `reporter/streamlit_ui/app.py` | **Fix Members Tab Display.** This tab will be broken. Update the DataFrame display to use the attributes from the simplified `MemberView` DTO. \<br\> **Action:** Modify the `render_members_tab` function. |
| **4.3** | `reporter/streamlit_ui/app.py` | **Fix Membership Edit Form.** The form fails when trying to access `amount_paid`. Since you added this field back into the DTO in Task 2.3, this should now work. \<br\> **Action:** Verify that `selected_data.amount_paid` is now a valid attribute and the edit form loads correctly. |
| **4.4** | `reporter/streamlit_ui/app.py` | **Update PT Membership Creation.** The form for creating a new PT membership needs a field for `notes`. \<br\> **Action:** In `render_memberships_tab`, add an `st.text_area("Notes")` to the PT creation form and pass its value to the `api.create_pt_membership` function call. |

-----

### **Phase 5: Cleanup and Verification**

**Objective:** Bring the migration script and test suite in line with the fixed application code.

| Task ID | File | Instructions |
| :--- | :--- | :--- |
| **5.1** | `reporter/migrate_historical_data.py` | **Update PT Data Migration.** The script needs to handle the new `pt_memberships` schema. \<br\> **Action:** In the `migrate_pt_data` function, modify the `INSERT` statement to use the `sessions_total` column (renamed from `sessions_purchased`). Set default values for `sessions_remaining` (e.g., same as `sessions_total`) and `notes` (e.g., an empty string `''`). |
| **5.2** | `reporter/tests/test_database_manager.py` | **Fix Failing Tests.** Many tests will be failing due to schema and DTO changes. \<br\> **Action:** Go through the test file. Update `INSERT` statements in test setups to match the new schema. Update assertions to check for the correct data structures and DTOs. Remove tests for obsolete logic or columns. |
| **5.3** | `reporter/tests/test_pt_memberships.py` | **Fix Failing PT Tests.** This test file is heavily affected. \<br\> **Action:** Rewrite the tests to align with the new `pt_memberships` schema and the `PTMembershipView` DTO. Ensure you are testing the `notes` and `sessions_remaining` functionality. |


**Objective:** To complete the application by first resolving critical structural issues and then implementing the refined specifications for the backend and user interface.

-----

### **Phase 1: Foundational Cleanup & Critical Fixes (Must be completed first)**

**Goal:** Stabilize the codebase. A clean foundation prevents future bugs and makes development faster. Do not skip these steps.

| Task ID | Task Description | Instructions for Junior Developer | Status |
| :--- | :--- | :--- | :--- |
| **P1-T1** | Consolidate Project Structure | **Why:** We have two code folders (`reporter`, `reporter`). This is confusing and will lead to errors. We need one source of truth. \<br\> **How:** \<br\> 1. In your file explorer, delete the entire `reporter` folder. \<br\> 2. In your code editor, do a project-wide search for "reporter" to find any leftover imports. Change them all to import from `reporter`. | `[ ]` |
| **P1-T2** | Clean Up Root Directory | **Why:** The main project folder is cluttered with dozens of old, single-purpose scripts. They are not part of the final application and create confusion. \<br\> **How:** Delete all the standalone Python scripts from the root directory (e.g., `add_and_verify_member.py`, `manage_plan_lifecycle.py`, all the `simulate_...` files). Their logic will be properly implemented in the main application. | `[ ]` |
| **P1-T3** | Fix Missing Dependency | **Why:** The application will crash when a user tries to download an Excel report because a required library is missing. \<br\> **How:** \<br\> 1. Open the `requirements.txt` file. \<br\> 2. On a new line, add the word `openpyxl`. | `[ ]` |

-----

### **Phase 2: Backend & Database Overhaul**

**Goal:** Rebuild the backend to perfectly support the logic from our wireframe and specs.

| Task ID | Task Description | Instructions for Junior Developer | Status |
| :--- | :--- | :--- | :--- |
| **P2-T1** | Implement New Database Schema | **Why:** Our current database tables cannot support the features we need, like tracking memberships or renewal types. \<br\> **How:** Open `reporter/database.py` and modify the `CREATE TABLE` statements: \<br\> 1. **`memberships` table:** This is new. It needs columns for `id`, `member_id`, `plan_id`, `start_date`, `end_date`, and `is_active`. \<br\> 2. **`transactions` table:** Add a `transaction_type TEXT` column. This will store 'New' or 'Renewal'. \<br\> 3. **`plans` table:** Add an `is_active BOOLEAN` column. | `[ ]` |
| **P2-T2** | Build Membership Creation Logic | **Why:** We need a single, smart function to handle the creation of a new membership, as per the wireframe's `SAVE` button logic. \<br\> **How:** In `reporter/app_api.py`, create a new function `create_membership(...)`. This function will take all the form data (member\_id, plan\_id, duration, amount, start\_date). Inside this function: \<br\> 1. Check if the member has any existing memberships to determine if the `transaction_type` is 'New' or 'Renewal'. \<br\> 2. Calculate the `end_date` using the `start_date` and `plan_duration`. \<br\> 3. Perform two database inserts: one into the `memberships` table and one into the `transactions` table. | `[ ]` |
| **P2-T3** | Build Membership Viewing Logic | **Why:** The UI needs an efficient way to get all the data for the membership list on the right side of the wireframe. \<br\> **How:** In `reporter/app_api.py`, create a function `get_all_memberships_for_view(...)`. This function should perform a database `JOIN` across the `members`, `memberships`, and `plans` tables to return all the columns needed for the display table in one go. | `[ ]` |

-----

### **Phase 3: UI Implementation from Wireframe**

**Goal:** Build the `Memberships` tab exactly as designed.

| Task ID | Task Description | Instructions for Junior Developer | Status |
| :--- | :--- | :--- | :--- |
| **P3-T1** | Build the Two-Panel Layout | **Why:** We need the visual structure in place before adding functionality. \<br\> **How:** In `reporter/streamlit_ui/app.py`, use `st.columns(2)` to create the left and right panels. Build the form widgets on the left and the filter/table placeholders on the right. | `[ ]` |
| **P3-T2** | Implement the "Create Membership" Form | **Why:** To enable the primary data entry workflow. \<br\> **How:** \<br\> 1. In the left panel, populate the 'Member Name' and 'Plan Name' dropdowns by calling the appropriate API functions. \<br\> 2. Connect the `SAVE` button to call the `api.create_membership` function you built in Phase 2, passing it the data from all the form fields. \<br\> 3. Connect the `CLEAR` button to reset all the form fields. | `[ ]` |
| **P3-T3** | Implement the "View/Manage" Panel | **Why:** To allow users to see, filter, and manage existing memberships. \<br\> **How:** \<br\> 1. In the right panel, implement the filters (`Name`, `Phone`, `Status`). When they change, re-call the `api.get_all_memberships_for_view` function with the filter values. \<br\> 2. Display the returned data in an `st.dataframe`. \<br\> 3. **For selection:** Add an `st.selectbox` above the table, listing the displayed memberships. When a user selects one, display its details and the `EDIT` and `DELETE` buttons below the table. \<br\> 4. Wire up the `EDIT` and `DELETE` buttons to perform their respective actions on the *selected* membership. | `[ ]` |
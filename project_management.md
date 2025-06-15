Kranos Reporter v2.0 - Project Plan
Version

Date

1.1

June 15, 2025

This document outlines the tasks required to refactor the Kranos Reporter application to version 2.0. Please check off tasks as they are completed. Developer Note: As you complete each task, ensure you also remove any old, commented-out code and unnecessary comments related to the V1 implementation.

Phase 1: Initial Bug Fixes & Code Cleanup
Goal: Stabilize the current application before starting major refactoring.

[x] Fix Data Migration Crash: Modify get_or_create_plan_id in database_manager.py to first check if a plan with the same name and duration exists before inserting a new one. This will resolve the UNIQUE constraint failed error.

[x] Fix UI Startup Crash: In reporter/streamlit_ui/app.py, update the plan_display_list list comprehension to correctly unpack the 5 columns now returned by the plan query, resolving the ValueError.

[ ] Clean Up Dead Code:

[x] Delete the set_plan_active_status method from database_manager.py.

[x] Delete the get_all_plans_with_inactive method from database_manager.py.

[x] Delete the corresponding API endpoints for the above methods in app_api.py.

[ ] Fix "Add Plan" Feature:

[x] Add price and type input fields to the "Add New Plan" form in streamlit_ui/app.py.

[x] Update the api.add_plan call to pass the new values.

[x] Update the add_plan method signatures in app_api.py and database_manager.py to accept the new fields.

Phase 2: Backend & Data Model Refactoring
Goal: Align the backend with the simplified v2.0 data model.

[ ] Update Database Schema:

[x] In database.py, delete the CREATE TABLE pt_records statement.

[x] In database.py, add the is_active (BOOLEAN) column to the plans table definition.

[ ] Remove Obsolete PT Logic:

[x] In database_manager.py, delete all methods related to the pt_records table (e.g., add_pt_transaction). Ensure all associated comments are also removed.

[x] In app_api.py, delete the API endpoints that called the obsolete PT methods.

[ ] Update Data Migration Script:

[x] In migrate_data.py, modify process_pt_data to treat PT sessions as standard transactions.

[x] Ensure process_pt_data now calls get_or_create_plan_id and then add_transaction.

[x] Remove any old logic or comments related to processing PT data into a separate table.

Phase 3: UI Overhaul - Global Structure
Goal: Rebuild the Streamlit UI with the new tabbed navigation.

[x] Implement Tabbed Layout: In streamlit_ui/app.py, delete all old UI code and replace it with st.tabs(["Memberships", "Members", "Plans", "Reporting"]).

[x] Create Tab Functions: For better organization, create separate functions to render the content of each tab (e.g., render_memberships_tab(), etc.) and call them within their respective tabs.

Phase 4: UI Build - "Members" Tab
Goal: Implement the full functionality of the "Members" tab.

[x] Implement Layout: Create the two-column layout.

[x] Build Left Form: Create the "Add/Edit Member" form with "Save" and "Clear" buttons.

[x] Build Right Table & Filters:

[x] Add all specified filter widgets above the table.

[x] Create a new backend function get_filtered_members(...) that uses the filter values to query the database.

[x] Call the new backend function and display the results in a dataframe.

[ ] Implement Row Actions:

[x] Add "History," "Edit," and "Delete" buttons to each row of the members table.

[x] Wire the "Edit" button to populate the left form with the selected member's data.

[ ] Wire the "Delete" button to the corresponding API function.

[ ] Implement "History" Modal:

[ ] On "History" button click, open a modal window.

[ ] Inside the modal, display the selected member's transaction history with a total amount paid.

Phase 5: UI Build - Remaining Tabs
Goal: Implement the "Memberships," "Plans," and "Reporting" tabs.

[ ] "Memberships" Tab:

[ ] Implement the two-column layout.

[ ] Build the "Add Membership" form on the left.

[ ] Build the recent transactions list with filters on the right.

[ ] Add the "Close Books for Month" section at the bottom.

[ ] "Plans" Tab:

[ ] Implement the two-column layout.

[ ] Build the "Add/Edit Plan" form on the left.

[ ] Build the plans list on the right, including the "Active" checkbox and "Edit"/"Delete" buttons.

[ ] "Reporting" Tab:

[ ] Implement the two vertical sections.

[ ] Build the "Monthly Report" section with a table of transactions.

[ ] Build the "Upcoming Renewals" section with its corresponding table.

Phase 6: Final Validation
Goal: Ensure the entire application works as expected.

[ ] Full Data Migration Test: Delete the reporter.db file and run the migrate_data.py script from scratch. Verify that all GC and PT data is correctly imported into the transactions table.

[ ] CRUD Testing - Members: Test adding, editing, searching, filtering, and deleting members.

[ ] CRUD Testing - Plans: Test adding, editing, and deleting plans. Verify that the "Active" checkbox works correctly.

[ ] CRUD Testing - Memberships: Test adding, editing, and deleting membership transactions.

[ ] Functionality Testing:

[ ] Verify the "History" modal works correctly.

[ ] Verify the "Close Books" functionality works as expected.

[ ] Verify both reports on the "Reporting" tab generate correct data.

[ ] Final Code Review: Perform a final pass on the entire codebase. Look for any remaining dead code, unnecessary comments, or areas where code clarity can be improved. Ensure the code is clean and easy to maintain.
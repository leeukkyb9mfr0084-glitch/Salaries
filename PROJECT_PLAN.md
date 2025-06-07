# Kranos MMA Reporter - Project Plan

## Phase 1: Foundation & Setup

- [ ] **Task 1.1: Create the Database Schema Script.**
    - Create the `database.py` script.
    - The script must define a function `create_database()` that creates all four tables as per the schema in the project brief.
    - It must include a `seed_initial_plans()` function to populate the `plans` table with default data.
    - **Testing:** Create a `tests/test_database.py` file. Write a test that calls `create_database()` using an in-memory SQLite database and verifies that all four tables are created successfully.

## Phase 2: Core UI & Member Management

- [ ] **Task 2.1: Build the Main Application Window and Tabs.**
    - Create the `main.py` and `gui.py` scripts.
    - The window should have the title "Kranos MMA Reporter" and a default size.
    - Implement a `CTkTabview` with two tabs: "Membership Management" and "Reporting".
    - (No backend logic to test in this step).

- [ ] **Task 2.2: Implement Full "Add Member" Feature.**
    - Create the `database_manager.py` file.
    - In `database_manager.py`, create functions: `add_member_to_db(name, phone)` and `get_all_members()`.
    - In `gui.py`, build the UI form for adding a new member and a `CTkScrollableFrame` to display all members.
    - The "Save Member" button must save data via `database_manager` and the UI list must refresh instantly.
    - **Testing:** Create `tests/test_database_manager.py`. Write unit tests for `add_member_to_db` and `get_all_members`. Tests must use a temporary test database. Test cases should include: successful addition, attempting to add a member with a duplicate phone number (expecting an error), and verifying that `get_all_members` returns the correct data.

- [ ] **Task 2.3: Implement Full "Add Group Membership" Feature.**
    - In `database_manager.py`, add functions: `get_all_plans()` and `add_group_membership_to_db(...)`.
    - In `gui.py`, create the UI form for adding a group membership with dropdowns for members and plans.
    - The "Save Membership" button should calculate the `end_date` and save the record. The dropdowns should be populated from the database.
    - **Testing:** In `tests/test_database_manager.py`, add unit tests for `get_all_plans` and `add_group_membership_to_db`. The tests should ensure that a membership record is linked correctly to a member and a plan.

## Phase 3: Data Display & Reporting

- [ ] **Task 3.1: Display Membership History.**
    - In `database_manager.py`, create a function `get_memberships_for_member(member_id)`.
    - In `gui.py`, add a new frame that displays the membership history for the currently selected member in the "All Members" list.
    - **Testing:** In `tests/test_database_manager.py`, add unit tests for `get_memberships_for_member`. Create mock data with multiple memberships for a single member and verify the function returns only their records.

- [ ] **Task 3.2: Implement the "Pending Renewals" Report.**
    - In the "Reporting" tab, add a button "Generate Pending Renewals".
    - In `database_manager.py`, create a function `get_pending_renewals(target_date)` that finds all memberships ending in the month of the `target_date`.
    - The UI button should call this function for the current month and display the results.
    - **Testing:** Add unit tests for `get_pending_renewals`. The test should create mock data with memberships ending in different months and verify that the function returns only the correct ones for a given month.

- [ ] **Task 3.3: Implement the "Monthly Finance" Report.**
    - In the "Reporting" tab, add a button "Generate Last Month's Finance Report".
    - In `database_manager.py`, create a function `get_finance_report(year, month)` that sums the `amount_paid` from all transactions within that month.
    - The UI button should call this function for the previous month and display the summary.
    - **Testing:** Add unit tests for `get_finance_report`. Create mock data with payments in different months and verify the function returns the correct total for a specified month.

## Phase 4: Finalization

- [ ] **Task 4.1: Code Cleanup and Final Polish.**
    - Review all code for clarity, add comments where necessary.
    - Ensure all forms have robust error handling for incorrect user input.
    - **Testing:** Ensure all tests pass cleanly by running `pytest` on the entire `tests/` directory.

- [ ] **Task 4.2: Create `requirements.txt`.**
    - Generate a `requirements.txt` file listing all necessary Python packages (e.g., `customtkinter`, `pandas`, `pytest`).
# Project Recovery and Bug Fix Plan
**Date:** June 16, 2025
**Objective:** To address critical bugs, restore lost functionality, and clean up the codebase. Each task is designed to be a small, focused effort.

**Instructions for the Developer:**
1.  Complete each task in the order it is listed.
2.  Do not move to the next task until the current one is fully verified using the provided scripts.
3.  After completing each task, update the "Project Status Log" section at the bottom of this document.

---

### **Phase 1: Critical Bug Fixes & Code Cleanup**
This phase addresses the showstopper bugs that prevent the application from running correctly and cleans up obsolete files.

- [FAILED] **Task 1.1: Fix Database Variable Mismatch in Migration Script**
* **File to Modify:** `reporter/migrate_historical_data.py`
* **Instructions:**
    1.  Open `reporter/migrate_historical_data.py`.
    2.  Locate the line: `from reporter.database import DB_PATH, create_connection` and change `DB_PATH` to `DB_FILE`.
    3.  Locate the line: `conn = create_connection(DB_PATH)` and change `DB_PATH` to `DB_FILE`.
* **Verification:**
    * In the project's root directory, run the command: `python -c "from reporter.migrate_historical_data import migrate_historical_data; print('SUCCESS: Import OK')"`
    * The terminal must print "SUCCESS: Import OK" without any errors.

- [FAILED] **Task 1.2: Fix Incorrect Function Call in Main Application**
* **File to Modify:** `reporter/main.py`
* **Instructions:**
    1.  Open `reporter/main.py`.
    2.  At the top of the file, add the import: `from reporter.migrate_historical_data import migrate_historical_data`
    3.  Inside the `handle_database_migration` function, change the line `migrate_data()` to `migrate_historical_data()`.
* **Verification Script:**
    1.  Create a new file in the project root named `verify_task_1_2.py`.
    2.  Copy the following code into it:
        ```python
        import os
        from reporter.main import handle_database_migration
        from reporter.database import DB_FILE

        print("Running verification for Task 1.2...")
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        
        handle_database_migration()

        if os.path.exists(DB_FILE):
            print(f"SUCCESS: Database file '{DB_FILE}' was created by the handler.")
            os.remove(DB_FILE)
        else:
            print(f"FAILURE: Database file '{DB_FILE}' was not created.")
        ```
    3.  Run the script from your terminal: `python verify_task_1_2.py`.
    4.  It must print a SUCCESS message.

- [DONE] **Task 1.3: Clean Up Unused and Obsolete Files**
* **Files to Rename:**
* **Instructions:**
    1.  Rename `run_all_tests.sh` to `run_all_tests.sh-todelete`.
    2.  Rename `run_validation.sh` to `run_validation.sh-todelete`.
    3.  Rename `validate_fixes.sh` to `validate_fixes.sh-todelete`.
    4.  In `scripts/`, rename `process_data.py` to `process_data.py-todelete`.
    5.  In `tests/`, rename `test_process_data.py` to `test_process_data.py-todelete`.
* **Verification:**
    * Confirm that all specified files have been renamed with the `-todelete` suffix in your file explorer.

- [DONE] **Task 1.4: Clean Up Project Dependencies**
* **File to Modify:** `requirements.txt`
* **Instructions:**
    1.  Open `requirements.txt` and delete the line containing `flet`.
* **Verification:**
    * Open `requirements.txt` and confirm the line with `flet` is gone.

---

### **Phase 2: Logic and Functional Fixes**
This phase restores lost functionality and improves backend logic.

**Task 2.1: Restore "Renewal" Logic for Group Class Memberships**
* **File to Modify:** `reporter/database_manager.py`
* **Instructions:**
    1.  Open `reporter/database_manager.py` and find the `create_group_class_membership` function.
    2.  Delete the line: `membership_type = "New"`.
    3.  In its place, add the following logic to check for existing memberships before setting the `membership_type`:
        ```python
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM group_class_memberships WHERE member_id = ?", (member_id,))
        membership_type = "Renewal" if cursor.fetchone() else "New"
        ```
* **Verification Script:**
    1.  Create a new file in the project root named `verify_task_2_1.py`.
    2.  Copy the following code into it:
        ```python
        import os
        import sqlite3
        from reporter.database_manager import DatabaseManager

        DB_FILE = "test_renewal.db"
        print("Running verification for Task 2.1...")
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        
        db_manager = DatabaseManager(db_file=DB_FILE)
        member_id, _, _ = db_manager.add_member("Test Member", "555-0101", "test@test.com", "Active")
        plan_id, _, _ = db_manager.add_group_plan("Test Plan", 100, 30)

        db_manager.create_group_class_membership(member_id, plan_id, "2025-06-16")
        db_manager.create_group_class_membership(member_id, plan_id, "2025-07-16")

        conn = sqlite3.connect(DB_FILE)
        results = [row[0] for row in conn.cursor().execute("SELECT membership_type FROM group_class_memberships ORDER BY start_date")]
        conn.close()

        if results == ["New", "Renewal"]:
            print("SUCCESS: Membership types are correctly assigned as 'New' then 'Renewal'.")
        else:
            print(f"FAILURE: Expected ['New', 'Renewal'], but got {results}.")
        
        os.remove(DB_FILE)
        ```
    3.  Run the script from your terminal: `python verify_task_2_1.py`.
    4.  It must print a SUCCESS message.

**Task 2.2: Add User-Friendly Error for Duplicate Phone Numbers**
* **File to Modify:** `reporter/streamlit_ui/app.py`
* **Instructions:**
    1.  Open `reporter/streamlit_ui/app.py` and find the `render_members_tab` function.
    2.  Wrap the API calls in the "Add Member" and "Update Member" sections in `try...except ValueError` blocks. This allows the UI to catch the specific error from the backend.
        * **For "Add Member":**
            ```python
            try:
                success, message = self.api.add_member(name, phone, email, "Active")
                if success:
                    st.success(message)
                    st.experimental_rerun()
                else:
                    st.error(message)
            except ValueError as e:
                st.error(f"Error: {e}")
            ```
        * **For "Update Member":**
            ```python
            try:
                success, message = self.api.update_member(member_id, name, phone, email, status)
                if success:
                    st.success(message)
                    st.session_state.edit_member_id = None
                    st.experimental_rerun()
                else:
                    st.error(message)
            except ValueError as e:
                st.error(f"Error: {e}")
            ```
* **Verification Script:**
    * This task modifies the UI's error handling. The following script verifies that the backend correctly raises the error that the UI code is now designed to catch.
    1.  Create a file named `verify_task_2_2.py`.
    2.  Copy the following code into it:
        ```python
        import os
        from reporter.database_manager import DatabaseManager

        DB_FILE = "test_duplicate.db"
        print("Running verification for Task 2.2...")
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        db_manager = DatabaseManager(db_file=DB_FILE)

        db_manager.add_member("First Member", "555-1234", "first@test.com", "Active")
        
        try:
            db_manager.add_member("Second Member", "555-1234", "second@test.com", "Active")
            print("FAILURE: ValueError was NOT raised for a duplicate phone number.")
        except ValueError:
            print("SUCCESS: ValueError was correctly raised for a duplicate phone number.")
        
        os.remove(DB_FILE)
        ```
    3.  Run the script: `python verify_task_2_2.py`.
    4.  It must print a SUCCESS message.

---

### **Phase 3: Final Verification**

**Task 3.1: Update the Project Management File**
* **File to Modify:** `project_management.md`
* **Instructions:**
    1.  Open `project_management.md`, delete all its content.
    2.  Copy and paste the "Project Status Log" from below into it.
* **Verification:**
    * Open `project_management.md` and confirm its content matches the log.

---
<br>

## Project Status Log
*(Copy this section into `project_management.md` after all tasks are done)*

### Project Recovery Plan - June 2025

**Phase 1: Critical Bug Fixes & Code Cleanup**
- [DONE] Task 1.1: Fix Database Variable Mismatch in Migration Script
- [DONE] Task 1.2: Fix Incorrect Function Call in Main Application
- [DONE] Task 1.3: Clean Up Unused and Obsolete Files
- [DONE] Task 1.4: Clean Up Project Dependencies

**Phase 2: Logic and Functional Fixes**
- [DONE] Task 2.1: Restore "Renewal" Logic for Group Class Memberships
- [DONE] Task 2.2: Add User-Friendly Error for Duplicate Phone Numbers

**Phase 3: Final Verification**
- [DONE] Task 3.1: Update the Project Management File

**Conclusion:** All critical bugs and regressions have been addressed. The application is now in a stable state.

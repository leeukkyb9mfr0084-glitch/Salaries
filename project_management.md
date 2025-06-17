

#### **Task 1: Fix `display_name` in `group_plans` for Migrated Data - DONE**

* **Objective:** Ensure the `display_name` is correctly populated by the migration script.
* **File to Modify:** `reporter/database_manager.py`
* **Instructions:**
    1.  Locate the function `find_or_create_group_plan`.
    2.  Inside this function, right before the `INSERT` statement, add the logic to generate the `display_name`.
        ```python
        display_name = f"{name} - {duration_days} days - ₹{price}"
        ```
    3.  Modify the `INSERT` statement to include and save the new `display_name` value.
        * **Old:** `(name, duration_days, default_amount)`
        * **New:** `(name, display_name, duration_days, default_amount)`
        * Make sure to update the `VALUES` part of the query accordingly.

---

#### **Task 2: Make `is_active` Status for Group Memberships a Runtime Calculation - DONE**

* **Objective:** Remove the stored `is_active` column and calculate it dynamically.

* **Phase 2.1: Update Database Schema**
    * **File to Modify:** `reporter/database.py`
    * **Instructions:**
        1.  In the `create_tables` function, find the `CREATE TABLE group_class_memberships` statement.
        2.  Delete the line `is_active INTEGER,`.

* **Phase 2.2: Update Data Fetching Logic**
    * **File to Modify:** `reporter/database_manager.py`
    * **Instructions:**
        1.  Locate the function `get_all_group_class_memberships_for_view`.
        2.  Modify the `SELECT` query.
        3.  Instead of selecting `is_active`, add a calculated column that checks if the current date is between the start and end dates.
            ```sql
            -- Replace this:
            -- m.is_active,
            -- With this:
            CASE
                WHEN date('now') BETWEEN m.start_date AND m.end_date THEN 'Active'
                ELSE 'Inactive'
            END as status,
            ```

* **Phase 2.3: Update Data Creation Logic**
    * **File to Modify:** `reporter/database_manager.py`
    * **Instructions:**
        1.  Locate the `create_group_class_membership` function.
        2.  Remove the `is_active` parameter from the function definition.
        3.  Remove the line that adds `is_active` to the `INSERT` statement.

* **Phase 2.4: Update API Endpoint**
    * **File to Modify:** `reporter/app_api.py`
    * **Instructions:**
        1.  Locate the `add_group_class_membership` function.
        2.  In the call to `db_mngr.create_group_class_membership`, remove the `is_active=is_active` argument.

* **Phase 2.5: Update Migration Script**
    * **File to Modify:** `reporter/migrate_historical_data.py`
    * **Instructions:**
        1.  In `migrate_gc_data`, find the call to `db_mngr.create_group_class_membership`.
        2.  Remove the `is_active` argument from this function call.
        3.  Delete the `plan_status` variable and the logic that calculates it.

---

#### **Task 3: Refine `join_date` Logic for New Members - DONE**

* **Objective:** Set a member's `join_date` to their first-ever membership start date during migration.

* **Phase 3.1: Update Member Creation Logic**
    * **File to Modify:** `reporter/database_manager.py`
    * **Instructions:**
        1.  Locate the `add_member` function.
        2.  Change its signature to accept an optional `join_date`. If it's not provided, it should default to `date.today()`.
            ```python
            # From:
            def add_member(self, name, phone_number, email, is_active=True):
            # To:
            def add_member(self, name, phone_number, email, is_active=True, join_date=None):
            ```
        3.  Add logic to use the provided `join_date` or fall back to the default.
            ```python
            join_date_to_use = join_date if join_date else date.today().isoformat()
            # ...
            cursor.execute(
                "... VALUES (?, ?, ?, ?, ?)",
                (name, phone_number, email, join_date_to_use, is_active)
            )
            ```

* **Phase 3.2: Update Migration Script**
    * **File to Modify:** `reporter/migrate_historical_data.py`
    * **Instructions:**
        1.  At the beginning of the `migrate_data` function, read both `GC.csv` and `PT.csv` into separate pandas DataFrames.
        2.  Create a unified list of all members and their earliest start dates. You will need to iterate through both dataframes, extract phone numbers and start dates (`Plan Start Date` for GC, `Payment Date` for PT), and store the earliest date for each unique phone number in a dictionary.
        3.  Modify the loops in `migrate_gc_data` and `migrate_pt_data`. When you encounter a member for the first time, look up their earliest start date from the dictionary you created and pass it as the `join_date` when calling `db_mngr.add_member`.

---

#### **Task 4: Simplify `pt_memberships` Table - DONE**

* **Objective:** Remove unused columns from the `pt_memberships` table and associated logic.

* **Phase 4.1: Update Database Schema**
    * **File to Modify:** `reporter/database.py`
    * **Instructions:**
        1.  In the `create_tables` function, find the `CREATE TABLE pt_memberships` statement.
        2.  Delete the lines `sessions_remaining INTEGER,` and `notes TEXT,`.

* **Phase 4.2: Update Database & API Logic**
    * **File:** `reporter/database_manager.py`
        1.  In `add_pt_membership`, remove `sessions_remaining` and `notes` from the function parameters and the `INSERT` statement.
        2.  In `get_all_pt_memberships`, remove these two columns from the `SELECT` statement.
    * **File:** `reporter/app_api.py`
        1.  In `add_pt_membership`, remove `sessions_remaining` and `notes` from the parameters passed to the database manager.

* **Phase 4.3: Update UI**
    * **File to Modify:** `reporter/streamlit_ui/app.py`
    * **Instructions:**
        1.  In the `render_pt_memberships_tab` function, locate the form for creating a new PT membership.
        2.  Delete the `st.number_input` for "Sessions Remaining".
        3.  Delete the `st.text_area` for "Notes".
        4.  Find the `st.dataframe` or `st.data_editor` that displays the PT memberships table and remove "sessions_remaining" and "notes" from the list of displayed columns.

* **Phase 4.4: Update Migration Script**
    * **File to Modify:** `reporter/migrate_historical_data.py`
    * **Instructions:**
        1.  In `migrate_pt_data`, find the call to `db_mngr.add_pt_membership`.
        2.  Remove the `sessions_remaining` and `notes` arguments from the function call.
        3.  Delete any variables that were reading these values from the CSV.
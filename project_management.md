# Project Management: Kranos MMA Reporter

## 1. Instructions for Developers

All development must adhere to the standards outlined in the `Developer's Guide`.

* **Architecture**: Respect the 4-layer architecture (UI -> API -> Business Logic -> Data Access). The UI layer must only communicate with the API layer.
* **Code Style**: All Python code must be formatted with `black` and pass `flake8` linting before being committed.
* **Git Workflow**: Use the feature-branching workflow. Create a new branch from `main` for each distinct task.
* **Contribution**: To add or modify a feature, you must work through all four layers of the architecture, from the data access layer up to the UI.
* **Project Management**: Pick up from the last done task. Finish it. Mark it done if completed. Add notes if not.

---

## 2. Task List

Here is the breakdown of pending tasks. Mark a task as complete by changing `- [ ]` to `- [x]`.

### Phase 1: UI Refactor

* **Objective**: Transition the user interface to Streamlit, implementing the necessary forms and tables for daily operations.

* **Task 1.1: Implement Member Management UI in Streamlit**
    * **Status**: ` - [x] `
    * **Instructions**:
        1.  In `reporter/streamlit_ui/app.py`, create a form using `st.form` within the "Members" tab.
        2.  Add `st.text_input` fields for "Name" and "Phone" and a `st.form_submit_button`.
        3.  The button's action should call `api.add_member(name, phone)`.
        4.  Display the success or error message returned from the API call.
        5.  Ensure the main member table automatically refreshes after a new member is added.

* **Task 1.2: Implement Plan Management UI in Streamlit**
    * **Status**: ` - [x] `
    * **Instructions**:
        1.  In `reporter/streamlit_ui/app.py`, expand the "Plans" tab.
        2.  Add a form with "Plan Name" and "Duration (days)" input fields and a "Save Plan" button.
        3.  The button's action should call `api.add_plan(name, duration)`.
        4.  Display success or error messages and refresh the table on success.

* **Task 1.3: Implement Transaction Management UI in Streamlit**
    * **Status**: ` - [ ] `
    * **Instructions**:
        1.  Create a new "Transactions" tab in `reporter/streamlit_ui/app.py`.
        2.  Add a form to add new transactions. It should include `st.selectbox` dropdowns to select a member and a plan.
        3.  The form should also have inputs for "Amount", "Payment Date", and "Start Date".
        4.  The "Add Transaction" button should call `api.add_transaction(...)` with the appropriate details.
        5.  Display success or error messages.

### Phase 2: Align Database Schema with Design

* **Objective**: Update the database schema in `database.py` to match the `Design Document`.

* **Task 2.1: Add `price` and `type` columns to `plans` table**
    * **Status**: ` - [ ] `
    * **Instructions**:
        1.  Modify the `CREATE TABLE IF NOT EXISTS plans` statement in `reporter/database.py`.
        2.  Add a `price` column (INTEGER) and a `type` column (TEXT) as specified in the design.
        3.  Update the `add_plan` and `update_plan` methods in `database_manager.py` to handle these new fields.

* **Task 2.2: Refactor `transactions` table columns**
    * **Status**: ` - [ ] `
    * **Instructions**:
        1.  Modify the `CREATE TABLE IF NOT EXISTS transactions` statement in `reporter/database.py`.
        2.  Rename `payment_date` to `transaction_date` and `amount_paid` to `amount` to match the design document.
        3.  Update all methods in `database_manager.py` that interact with these columns to use the new names.

### Phase 3: Implement Core Business Logic

* **Objective**: Implement the business rules defined in the `Design Document` within the `DatabaseManager` class.

* **Task 3.1: Enforce Member Name Uniqueness**
    * **Status**: ` - [ ] `
    * **Instructions**:
        1.  The design specifies that member names must be unique. The current database schema has a `UNIQUE` constraint on the `phone` field.
        2.  Modify the `CREATE TABLE IF NOT EXISTS members` statement in `reporter/database.py` to add a `UNIQUE` constraint to the `client_name` column.
        3.  Verify that the `add_member_to_db` method in `database_manager.py` correctly catches the `sqlite3.IntegrityError` for duplicate names.

* **Task 3.2: Implement Member Status Logic**
    * **Status**: ` - [ ] `
    * **Instructions**:
        1.  The design requires a member's status to be active only if they have a current, valid plan.
        2.  Create a new private method `_update_member_status(member_id)` in `database_manager.py`.
        3.  This method should check if the member has any plan where the `end_date` is in the future.
        4.  If they have an active plan, set `is_active = 1` in the `members` table; otherwise, set it to `0`.
        5.  Call this method from `add_transaction` to ensure status is re-evaluated upon renewal.
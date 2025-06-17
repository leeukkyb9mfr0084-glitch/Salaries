### **Task List: Codebase Hardening**

**Objective:** To systematically review the application code, identify weak points, and implement fixes to prevent common runtime errors.

---

#### **Phase 1: Fortify the Data Layer Contracts [COMPLETED]**

**Instruction:** Your highest priority is to create explicit, unbreakable contracts for data moving between application layers. We will complete the DTO (Data Transfer Object) pattern implementation we discussed previously.

1.  **Define All DTOs:**
    * In `reporter/models.py`, create a unique `@dataclass` for every type of data view the application needs. Based on the UI tabs, you will need to create or verify the existence of the following:
        * `MemberView`
        * `GroupPlanView`
        * `GroupClassMembershipView`
        * `PTMembershipView`

2.  **Update Database Manager:**
    * Go to `reporter/database_manager.py`.
    * For every `get_all_..._for_view` function, change its return signature to use the appropriate DTO list (e.g., `-> List[GroupPlanView]`).
    * Inside each function, convert the raw database results into your DTOs before returning them.
        ```python
        # Example for get_all_group_plans_for_view
        rows = cursor.execute(query).fetchall()
        return [GroupPlanView(**row) for row in rows]
        ```

3.  **Update API and UI Layers:**
    * In `reporter/app_api.py`, update the return type hints for all data-fetching functions to match the DTOs from the step above.
    * In `reporter/streamlit_ui/app.py`, search for every location where this data is used. Change all dictionary-style access (`data['key']`) to attribute-style access (`data.key`). Your IDE should flag these locations as errors once the API signatures are updated, making them easy to find.

---

#### **Phase 2: Harden Database Interactions [COMPLETED]**

**Instruction:** We must ensure all database queries are safe and that the application gracefully handles cases where data is not found.

1.  **Verify SQL Parameterization:**
    * Manually inspect every function in `reporter/database_manager.py`.
    * Confirm that no Python variables are ever formatted directly into a SQL query string using f-strings or `%`. This is non-negotiable to prevent SQL injection.
    * **Invalid:** `cursor.execute(f"SELECT * FROM members WHERE id = {member_id}")`
    * **Correct:** `cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))`

2.  **Check for `None` Return Values:**
    * Identify every function that uses `cursor.fetchone()` (e.g., `get_member_by_id`). These functions return `None` when no record is found.
    * Trace every call to these functions in the UI layer (`reporter/streamlit_ui/app.py`).
    * Before attempting to use the returned object, you **must** add a check:
        ```python
        # Example in the UI, when populating a form
        member_data = api.get_member_by_id(selected_id)
        if member_data is None:
            st.error(f"Member with ID {selected_id} not found.")
            return # Stop further execution
        
        # Now it's safe to use member_data
        st.text_input("Name", value=member_data.name) 
        ```
    * Failure to do this will result in an `AttributeError: 'NoneType' object has no attribute 'name'`.

---

#### **Phase 3: Validate All User Input [COMPLETED]**

**Instruction:** Never trust input from the UI. All data must be validated before it is sent to the database.

1.  **Enforce Required Fields:**
    * In `reporter/streamlit_ui/app.py`, go to every `st.form`.
    * Before the `api.create_...` or `api.update_...` call, add `if/else` checks to ensure that mandatory fields are not empty. If a field is empty, use `st.error()` to inform the user and `return` to stop the submission.

2.  **Sanitize Data Types:**
    * Look at all numeric inputs (`st.number_input`). The API layer expects numbers (`int`, `float`), not strings. Ensure the data is in the correct format. `st.number_input` helps with this, but be mindful of any `st.text_input` used for numbers.
    * Verify all date inputs. The `st.date_input` returns a `date` object. The database manager expects a string. Ensure every date object is formatted correctly (`my_date.strftime('%Y-%m-%d')`) before being passed to the API.

---

#### **Phase 4: Stabilize UI State [COMPLETED]**

**Instruction:** Prevent errors caused by Streamlit's re-run behavior and state management.

1.  **Initialize All Session State Keys:**
    * Create a list of all keys you use in `st.session_state` (e.g., `selected_member_id`, `selected_gc_membership_id`).
    * At the beginning of your main app function, write a block that initializes all of them if they don't already exist.
        ```python
        if 'selected_member_id' not in st.session_state:
            st.session_state.selected_member_id = "add_new"
        if 'selected_pt_membership_id' not in st.session_state:
            st.session_state.selected_pt_membership_id = "add_new"
        # ... and so on for all keys
        ```
    * This will prevent `KeyError` exceptions the first time a user interacts with a widget.
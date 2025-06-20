Of course. Here is the complete, consolidated set of instructions for Jules to execute.

### **Log Entry: 2025-06-20 07:58 AM**

**Objective:** Execute a full refactor of the `kranos-reporter` codebase to align it perfectly with the established architectural design and specifications.

**Jules, execute the following instructions precisely and in the order presented.**

---

### **Phase 1: Refactor Foundational Layers**

**Task 1.1: Update `reporter/database.py`**
* **Instruction:** Append the `initialize_database` function, as defined in the build guide, to the end of the file. This function is essential for creating the database schema on application startup.

**Task 1.2: Update `reporter/main.py`**
* **Instruction:** Modify the `main` function. Before the `app.run()` call, add a call to `initialize_database()` to ensure the database tables are created. The function should now have two lines in it.

---

### **Phase 2: Refactor the Data Access Layer (`database_manager.py`)**

**Context:** This is a critical step. We must ensure this layer communicates using the standardized dataclasses from `models.py`, not raw database tuples.

**Task 2.1: Refactor all functions in `reporter/database_manager.py`**
* **Instruction 1 (Connection Factory):** In the `get_connection` function, insert the line `conn.row_factory = sqlite3.Row` before `return conn`.
* **Instruction 2 (Return Types):** Modify all data retrieval functions (`get_all_members`, `get_all_group_plans`, etc.) to return lists of the corresponding dataclass objects (e.g., `List[Member]`). You will use a list comprehension like `[Member(**row) for row in cursor.fetchall()]`.
* **Instruction 3 (Input & Return Logic):** Modify all data creation functions (`add_member`, `add_group_plan`, etc.) to:
    1.  Accept a dataclass object as their single argument (e.g., `def add_member(member: Member)`).
    2.  Use the attributes of this object in the `cursor.execute` call (e.g., `member.name`, `member.email`).
    3.  After `conn.commit()`, set the ID on the passed object (`member.id = cursor.lastrowid`) and return the modified object.

---

### **Phase 3: Refactor the Business Logic Layer (`app_api.py`)**

**Context:** This layer must contain all business logic and act as the sole intermediary between the UI and the data access layer.

**Task 3.1: Refactor all functions in `reporter/app_api.py`**
* **Instruction 1 (Signatures):** Update all function signatures to match the build guide exactly. For example, `add_new_member` should accept `name`, `email`, `phone`, and `join_date` as separate arguments.
* **Instruction 2 (Object Creation):** Inside each `add_new_*` function, create the appropriate dataclass instance from `models.py` using the function's arguments.
* **Instruction 3 (Business Logic):** Implement the core business logic. Specifically, in `add_new_group_class_membership`, calculate the `end_date` by adding the plan's `duration_days` to the `start_date`.
* **Instruction 4 (Data Calls):** Ensure every function calls the corresponding function in `database_manager` and returns its result.

---

### **Phase 4: Refactor the UI Layer (`streamlit_ui/app.py`)**

**Context:** The UI must be completely decoupled from the data access layer. It should only ever communicate with the `app_api`.

**Task 4.1: Refactor all functions in `reporter/streamlit_ui/app.py`**
* **Instruction 1 (API Calls):** Go through the entire file. Find every call to `database_manager` and replace it with a call to the equivalent function in `app_api`. For example, a call to `database_manager.get_all_members()` must be changed to `app_api.get_all_members()`.
* **Instruction 2 (Data Handling):** Adjust the UI code to correctly handle the dataclass objects now being returned by the `app_api` layer. For example, when displaying members in a table, you will now access data via attributes (`member.name`, `member.email`) instead of by index.

---

### **Phase 5: Final Verification**

**Task 5.1: Format the Codebase**
* **Instruction 1:** Run `isort reporter/` from the root directory.
* **Instruction 2:** Run `black reporter/` from the root directory.

**Task 5.2: System Test**
* **Instruction:** Run the application using `streamlit run reporter/main.py`. Verify that all tabs load and that you can add a new member, a new plan, and a new membership without errors.

Execute these phases in order. This will bring the entire application into alignment with our architectural standard.
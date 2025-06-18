# Kranos Reporter: Official Developer's Guide
*Version 1.0 - June 18, 2025*

## 1. Introduction
This document establishes the official development standards and architectural patterns for the Kranos Reporter application. Its purpose is to ensure that all future development is consistent, maintainable, and stable. Adherence to these principles is mandatory for all contributors.

## 2. Core Architectural Principles
The application follows a strict, multi-layered architecture. Understanding this separation of concerns is critical.

### 2.1. The Four Layers
1.  **UI Layer (`reporter/streamlit_ui/app.py`)**
    * **Responsibility:** Solely for rendering UI components and capturing user input.
    * **Rule:** This layer must not contain any business logic (e.g., calculating dates, complex validation). It receives data via DTOs and sends user input to the API Layer. It is meant to be as "dumb" as possible.

2.  **API Layer (`reporter/app_api.py`)**
    * **Responsibility:** To act as the single, clean interface between the UI and the backend logic.
    * **Rule:** This layer does not interact with the database directly. It orchestrates calls to the Data Access Layer and shapes the results into the DTOs required by the UI.

3.  **Data Access Layer (`reporter/database_manager.py`)**
    * **Responsibility:** To handle all database interactions. All SQL queries and `connection.execute()` calls must be contained within this layer.
    * **Rule:** Functions in this layer must not return raw database tuples or dictionaries. They must return data structured in application-level objects, preferably the DTOs defined in `models.py`.

4.  **Database Schema (`reporter/database.py`)**
    * **Responsibility:** To define the structure of the database tables.
    * **Rule:** This file is the ultimate source of truth for all data structures. It must be kept in perfect sync with `app_specs.md`.

### 2.2. The DTO Contract (`reporter/models.py`)
Data Transfer Objects (DTOs), defined as `@dataclass` objects in `models.py`, are the formal "contract" for passing data between layers.
* The UI should **only** receive data from the API Layer in the form of a DTO instance or a list of DTOs.
* This prevents database-specific details from leaking into the UI and ensures that the data structure is predictable and self-documenting.

## 3. The Development Workflow
All changes, from minor bug fixes to major features, must follow this schema-first workflow to ensure all layers remain synchronized.

1.  **Update the Specification:** Clearly define the change in `app_specs.md`.
2.  **Update the Schema (`database.py`):** If the change requires a database modification, alter the `CREATE TABLE` statements first.
3.  **Update the DTO (`models.py`):** Update the relevant "View" DTO to reflect the data structure the UI will need.
4.  **Update the Data Access Layer (`database_manager.py`):** Modify the SQL queries to support the new schema and correctly populate the updated DTO.
5.  **Update the API Layer (`app_api.py`):** Adjust function signatures to handle the new data flow to and from the Data Access Layer.
6.  **Update the UI Layer (`streamlit_ui/app.py`):** Finally, implement the UI changes, relying entirely on the new DTO structure provided by the API Layer.
7.  **Update the Tests (`reporter/tests/`):** This is a mandatory step. Write or update unit tests that cover the new changes and verify the new logic.
8.  **Run All Tests:** Execute the entire test suite to ensure the changes have not introduced any regressions.

## 4. Coding Standards & Conventions

### 4.1. Naming
* **Classes & DTOs:** `PascalCase` (e.g., `DatabaseManager`, `PTMembershipView`)
* **Functions & Variables:** `snake_case` (e.g., `get_all_members`, `member_list`)
* **Constants:** `UPPER_SNAKE_CASE` (e.g., `DB_FILE`)

### 4.2. Error Handling
* The `database_manager.py` and `app_api.py` layers should raise specific `ValueError` exceptions for predictable issues (e.g., duplicate entries, invalid IDs).
* The `streamlit_ui/app.py` layer must wrap all API calls in `try...except` blocks to catch these exceptions and display a user-friendly message using `st.error()`. Do not let raw exceptions crash the app.

### 4.3. UI State Management
* All Streamlit session state keys must be initialized with a default value at the top of `app.py`. This prevents `KeyError` exceptions and makes the app's state predictable.
* Use descriptive, unique keys for widgets and session state variables (e.g., `key="pt_form_member_id_select"`).

## 5. Testing Strategy
* Every function in `database_manager.py` that executes a query must have corresponding test coverage in `reporter/tests/`.
* When a bug is fixed, a new unit test that replicates the bug must be added to prevent future regressions.
* A change is not considered "Done" until all existing and new tests pass.

## 6. Database Migrations
* This project handles schema migrations manually.
* Any change to `database.py` that alters a table requires a corresponding update to `reporter/migrate_historical_data.py` to ensure historical data can be correctly migrated to the new schema.
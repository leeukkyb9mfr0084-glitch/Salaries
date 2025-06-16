### Kranos Reporter: Developer's Guide
*Version 6.0 - Last Updated: June 16, 2025*

This guide provides an overview of the application's architecture and the key modules involved.

#### 1. Project Structure
The project is organized into several key directories:
- `reporter/`: The main application package.
  - `streamlit_ui/`: Contains the Streamlit front-end application (`app.py`).
  - `tests/`: Contains all unit and integration tests.
  - `data/`: (If needed) For storing the SQLite database file.
- `scripts/`: (If needed) For one-off utility scripts like data migration.

#### 2. Core Modules

**`reporter/database.py`**
- **Purpose:** Defines the database schema and handles the initial creation of tables.
- **Key Function:** `create_database()`: Executes the `CREATE TABLE` SQL statements for all four tables: `members`, `group_plans`, `group_class_memberships`, and `pt_memberships`. It also seeds the initial `group_plans`.

**`reporter/database_manager.py`**
- **Purpose:** Acts as the data access layer (DAL). This is the *only* module that should directly execute SQL queries against the database.
- **Key Responsibilities:**
  - Provides CRUD (Create, Read, Update, Delete) methods for each of the four main tables.
  - All business logic related to data (e.g., generating unique display names, calculating report data) resides here.
  - Function Naming Convention: Functions are named to clearly indicate the table they operate on (e.g., `add_group_plan`, `get_all_pt_memberships`).

**`reporter/app_api.py`**
- **Purpose:** Serves as a simple API layer or facade that sits between the UI and the `DatabaseManager`.
- **Key Responsibilities:**
  - Exposes the functionality of the `DatabaseManager` to the Streamlit UI.
  - Its functions are simple pass-through calls to the corresponding `DatabaseManager` methods. This separation allows for easier future expansion, such as adding a true web API (e.g., FastAPI) without changing the core business logic.

**`reporter/streamlit_ui/app.py`**
- **Purpose:** The main entry point for the user-facing application.
- **Key Responsibilities:**
  - Renders all UI components using the Streamlit library.
  - Handles user input and triggers calls to the `app_api`.
  - Organizes the UI into four distinct tabs: `Members`, `Group Plans`, `Memberships`, and `Reporting`.
  - The `Memberships` tab contains internal logic to switch between "Group Class Memberships" and "Personal Training Memberships" modes.

#### 3. Development Workflow

1.  **Schema Changes:** All changes to the database structure must start in `database.py`.
2.  **Logic Changes:** New business logic or data queries are added to `database_manager.py`.
3.  **API Exposure:** New `DatabaseManager` functions are exposed to the UI via `app_api.py`.
4.  **UI Implementation:** The UI in `streamlit_ui/app.py` calls the API functions to display data and handle user actions.
5.  **Testing:** New functionality must be accompanied by tests in the `reporter/tests/` directory.

#### 4. Running the Application
To run the application locally, execute the following command from the root directory of the project:
```bash
streamlit run reporter/streamlit_ui/app.py
```

#### 5. Running Tests
To run the entire test suite, execute the following command from the root directory:
```bash
python -m pytest
```
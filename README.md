# Kranos MMA Reporter

## Objective
An internal tool designed to manage members, group class plans, personal training memberships, and all associated financial reporting for Kranos MMA. The system facilitates comprehensive tracking and management of these core operational areas.

## Technology Stack
* **Language**: Python 3
* **GUI**: Streamlit
* **Database**: SQLite
* **Testing**: pytest

## Features

The application is organized into four main tabs:

### Members Tab
*   **Full CRUD Operations:** Add, view, edit, and delete member profiles.
*   **Information:** Manage member details such as name, phone number, email, and active status.
*   **Join Date:** Automatically recorded (though managed by backend logic, not directly edited in this tab).

### Group Plans Tab
*   **Full CRUD Operations:** Create, view, edit, and delete group class plan templates (e.g., "MMA Basic - 30 days").
*   **Details:** Define plan name, duration in days, and default price.
*   **Activation:** Toggle plans as active or inactive. Inactive plans are hidden from selection when creating new group class memberships.
*   **Display Name:** Automatically generated (e.g., "Plan Name - X days") for clarity.

### Memberships Tab
This tab consolidates the management of both Group Class and Personal Training memberships via a mode selector.

*   **Mode Selector:** Switch between "Group Class Memberships" and "Personal Training Memberships".

*   **Group Class Memberships Mode:**
    *   **Create:** Assign members to a group plan with a specified start date and amount paid. End date and membership type ('New'/'Renewal') are automatically determined.
    *   **View:** Display a list of all group class memberships, showing member name, plan name, start/end dates, amount paid, and status.
    *   **Delete:** Remove group class membership records.
    *   *(Note: Direct editing of existing group class memberships is simplified in the current UI.)*

*   **Personal Training Memberships Mode:**
    *   **Create:** Record new PT packages for members, including purchase date, amount paid, sessions purchased, and optional notes. Sessions remaining are initialized.
    *   **View:** Display a list of all PT memberships, showing member name, purchase details, sessions purchased/remaining, and notes.
    *   **Delete:** Remove PT membership records.
    *   *(Note: UI does not include functionality to decrement/manage `sessions_remaining` after purchase. Direct editing of existing PT memberships is simplified in the current UI.)*

### Reporting Tab
*   **Monthly Financial Report:**
    *   Generate a financial report for a selected month.
    *   Sums total revenue from **both** group class memberships and personal training memberships based on their purchase dates within the selected month.
    *   Provides a detailed list of all transactions contributing to the revenue.
    *   Allows downloading the report as an Excel file.
*   **Upcoming Renewals Report:**
    *   Generate a report of all active **group class memberships** scheduled to end within the next 30 days.
    *   Lists member details, plan name, and end dates to facilitate renewal follow-ups.
    *   This report does not include Personal Training data.

## Database Schema
The application uses an SQLite database with the following four core tables:

**`members` table:** Stores information about gym members.
```sql
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE,
    email TEXT,
    join_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);
```

**`group_plans` table:** Stores templates for duration-based group class plans.
```sql
CREATE TABLE IF NOT EXISTS group_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    duration_days INTEGER NOT NULL,
    default_amount REAL NOT NULL,
    display_name TEXT UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT 1
);
```

**`group_class_memberships` table:** Tracks the purchase of time-based group class memberships.
```sql
CREATE TABLE IF NOT EXISTS group_class_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    plan_id INTEGER,
    start_date TEXT,
    end_date TEXT,
    amount_paid REAL,
    purchase_date TEXT,
    membership_type TEXT, -- 'New' or 'Renewal'
    is_active BOOLEAN,
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (plan_id) REFERENCES group_plans(id)
);
```

**`pt_memberships` table:** Tracks the purchase of session-based personal training packages.
```sql
CREATE TABLE IF NOT EXISTS pt_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    purchase_date TEXT,
    amount_paid REAL,
    sessions_purchased INTEGER,
    sessions_remaining INTEGER,
    notes TEXT,
    FOREIGN KEY (member_id) REFERENCES members(id)
);
```

## File Structure

/
|-- reporter/
|   |-- streamlit_ui/
|   |   |-- app.py              # Main Streamlit application GUI (Entry point for UI)
|   |-- main.py                 # Script for setup: dependency checks, DB initialization, data migration trigger (see Setup and Run)
|   |-- app_api.py              # Application Programming Interface between UI and database logic
|   |-- database.py             # Defines database schema and initial table creation
|   |-- database_manager.py     # Handles all database CRUD operations and business logic
|   |-- migrate_historical_data.py # Script for migrating historical data from CSV files
|   |-- data/
|   |   |-- kranos_data.db      # SQLite database file
|   |-- tests/                  # Contains all pytest tests for the 'reporter' module
|-- scripts/
|   |-- process_data.py         # Example utility script for processing raw_data.csv
|-- tests/                      # Contains tests for scripts (e.g., test_process_data.py)
|-- Kranos MMA Members.xlsx - GC.csv  # Data file used by 'migrate_historical_data.py'
|-- Kranos MMA Members.xlsx - PT.csv  # Data file used by 'migrate_historical_data.py'
|-- data/
|   |-- raw_data.csv            # Raw data CSV file for 'scripts/process_data.py'
|-- README.md                   # This file
|-- requirements.txt            # Project dependencies
|-- Developers_Guide.md         # In-depth guide for developers
|-- app_specs.md                # Detailed application specifications
|-- .gitignore                  # Specifies intentionally untracked files that Git should ignore
|-- run_all_tests.sh            # Shell script to run all tests
|-- run_validation.sh           # Shell script for running validations
|-- validate_fixes.sh           # Shell script for validating fixes
... (other configuration files)
```

## Setup and Run

1.  **Ensure Python:** You have Python 3.8 or newer installed.
2.  **Project Root:** Navigate to the root directory of the project in your terminal.
3.  **Prepare Data for Initial Migration (Optional):**
    *   If you have existing data to migrate from `Kranos MMA Members.xlsx - GC.csv` and `Kranos MMA Members.xlsx - PT.csv`, place these files in the project's root directory.
    *   The setup script in the next step will attempt to run the migration process. (See `## Data Migration` section for more details on the script `reporter/migrate_historical_data.py`).
4.  **Initial Setup (Run Once):**
    Execute the main setup script. This will:
    *   Check and install any missing Python dependencies from `requirements.txt`.
    *   Initialize the SQLite database (`kranos_data.db`) in the `reporter/data/` directory.
    *   Attempt to run the data migration process using the CSV files (if present).
    ```bash
    python reporter/main.py
    ```
    *Note: The script might restart itself once if it needs to install dependencies. This script internally calls the migration script detailed in the `## Data Migration` section.*
5.  **Run the Application:**
    Once the initial setup is complete, or for subsequent uses, run the Streamlit application:
    ```bash
    python -m streamlit run reporter/streamlit_ui/app.py
    ```

## Data Migration

The `reporter/migrate_historical_data.py` script is provided to import existing member and membership data from CSV files into the application's database.

**Important Considerations:**
*   **Destructive Operation:** Running this script is a destructive operation. It will permanently delete all existing data from the `members`, `group_plans`, `group_class_memberships`, and `pt_memberships` tables before attempting to import data from the CSV files. **It is highly recommended to back up the database file (`reporter/data/kranos_data.db`) before running this script if you have existing data you wish to preserve.**
*   **CSV File Requirements:**
    *   The script expects two CSV files to be present in the **root directory** of the project:
        *   `Kranos MMA Members.xlsx - GC.csv`: For group class membership data.
        *   `Kranos MMA Members.xlsx - PT.csv`: For personal training membership data.
    *   Ensure these files are correctly named and placed before running the migration.

**Functionality:**
*   Reads member and membership data from the specified CSV files.
*   Creates new member records if they don't already exist (based on phone number).
*   Creates new group plan records if they don't already exist (based on plan details in the CSVs).
*   Populates the `group_class_memberships` and `pt_memberships` tables with data from the CSVs.

**How to Run:**
*   **Automated (during initial setup):**
    The `python reporter/main.py` script (used for initial setup as described in "Setup and Run") attempts to execute the migration process automatically. If the CSV files are in place, this might be sufficient for the initial data load. *Note: The `reporter/main.py` script may currently try to call an older version of the migration script name (`reporter.migrate_data` instead of `reporter.migrate_historical_data`). This may require an update in `reporter/main.py` itself for seamless automatic execution. Until then, manual execution is more reliable.*
*   **Manual Execution:**
    To ensure the migration runs correctly, or if the automated step via `reporter/main.py` encounters issues, you can execute the migration script directly from the project's root directory:
    ```bash
    python reporter/migrate_historical_data.py
    ```
    Remember the destructive nature of this script and ensure the required CSV files are correctly placed in the root directory.

## Data Processing Script

The `scripts/process_data.py` script reads data from `data/raw_data.csv`, calculates the sum of the 'value' column, and prints the result.

### Running the Script

To run the script, use the following command:

```bash
python scripts/process_data.py
```

### Running the Tests

To run the tests for the script, use the following command:

```bash
python -m unittest tests.test_process_data
```

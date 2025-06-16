# Kranos MMA Reporter

## Objective
An application designed to manage gym operations, including memberships, personal training (PT) bookings, and financial reporting. The system allows for easy management of members, plans, and activities, and it includes a robust test suite to ensure data integrity and reliability.

## Technology Stack
* **Language**: Python 3
* **GUI**: Streamlit
* **Database**: SQLite
* **Testing**: pytest

## Features

### Membership Management
* **Add & View Members**: Add new members with their name and phone number. The join date is automatically set based on their first recorded activity.
* **List All Members**: View a searchable and scrollable list of all gym members.
* **Activity History**: Select a member to view their complete history of all group memberships and personal training bookings.
* **Add Group Memberships**: Assign members to a group plan with a specified start date, payment details, and payment method.
* **Add PT Bookings**: Record personal training sessions for members, including start date, number of sessions, and amount paid.

### Plan Management
* **Add & Edit Plans**: Create new membership plans or update existing ones by specifying a name and duration in days.
* **Activate/Deactivate Plans**: Toggle the active status of plans. Inactive plans will not appear in the dropdown when adding a new group membership.

### Reporting
* **Pending Renewals**: Generate a report of all memberships scheduled to end in the current month.
* **Monthly Finance Report**: Calculate and display the total revenue from all group memberships and PT bookings for the previous month.

## Database Schema
The application uses the following SQLite schema:

**`members` Table**
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

**`plans` Table**
```sql
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    default_duration INTEGER NOT NULL,
    price INTEGER,
    type TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    UNIQUE(name, default_duration, type)
);
```

**`memberships` Table**
```sql
CREATE TABLE IF NOT EXISTS memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    plan_id INTEGER,
    start_date TEXT,
    end_date TEXT,
    is_active BOOLEAN,
    amount_paid REAL,
    purchase_date TEXT,
    membership_type TEXT,
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (plan_id) REFERENCES plans(id)
);
```

## File Structure
```
/reporter/
|-- main.py                 # Main script (if still primary entry point, or describe new role)
|-- streamlit_ui/
|   |-- app.py              # Main Streamlit application GUI
|-- app_api.py              # Application Programming Interface for UI and backend logic
|-- database.py             # Defines the database schema and setup
|-- database_manager.py     # Handles all database CRUD operations
|-- migrate_data.py         # Script to migrate data from CSV files
|-- /data/
|   |-- kranos_data.db      # SQLite database file
|-- /tests/                 # Contains all pytest tests
|-- /simulations/           # Scripts for simulating various application flows
|-- requirements.txt        # Project dependencies
```

## Setup and Run
1.  Ensure you have Python 3 installed.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Place your data files (`Kranos MMA Members.xlsx - GC.csv` and `Kranos MMA Members.xlsx - PT.csv`) in the root directory of the project if you wish to use the data migration script.
4.  Run the application by executing the `main.py` script:
    ```bash
    python -m streamlit run reporter/streamlit_ui/app.py
    ```

## Data Migration
The `migrate_data.py` script is provided to import existing member data from CSV files into the database. Duration is always in days. Month wise calculation is not needed.

**Warning: Running the migration script is a destructive operation. It will permanently delete all existing data from the members, plans, and memberships tables before importing data from the CSV files.**

* **Functionality**:
    * Reads member data from `Kranos MMA Members.xlsx - GC.csv` for group classes and `Kranos MMA Members.xlsx - PT.csv` for personal training.
    * Creates new members if they don't exist based on their phone number.
    * Creates new plans if they don't exist.
    * Populates the `memberships` table with the data from the CSV files (previously `group_memberships` and `pt_bookings`).
* **How to Run**:
    Execute the script directly from your terminal:
    ```bash
    python reporter/migrate_data.py
    ```

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

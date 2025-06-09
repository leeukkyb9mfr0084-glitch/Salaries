# Kranos MMA Reporter

## Objective
A desktop application designed to manage gym operations, including memberships, personal training (PT) bookings, and financial reporting. The system allows for easy management of members, plans, and activities, and it includes a robust test suite to ensure data integrity and reliability.

## Technology Stack
* **Language**: Python 3
* **GUI**: CustomTkinter
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
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    phone TEXT UNIQUE,
    join_date TEXT
);
```

**`plans` Table**
```sql
CREATE TABLE IF NOT EXISTS plans (
    plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_name TEXT NOT NULL UNIQUE,
    duration_days INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
```

**`transactions` Table**
```sql
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    plan_id INTEGER,
    payment_date TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT,
    amount_paid REAL NOT NULL,
    payment_method TEXT,
    sessions INTEGER,
    FOREIGN KEY (member_id) REFERENCES members (member_id),
    FOREIGN KEY (plan_id) REFERENCES plans (plan_id)
);
```

## File Structure
```
/reporter/
|-- main.py                 # Main application entry point
|-- gui.py                  # Defines the CustomTkinter GUI
|-- database.py             # Defines the database schema and setup
|-- database_manager.py     # Handles all database CRUD operations
|-- migrate_data.py         # Script to migrate data from CSV files
|-- /data/
|   |-- kranos_data.db      # SQLite database file
|-- /tests/
|   |-- test_database.py
|   |-- test_database_manager.py
|-- requirements.txt
```

## Setup and Run
1.  Ensure you have Python 3 installed.
2.  Place your data files (`Kranos MMA Members.xlsx - GC.csv` and `Kranos MMA Members.xlsx - PT.csv`) in the root directory of the project if you wish to use the data migration script.
3.  Run the application by executing the `main.py` script:
    ```bash
    python reporter/main.py
    ```
4.  The application will automatically check for and install the required `customtkinter` dependency on the first run.

## Data Migration
The `migrate_data.py` script is provided to import existing member data from CSV files into the database.

**Warning: Running the migration script is a destructive operation. It will permanently delete all existing data from the members, plans, and transactions tables before importing data from the CSV files.**

* **Functionality**:
    * Reads member data from `Kranos MMA Members.xlsx - GC.csv` for group classes and `Kranos MMA Members.xlsx - PT.csv` for personal training.
    * Creates new members if they don't exist based on their phone number.
    * Creates new plans if they don't exist.
    * Populates the `transactions` table with the data from the CSV files (previously `group_memberships` and `pt_bookings`).
* **How to Run**:
    Execute the script directly from your terminal:
    ```bash
    python reporter/migrate_data.py
    ```

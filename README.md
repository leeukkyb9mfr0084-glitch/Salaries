# Kranos MMA Reporter

## Objective
A desktop application to manage gym memberships, track payments, and generate key reports, validated by a robust test suite.

## Technology Stack
- Language: Python 3
- GUI: CustomTkinter
- Database: SQLite
- Testing: pytest

## File Structure
```
/reporter/
|-- main.py
|-- gui.py
|-- database.py
|-- database_manager.py
|-- PROJECT_PLAN.md
|-- /data/
|   |-- kranos_data.db
|-- /tests/
    |-- test_database_manager.py
    |-- ... (other test files)
```

## Database Schema
The application must use the following SQLite schema.

### Table: `members`
```sql
CREATE TABLE IF NOT EXISTS members (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    phone TEXT UNIQUE,
    join_date TEXT
);
```

### Table: `plans`
```sql
CREATE TABLE IF NOT EXISTS plans (
    plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_name TEXT NOT NULL UNIQUE,
    duration_days INTEGER NOT NULL
);
```

### Table: `group_memberships`
```sql
CREATE TABLE IF NOT EXISTS group_memberships (
    membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    plan_id INTEGER NOT NULL,
    payment_date TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    amount_paid REAL NOT NULL,
    payment_method TEXT,
    FOREIGN KEY (member_id) REFERENCES members (member_id),
    FOREIGN KEY (plan_id) REFERENCES plans (plan_id)
);
```

### Table: `pt_bookings`
```sql
CREATE TABLE IF NOT EXISTS pt_bookings (
    pt_booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    sessions INTEGER NOT NULL,
    amount_paid REAL NOT NULL,
    FOREIGN KEY (member_id) REFERENCES members (member_id)
);
```
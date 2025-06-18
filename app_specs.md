### Kranos Reporter: Application Specifications
*Version 7.0 - Last Updated: June 18, 2025*

#### 1. Overview
This document outlines the complete functional and technical specifications for the Kranos Reporter application. The application is an internal tool designed to manage members, group class plans, personal training memberships, and all associated financial reporting.

#### 2. Database Schema
The application will use an SQLite database with the following four core tables. This schema separates duration-based group classes from session-based personal training for data integrity.

**`members` table:**
* `id` (INTEGER, Primary Key)
* `name` (TEXT, Mandatory)
* `phone` (TEXT, Mandatory, Unique)
* `email` (TEXT)
* `join_date` (TEXT)
* `is_active` (BOOLEAN)

**`group_plans` table:**
*This table stores templates for duration-based group classes.*
* `id` (INTEGER, Primary Key)
* `name` (TEXT, Mandatory)
* `duration_days` (INTEGER, Mandatory)
* `default_amount` (REAL, Mandatory)
* `display_name` (TEXT, Unique)
* `is_active` (BOOLEAN)

**`group_class_memberships` table:**
*This table tracks the purchase of time-based group class memberships.*
* `id` (INTEGER, Primary Key)
* `member_id` (INTEGER, Foreign Key to `members.id`)
* `plan_id` (INTEGER, Foreign Key to `group_plans.id`)
* `start_date` (TEXT)
* `end_date` (TEXT)
* `amount_paid` (REAL)
* `purchase_date` (TEXT)
* `membership_type` (TEXT: 'New' or 'Renewal')
* `is_active` (BOOLEAN)

**`pt_memberships` table:**
*This table tracks the purchase of session-based personal training packages.*
* `id` (INTEGER, Primary Key)
* `member_id` (INTEGER, Foreign Key to `members.id`)
* `purchase_date` (TEXT)
* `amount_paid` (REAL)
* `sessions_purchased` (INTEGER)
* `sessions_remaining` (INTEGER)

#### 3. Functional Specifications by Tab

The application will feature a four-tab navigation structure.

**`Members` Tab**
* **Functionality:** This tab is dedicated exclusively to Member CRUD (Create, Read, Update, Delete) operations. No other functionality will be present.

**`Group Plans` Tab**
* **Functionality:** This tab is for managing the templates for group class plans (e.g., "MMA Mastery - 90 Days"). The UI and logic will support full CRUD operations on the `group_plans` table.

**`Memberships` Tab**
* **Functionality:** This tab consolidates the management of both Group Class and Personal Training memberships.
* **Mode Selector:** A radio button will be placed at the top of this tab with two options: "Group Class Memberships" (default) and "Personal Training Memberships". The selection will determine the content displayed below.
* **"Group Class Memberships" Mode:**
    * **UI:** A two-panel layout. The **left panel** will feature the form for creating a new time-based membership. It will include a dropdown to select a member and another to select from the `group_plans` list. The **right panel** will display a filterable, selectable list of all existing records from the `group_class_memberships` table. Selecting a record will populate the form on the left for editing.
* **"Personal Training Memberships" Mode:**
    * **UI:** A two-panel layout consistent with the Group Class mode. The **left panel** will feature the form for creating a new PT package, including fields for selecting a member, `Purchase Date`, `Amount Paid`, and `Sessions Purchased`. The **right panel** will display a filterable, selectable list of all existing records from the `pt_memberships` table. Selecting a record will populate the form on the left for editing.
    * **Note:** The `sessions_remaining` field will be saved to the database but no UI functionality will be built to manage it (e.g., no "Use Session" button).
    
**`Reporting` Tab**
* **Functionality:** This tab provides financial and renewal reporting.
* **Financial Report:**
    * **Logic:** The report must query **both** the `group_class_memberships` and `pt_memberships` tables. It will sum the `amount_paid` from all records in both tables where the `purchase_date` falls within the user-selected date range.
* **Renewals Report:**
    * **Logic:** This report's logic will **only** query the `group_class_memberships` table. It will list all active memberships where the `end_date` is within the next 30 days. This report will not include PT data.
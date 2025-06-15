Of course. Here are the updated application specifications as a direct response.

***

### Kranos Reporter: Application Specifications
*Version 2.1 - Last Updated: June 15, 2025*

#### 1. Overview
This document outlines the complete functional and technical specifications for the Kranos Reporter application. The application is an internal tool designed to manage gym memberships, track payments, and provide essential financial and renewal reporting, based on a model where each membership record is a self-contained transaction.

#### 2. Database Schema
The application will use a simplified SQLite database with the following **three core tables**:

**`members` table:**
* `id` (INTEGER, Primary Key)
* `name` (TEXT)
* `phone` (TEXT)
* `email` (TEXT)
* `join_date` (TEXT)
* `is_active` (BOOLEAN)

**`plans` table:**
* `id` (INTEGER, Primary Key)
* `name` (TEXT)
* `price` (REAL)
* `type` (TEXT: 'GC' or 'PT')
* `is_active` (BOOLEAN)

**`memberships` table:**
* `id` (INTEGER, Primary Key)
* `member_id` (INTEGER, Foreign Key to `members.id`)
* `plan_id` (INTEGER, Foreign Key to `plans.id`)
* `start_date` (TEXT)
* `end_date` (TEXT)
* `amount_paid` (REAL)
* `purchase_date` (TEXT)
* `membership_type` (TEXT: 'New' or 'Renewal')
* `is_active` (BOOLEAN)

#### 3. Functional Specifications by Tab

**Memberships Tab (Primary Tab)**
This tab features a two-panel layout.

* **Left Panel: Create / Update Membership**
    * **Member Name:** A searchable dropdown list of all active members.
    * **Plan Name:** A dropdown list of all active plans.
    * **Plan Duration (Days):** A number input for the length of the membership.
    * **Amount:** A number input for the amount being paid for this specific purchase.
    * **Start Date:** A date picker control.
    * **SAVE Button Logic:**
        1.  Calculates `end_date` from `start_date` + `Plan Duration`.
        2.  Sets the `purchase_date` to the current date.
        3.  Checks if the selected member has any prior memberships. If not, sets `membership_type` to "New". If they do, sets it to "Renewal".
        4.  Creates **one single new row** in the `memberships` table containing all of this information.
    * **CLEAR Button:** Resets all form fields.

* **Right Panel: View / Manage Memberships**
    * **Filters:** Text inputs for `Name` and `Phone`, and radio buttons for `Active`/`Inactive` status.
    * **Membership List:** A table displays membership records matching the filters.
    * **Selection & Actions:** When a user clicks a row, it becomes the "Selected Membership." `EDIT` and `DELETE` buttons appear and function on the selected record.

**Reporting Tab**

* **Financial Report:**
    * **Logic:** Allows user to select a date range. It will query the `memberships` table, summing the `amount_paid` for all records where the **`purchase_date`** falls within that range. It generates a summary and an Excel download.
* **Renewals Report:**
    * **Logic:** Lists all active memberships (`is_active = True`) from the `memberships` table where the **`end_date`** is within the next 30 days.
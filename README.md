# Kranos Reporter

A Streamlit application for managing gym memberships and generating financial reports.

## Prerequisites

Before you begin, ensure you have the following installed:
* Python (version 3.8 or higher)

## Setup Instructions

Follow these steps to set up your local development environment.

### 1. Create a Virtual Environment

First, create and activate a virtual environment to isolate project dependencies.

* **On macOS / Linux:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

* **On Windows:**
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

### 2. Install Dependencies

With your virtual environment active, install the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### Simplified Setup and Launch (Recommended)

A shell script `run_app.sh` is provided to automate the entire setup and launch process. This script will:
1. Create a virtual environment (if it doesn't exist).
2. Activate the virtual environment.
3. Install all required dependencies.
4. Run the data migration (initial setup).
5. Launch the Streamlit application.

To use the script, navigate to the project's root directory in your terminal and run:

```bash
./run_app.sh
```
This is the recommended way to run the application.

## Data Migration (First-Time Setup)

**Note:** If you are using the `run_app.sh` script, it handles this step automatically. These instructions are for manual setup.

Before running the application for the first time, you must migrate the historical data from the provided CSV files into the application's database.

**Required Files:**
Ensure the following files are present in the root directory of the project:
* `Kranos MMA Members.xlsx - GC.csv`
* `Kranos MMA Members.xlsx - PT.csv`

**Run the Migration Script:**
Execute the following command from the project's root directory. This will create and populate the `kranos_reporter.db` SQLite database file.

```bash
python -m reporter.migrate_historical_data
```
You only need to run this command once during the initial setup.

## Running the Application

**Note:** If you are using the `run_app.sh` script, it handles this step automatically. These instructions are for manual setup.

Once the setup and data migration are complete, you can run the application.

**Launch the Streamlit App:**
Execute the following command from the project's root directory. This will start the web server and open the application in your default browser.

```bash
python -m streamlit run reporter/main.py
```

## Running Tests (For Developers)

To ensure the application's logic is working correctly after making code changes, run the automated test suite.

**Execute Pytest:**
With your virtual environment active, run the following command from the project's root directory:

```bash
pytest
```
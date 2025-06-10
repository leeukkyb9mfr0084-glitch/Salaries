import pytest
import sqlite3
import os

# Functions and variables to be tested or used in tests
from reporter.migrate_data import process_gc_data
from reporter.database import create_database
# Assuming DB_FILE is imported in migrate_data from database_manager,
# or defined in migrate_data itself. We'll patch where it's used by process_gc_data.
    # The key is that process_gc_data itself and any database_manager functions it calls
    # must use the patched DB_FILE.

# Path to the dummy CSV for testing
DUMMY_CSV_PATH = os.path.join(os.path.dirname(__file__), 'dummy_gc_data.csv')
TEST_DB_DIR_MIGRATE = 'reporter/tests/test_data_migrate' # Separate dir for this test's DB
TEST_DB_FILE_MIGRATE = os.path.join(TEST_DB_DIR_MIGRATE, 'test_migrate_data.db')


@pytest.fixture
def migrate_test_db(monkeypatch):
    """Fixture to set up a temporary file-based database for migration tests."""
    os.makedirs(TEST_DB_DIR_MIGRATE, exist_ok=True)

    # Monkeypatch DB_FILE before create_database and process_gc_data are called.
    # This ensures that all references to DB_FILE within the scope of reporter.migrate_data
    # and reporter.database_manager (if it's imported and used by migrate_data) point to our test DB.
    monkeypatch.setattr("reporter.migrate_data.DB_FILE", TEST_DB_FILE_MIGRATE)
    monkeypatch.setattr("reporter.database_manager.DB_FILE", TEST_DB_FILE_MIGRATE) # Critical for consistency
    # The create_database function in reporter.database module takes db_name as a parameter,
    # so it does not need its own DB_FILE to be patched, as long as it's called with the correct test db path.

    # Create schema in the test DB file
    create_database(db_name=TEST_DB_FILE_MIGRATE)

    # Monkeypatch the GC_CSV_PATH for process_gc_data
    monkeypatch.setattr("reporter.migrate_data.GC_CSV_PATH", DUMMY_CSV_PATH)

    yield TEST_DB_FILE_MIGRATE # Provide the path to the test DB

    # Teardown
    if os.path.exists(TEST_DB_FILE_MIGRATE):
        os.remove(TEST_DB_FILE_MIGRATE)
    if os.path.exists(TEST_DB_DIR_MIGRATE) and not os.listdir(TEST_DB_DIR_MIGRATE):
        os.rmdir(TEST_DB_DIR_MIGRATE)


def test_migration_clears_tables(migrate_test_db): # Uses the fixture
    '''
    Tests if process_gc_data correctly clears the relevant tables using a file-based test DB.
    '''
    test_db_path = migrate_test_db # Get the path from the fixture

    # Connect to the test DB to pre-populate data
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    # Setup: Pre-populate some data
    # (The schema is already created by the fixture's call to create_database)
    # Members
    cursor.execute("INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)", ("Test User 1", "111", "2023-01-01"))
    cursor.execute("INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)", ("Test User 2", "222", "2023-01-02"))
    # Plans
    cursor.execute("INSERT INTO plans (plan_name, duration_days, is_active) VALUES (?, ?, ?)", ("Test Plan 1", 30, True))
    # Transactions
    cursor.execute("INSERT INTO transactions (member_id, transaction_type, plan_id, payment_date, start_date, amount_paid) VALUES (?, ?, ?, ?, ?, ?)",
                   (1, "Group Class", 1, "2023-01-01", "2023-01-01", 100))
    conn.commit()

    # Verify pre-population
    # sqlite_sequence is managed by SQLite automatically for tables with AUTOINCREMENT.
    # After inserting into members, plans, and transactions, there should be one entry for each.
    assert cursor.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 2
    assert cursor.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 1
    assert cursor.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1
    # After inserting into autoincrement tables, sqlite_sequence should have entries.
    # The exact count might include other system sequences or if other tables used AUTOINCREMENT.
    # We are interested in these specific three.
    assert cursor.execute("SELECT COUNT(*) FROM sqlite_sequence WHERE name IN ('members', 'plans', 'transactions')").fetchone()[0] == 3, \
        "sqlite_sequence should have entries for members, plans, and transactions after population."

    conn.close() # Close connection used for setup before process_gc_data runs with its own connection.

    # Action: Run the migration process
    # process_gc_data will use the DB_FILE monkeypatched by the fixture
    # process_gc_data might print errors if the dummy CSV is not perfectly aligned with its expectations
    # after the deletion step, but the focus of this test is the deletion itself.
    try:
        process_gc_data()
    except Exception as e:
        # If process_gc_data fails due to CSV processing after deletion,
        # we might want to catch it if the test is only about the deletion part.
        # However, a robust test would ensure the dummy CSV allows it to run to completion or mock the CSV processing part.
        print(f"process_gc_data raised an exception: {e}. Checking table clearing status anyway.")

    # Assertions: Reconnect to the database to check if tables are cleared
    conn_assert = sqlite3.connect(test_db_path)
    cursor_assert = conn_assert.cursor()

    # Assertions after process_gc_data has run with dummy_gc_data.csv:
    # The dummy CSV adds 1 member, 1 plan (if 'Test Plan' is new), and 1 transaction.
    # So, the tables will not be empty.
    assert cursor_assert.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 1, \
        "Members table should have 1 entry from dummy CSV"

    # Check if the "Test Plan" from dummy CSV is the only one, or if other plans might exist
    # depending on how get_or_create_plan_id behaves with existing plans vs new ones.
    # For this test, let's assume "Test Plan" is uniquely handled.
    # If the dummy CSV's plan name could conflict with pre-seeded plans in a different test setup,
    # this might need more specific checks. Given this test's fixture, it should be clean.
    assert cursor_assert.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 1, \
        "Plans table should have 1 entry from dummy CSV"

    assert cursor_assert.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1, \
        "Transactions table should have 1 entry from dummy CSV"

    # Check sqlite_sequence: after clearing and adding 1 of each, seq should be 1 for each.
    # And there should be 3 rows in sqlite_sequence for these tables.
    seq_members = cursor_assert.execute("SELECT seq FROM sqlite_sequence WHERE name = 'members'").fetchone()
    seq_plans = cursor_assert.execute("SELECT seq FROM sqlite_sequence WHERE name = 'plans'").fetchone()
    seq_transactions = cursor_assert.execute("SELECT seq FROM sqlite_sequence WHERE name = 'transactions'").fetchone()

    assert seq_members is not None and seq_members[0] >= 1, "sqlite_sequence for members should exist and be >= 1"
    assert seq_plans is not None and seq_plans[0] >= 1, "sqlite_sequence for plans should exist and be >= 1"
    assert seq_transactions is not None and seq_transactions[0] >= 1, "sqlite_sequence for transactions should exist and be >= 1"

    # Verify the specific data if necessary
    member_name = cursor_assert.execute("SELECT client_name FROM members WHERE client_name = 'Dummy User'").fetchone()
    assert member_name is not None and member_name[0] == "Dummy User", "Dummy User not found in members table"

    # Cleanup (assertion connection, fixture handles file deletion)
    conn_assert.close()


# Test for new duration and end_date logic in process_gc_data
def test_process_gc_data_duration_and_end_date_logic(migrate_test_db, monkeypatch):
    """
    Tests the logic for calculating duration_days and handling end_date_override
    in process_gc_data based on 'Plan Start Date', 'Plan End Date', and 'Plan Duration'.
    """
    from reporter.migrate_data import process_gc_data # Re-import for clarity or if not top-level
    from datetime import datetime, timedelta # For date calculations

    test_db_path = migrate_test_db

    # 1. Define CSV data as a string
    csv_data = """Client Name,Phone,Plan Type,Plan Duration,Plan Start Date,Plan End Date,Payment Date,Amount,Payment Mode
User With EndDate,1001,Explicit EndDate Plan,3,01/01/2024,31/01/2024,01/01/2024,100,Cash
User With Duration,1002,Duration Plan,2,15/02/2024,,15/02/2024,200,Online
User Invalid EndDate,1003,Invalid EndDate Plan,1,01/03/2024,01/01/2000,01/03/2024,300,Card
User Missing StartDate,1004,No Start Plan,1,,01/01/2025,01/03/2024,400,Card
"""
    # 2. Create a temporary CSV file
    temp_csv_filename = "test_specific_gc_data.csv"
    temp_csv_path = os.path.join(TEST_DB_DIR_MIGRATE, temp_csv_filename)
    with open(temp_csv_path, "w") as f:
        f.write(csv_data)

    # 3. Use monkeypatch to make process_gc_data use this temporary CSV
    monkeypatch.setattr("reporter.migrate_data.GC_CSV_PATH", temp_csv_path)

    # 4. Call process_gc_data()
    process_gc_data()

    # 5. Connect to the test database
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    # Helper to get member_id
    def get_member_id(phone):
        cursor.execute("SELECT member_id FROM members WHERE phone = ?", (phone,))
        result = cursor.fetchone()
        return result[0] if result else None

    # 6. Assertions
    # User With EndDate (Phone 1001)
    member_id_1001 = get_member_id("1001")
    assert member_id_1001 is not None
    cursor.execute("SELECT start_date, end_date, plan_id FROM transactions WHERE member_id = ?", (member_id_1001,))
    tx_1001 = cursor.fetchone()
    assert tx_1001 is not None
    assert tx_1001[0] == "2024-01-01" # start_date
    assert tx_1001[1] == "2024-01-31" # end_date (from CSV)
    plan_id_1001 = tx_1001[2]
    cursor.execute("SELECT duration_days FROM plans WHERE plan_id = ?", (plan_id_1001,))
    plan_1001 = cursor.fetchone()
    assert plan_1001 is not None
    # Duration from dates: 31/01/2024 - 01/01/2024 = 30 days
    assert plan_1001[0] == 30

    # User With Duration (Phone 1002)
    member_id_1002 = get_member_id("1002")
    assert member_id_1002 is not None
    cursor.execute("SELECT start_date, end_date, plan_id FROM transactions WHERE member_id = ?", (member_id_1002,))
    tx_1002 = cursor.fetchone()
    assert tx_1002 is not None
    start_date_1002_str = "2024-02-15"
    assert tx_1002[0] == start_date_1002_str # start_date
    # Expected end_date: 15/02/2024 + (2 months * 30 days/month) = 15/02/2024 + 60 days
    expected_end_date_1002 = (datetime.strptime(start_date_1002_str, '%Y-%m-%d') + timedelta(days=60)).strftime('%Y-%m-%d')
    assert tx_1002[1] == expected_end_date_1002 # end_date
    plan_id_1002 = tx_1002[2]
    cursor.execute("SELECT duration_days FROM plans WHERE plan_id = ?", (plan_id_1002,))
    plan_1002 = cursor.fetchone()
    assert plan_1002 is not None
    assert plan_1002[0] == 60 # 2 months * 30 days

    # User Invalid EndDate (Phone 1003) - End date is before start date, fallback to duration
    member_id_1003 = get_member_id("1003")
    assert member_id_1003 is not None
    cursor.execute("SELECT start_date, end_date, plan_id FROM transactions WHERE member_id = ?", (member_id_1003,))
    tx_1003 = cursor.fetchone()
    assert tx_1003 is not None
    start_date_1003_str = "2024-03-01"
    assert tx_1003[0] == start_date_1003_str # start_date
    # Expected end_date: 01/03/2024 + (1 month * 30 days/month) = 01/03/2024 + 30 days
    expected_end_date_1003 = (datetime.strptime(start_date_1003_str, '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')
    assert tx_1003[1] == expected_end_date_1003 # end_date
    plan_id_1003 = tx_1003[2]
    cursor.execute("SELECT duration_days FROM plans WHERE plan_id = ?", (plan_id_1003,))
    plan_1003 = cursor.fetchone()
    assert plan_1003 is not None
    assert plan_1003[0] == 30 # 1 month * 30 days

    # User Missing StartDate (Phone 1004) - Should be skipped
    member_id_1004 = get_member_id("1004")
    assert member_id_1004 is None # Member should not have been created
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE member_id = (SELECT member_id FROM members WHERE phone = '1004')")
    tx_count_1004 = cursor.fetchone()[0]
    assert tx_count_1004 == 0 # No transactions for this user

    # Cleanup
    conn.close()
    if os.path.exists(temp_csv_path):
        os.remove(temp_csv_path)

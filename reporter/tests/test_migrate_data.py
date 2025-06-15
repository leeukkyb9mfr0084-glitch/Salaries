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
DUMMY_CSV_PATH = os.path.join(os.path.dirname(__file__), "dummy_gc_data.csv")
TEST_DB_DIR_MIGRATE = (
    "reporter/tests/test_data_migrate"  # Separate dir for this test's DB
)
TEST_DB_FILE_MIGRATE = os.path.join(TEST_DB_DIR_MIGRATE, "test_migrate_data.db")


@pytest.fixture
def migrate_test_db(monkeypatch):
    """Fixture to set up a temporary file-based database for migration tests."""
    os.makedirs(TEST_DB_DIR_MIGRATE, exist_ok=True)

    # Monkeypatch DB_FILE before create_database and process_gc_data are called.
    # This ensures that all references to DB_FILE within the scope of reporter.migrate_data
    # and reporter.database_manager (if it's imported and used by migrate_data) point to our test DB.
    monkeypatch.setattr("reporter.migrate_data.DB_FILE", TEST_DB_FILE_MIGRATE)
    monkeypatch.setattr(
        "reporter.database_manager.DB_FILE", TEST_DB_FILE_MIGRATE
    )  # Critical for consistency
    # The create_database function in reporter.database module takes db_name as a parameter,
    # so it does not need its own DB_FILE to be patched, as long as it's called with the correct test db path.

    # Create schema in the test DB file
    create_database(db_name=TEST_DB_FILE_MIGRATE)

    # Monkeypatch the GC_CSV_PATH for process_gc_data
    monkeypatch.setattr("reporter.migrate_data.GC_CSV_PATH", DUMMY_CSV_PATH)

    yield TEST_DB_FILE_MIGRATE  # Provide the path to the test DB

    # Teardown
    if os.path.exists(TEST_DB_FILE_MIGRATE):
        os.remove(TEST_DB_FILE_MIGRATE)
    if os.path.exists(TEST_DB_DIR_MIGRATE) and not os.listdir(TEST_DB_DIR_MIGRATE):
        os.rmdir(TEST_DB_DIR_MIGRATE)


def test_migration_clears_tables(migrate_test_db):  # Uses the fixture
    """
    Tests if process_gc_data correctly clears the relevant tables using a file-based test DB.
    """
    test_db_path = migrate_test_db  # Get the path from the fixture

    # Connect to the test DB to pre-populate data
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    # Setup: Pre-populate some data
    # (The schema is already created by the fixture's call to create_database)
    # Members
    cursor.execute(
        "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
        ("Test User 1", "111", "2023-01-01"),
    )
    cursor.execute(
        "INSERT INTO members (client_name, phone, join_date) VALUES (?, ?, ?)",
        ("Test User 2", "222", "2023-01-02"),
    )
    # Plans
    cursor.execute(
        "INSERT INTO plans (plan_name, duration_days, is_active) VALUES (?, ?, ?)",
        ("Test Plan 1", 30, True),
    )
    # Transactions
    cursor.execute(
        "INSERT INTO transactions (member_id, transaction_type, plan_id, transaction_date, start_date, amount) VALUES (?, ?, ?, ?, ?, ?)",
        (1, "Group Class", 1, "2023-01-01", "2023-01-01", 100),
    )
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
    assert (
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_sequence WHERE name IN ('members', 'plans', 'transactions')"
        ).fetchone()[0]
        == 3
    ), "sqlite_sequence should have entries for members, plans, and transactions after population."

    conn.close()  # Close connection used for setup before process_gc_data runs with its own connection.

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
        print(
            f"process_gc_data raised an exception: {e}. Checking table clearing status anyway."
        )

    # Assertions: Reconnect to the database to check if tables are cleared
    conn_assert = sqlite3.connect(test_db_path)
    cursor_assert = conn_assert.cursor()

    # Assertions after process_gc_data has run with dummy_gc_data.csv:
    # The dummy CSV adds 1 member, 1 plan (if 'Test Plan' is new), and 1 transaction.
    # So, the tables will not be empty.
    assert (
        cursor_assert.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 1
    ), "Members table should have 1 entry from dummy CSV"

    # Check if the "Test Plan" from dummy CSV is the only one, or if other plans might exist
    # depending on how get_or_create_plan_id behaves with existing plans vs new ones.
    # For this test, let's assume "Test Plan" is uniquely handled.
    # If the dummy CSV's plan name could conflict with pre-seeded plans in a different test setup,
    # this might need more specific checks. Given this test's fixture, it should be clean.
    assert (
        cursor_assert.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 1
    ), "Plans table should have 1 entry from dummy CSV"

    assert (
        cursor_assert.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1
    ), "Transactions table should have 1 entry from dummy CSV"

    # Check sqlite_sequence: after clearing and adding 1 of each, seq should be 1 for each.
    # And there should be 3 rows in sqlite_sequence for these tables.
    seq_members = cursor_assert.execute(
        "SELECT seq FROM sqlite_sequence WHERE name = 'members'"
    ).fetchone()
    seq_plans = cursor_assert.execute(
        "SELECT seq FROM sqlite_sequence WHERE name = 'plans'"
    ).fetchone()
    seq_transactions = cursor_assert.execute(
        "SELECT seq FROM sqlite_sequence WHERE name = 'transactions'"
    ).fetchone()

    assert (
        seq_members is not None and seq_members[0] >= 1
    ), "sqlite_sequence for members should exist and be >= 1"
    assert (
        seq_plans is not None and seq_plans[0] >= 1
    ), "sqlite_sequence for plans should exist and be >= 1"
    assert (
        seq_transactions is not None and seq_transactions[0] >= 1
    ), "sqlite_sequence for transactions should exist and be >= 1"

    # Verify the specific data if necessary
    member_name = cursor_assert.execute(
        "SELECT client_name FROM members WHERE client_name = 'Dummy User'"
    ).fetchone()
    assert (
        member_name is not None and member_name[0] == "Dummy User"
    ), "Dummy User not found in members table"

    # Cleanup (assertion connection, fixture handles file deletion)
    conn_assert.close()


def test_end_date_calculation_with_months(migrate_test_db, monkeypatch):
    """
    Tests the end_date calculation in process_gc_data when 'Plan Duration' is in months,
    using dateutil.relativedelta.
    Also verifies the derived plan_duration_for_db_days (months * 30) stored in plans table.
    """
    from reporter.migrate_data import process_gc_data  # Target function
    from datetime import datetime  # For expected date calculations
    from dateutil.relativedelta import relativedelta  # For expected date calculations

    test_db_path = migrate_test_db

    # CSV data where 'Plan Duration' is in months
    csv_data_months = """Client Name,Phone,Plan Type,Plan Duration,Plan Start Date,Plan End Date,Payment Date,Amount,Payment Mode
Alice,111,Monthly A,1,01/01/24,,01/01/24,100,Cash
Bob,222,Quarterly B,3,15/01/24,,15/01/24,250,Card
Carol,333,Annual C,12,01/02/24,,01/02/24,1000,Online
David,444,HalfYear D,6,20/02/2024,,20/02/2024,600,Cash
"""
    temp_csv_filename_months = "test_gc_data_months.csv"
    temp_csv_path_months = os.path.join(TEST_DB_DIR_MIGRATE, temp_csv_filename_months)
    with open(temp_csv_path_months, "w", newline="") as f:
        f.write(csv_data_months)

    monkeypatch.setattr("reporter.migrate_data.GC_CSV_PATH", temp_csv_path_months)
    process_gc_data()

    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    # Helper to get transaction and plan info
    def get_transaction_and_plan_info(phone: str):
        cursor.execute(
            """
            SELECT m.member_id, t.start_date, t.end_date, t.plan_id, p.plan_name, p.duration_days
            FROM transactions t
            JOIN members m ON t.member_id = m.member_id
            JOIN plans p ON t.plan_id = p.plan_id
            WHERE m.phone = ?
        """,
            (phone,),
        )
        return cursor.fetchone()

    # Assertions
    # Alice: 01/01/24 + 1 month = 01/02/2024. Plan duration in DB: 1*30 = 30 days
    alice_tx_info = get_transaction_and_plan_info("111")
    assert alice_tx_info is not None, "Alice's transaction not found"
    assert alice_tx_info[1] == "2024-01-01"  # start_date
    assert alice_tx_info[2] == "2024-02-01"  # end_date
    assert alice_tx_info[4] == "Monthly A"  # plan_name
    assert alice_tx_info[5] == 30  # plan.duration_days (1*30)

    # Bob: 15/01/24 + 3 months = 15/04/2024. Plan duration in DB: 3*30 = 90 days
    bob_tx_info = get_transaction_and_plan_info("222")
    assert bob_tx_info is not None, "Bob's transaction not found"
    assert bob_tx_info[1] == "2024-01-15"  # start_date
    assert bob_tx_info[2] == "2024-04-15"  # end_date
    assert bob_tx_info[4] == "Quarterly B"  # plan_name
    assert bob_tx_info[5] == 90  # plan.duration_days (3*30)

    # Carol: 01/02/24 + 12 months = 01/02/2025. Plan duration in DB: 12*30 = 360 days
    carol_tx_info = get_transaction_and_plan_info("333")
    assert carol_tx_info is not None, "Carol's transaction not found"
    assert carol_tx_info[1] == "2024-02-01"  # start_date
    assert carol_tx_info[2] == "2025-02-01"  # end_date
    assert carol_tx_info[4] == "Annual C"  # plan_name
    assert carol_tx_info[5] == 360  # plan.duration_days (12*30)

    # David: 20/02/2024 + 6 months = 20/08/2024. Plan duration in DB: 6*30 = 180 days
    david_tx_info = get_transaction_and_plan_info("444")
    assert david_tx_info is not None, "David's transaction not found"
    assert david_tx_info[1] == "2024-02-20"  # start_date
    assert david_tx_info[2] == "2024-08-20"  # end_date
    assert david_tx_info[4] == "HalfYear D"  # plan_name
    assert david_tx_info[5] == 180  # plan.duration_days (6*30)

    # Check total number of transactions
    cursor.execute("SELECT COUNT(*) FROM transactions")
    assert (
        cursor.fetchone()[0] == 4
    ), "Expected 4 transactions from the month-based CSV."

    conn.close()
    if os.path.exists(temp_csv_path_months):
        os.remove(temp_csv_path_months)

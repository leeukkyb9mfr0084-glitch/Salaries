import sqlite3
import pytest
import os  # Added os import
from reporter.database import (
    create_database,
    seed_initial_plans,
    initialize_database,
    DB_FILE as ORIGINAL_DB_FILE,
)  # Import initialize_database and original DB_FILE

# Expected table names
EXPECTED_TABLES = ["members", "plans", "memberships"]
EXPECTED_INITIAL_PLANS = [
    ("Monthly - Unrestricted", 30, 100.0, "Monthly Unrestricted"),
    ("3 Months - Unrestricted", 90, 270.0, "3 Months Unrestricted"),
    ("Annual - Unrestricted", 365, 1000.0, "Annual Unrestricted"),
]


def test_create_database_tables():
    """
    Tests if create_database function correctly creates all specified tables.
    """
    db_name = ":memory:"
    conn = None  # Initialize conn here to ensure it's available in finally
    try:
        conn = create_database(db_name)  # Create tables and get connection
        assert (
            conn is not None
        ), "create_database(':memory:') should return a connection."
        cursor = conn.cursor()

        # Query sqlite_master table for existing table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        # Assert that all expected tables are present
        for table_name in EXPECTED_TABLES:
            assert table_name in tables, f"Table '{table_name}' not found in database."

        # For good measure, check that no other unexpected tables are present (owned by us)
        # sqlite_sequence is an internal table sqlite creates for AUTOINCREMENT
        non_expected_tables = [
            t for t in tables if t not in EXPECTED_TABLES and t != "sqlite_sequence"
        ]
        assert (
            not non_expected_tables
        ), f"Unexpected tables found: {non_expected_tables}"

    except sqlite3.Error as e:
        pytest.fail(f"Database operation failed: {e}")
    finally:
        if conn:
            conn.close()


def test_seed_initial_plans():
    """
    Tests if seed_initial_plans correctly inserts the default plans.
    """
    db_name = ":memory:"
    conn = None  # Initialize conn here to ensure it's available in finally
    try:
        conn = create_database(db_name)  # Create tables and get connection
        assert (
            conn is not None
        ), "create_database(':memory:') should return a connection."

        # seed_initial_plans expects a connection object
        seed_initial_plans(conn)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, duration_days, default_amount, display_name FROM plans ORDER BY duration_days;"
        )
        seeded_plans = cursor.fetchall()

        assert len(seeded_plans) == len(
            EXPECTED_INITIAL_PLANS
        ), f"Expected {len(EXPECTED_INITIAL_PLANS)} plans, but found {len(seeded_plans)}."

        for i, expected_plan in enumerate(EXPECTED_INITIAL_PLANS):
            assert (
                seeded_plans[i][0] == expected_plan[0]
            ), f"Plan name mismatch: Expected '{expected_plan[0]}', got '{seeded_plans[i][0]}'"
            assert (
                seeded_plans[i][1] == expected_plan[1]
            ), f"Plan duration mismatch for '{expected_plan[0]}': Expected {expected_plan[1]}, got {seeded_plans[i][1]}"
            assert (
                seeded_plans[i][2] == expected_plan[2]
            ), f"Plan default_amount mismatch for '{expected_plan[0]}': Expected {expected_plan[2]}, got {seeded_plans[i][2]}"
            assert (
                seeded_plans[i][3] == expected_plan[3]
            ), f"Plan display_name mismatch for '{expected_plan[0]}': Expected {expected_plan[3]}, got {seeded_plans[i][3]}"

    except sqlite3.Error as e:
        pytest.fail(f"Database operation failed during seeding or verification: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # This allows running tests directly with `python reporter/tests/test_database.py`
    # though `pytest` is the recommended way.
    pytest.main()


def test_initialize_database_runs_without_error(monkeypatch, tmp_path):
    """
    Tests if initialize_database function runs without error, creates the DB and tables,
    and seeds initial plans, using a temporary database file.
    """
    # Define a temporary database path within pytest's tmp_path fixture
    test_db_name = "test_temp_init.db"
    test_db_dir = tmp_path / "data"  # Use a subdirectory within tmp_path
    test_db_file = test_db_dir / test_db_name

    # Monkeypatch reporter.database.DB_FILE to this test_db_file
    monkeypatch.setattr("reporter.database.DB_FILE", str(test_db_file))

    # Ensure the target directory for the test_db_file does not exist initially
    # initialize_database should create it.
    if os.path.exists(test_db_dir):
        # If we want to ensure initialize_database creates the directory,
        # we might remove it here. However, initialize_database itself has logic
        # to create os.path.dirname(DB_FILE). Let's rely on that.
        # For the DB file itself, initialize_database calls create_database,
        # which will create a new DB or open existing.
        # Let's ensure the DB file specifically is gone.
        if os.path.exists(test_db_file):
            os.remove(test_db_file)

    conn = None
    try:
        # Call initialize_database()
        # This should create the directory (if not exists), db, tables, and seed plans.
        initialize_database()

        # Assert that the test_db_file now exists
        assert os.path.exists(
            test_db_file
        ), f"Database file '{test_db_file}' was not created."

        # Connect to test_db_file and verify tables and initial plans
        conn = sqlite3.connect(test_db_file)
        cursor = conn.cursor()

        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables_in_test_db = [row[0] for row in cursor.fetchall()]
        for (
            table_name
        ) in (
            EXPECTED_TABLES
        ):  # Assuming EXPECTED_TABLES is defined globally in this file
            assert (
                table_name in tables_in_test_db
            ), f"Table '{table_name}' not found in temporary database."

        # Verify initial plans
        cursor.execute(
            "SELECT name, duration_days, default_amount, display_name FROM plans ORDER BY duration_days;"
        )
        seeded_plans_in_test_db = cursor.fetchall()
        assert len(seeded_plans_in_test_db) == len(
            EXPECTED_INITIAL_PLANS
        ), f"Expected {len(EXPECTED_INITIAL_PLANS)} plans, but found {len(seeded_plans_in_test_db)}."

        for i, expected_plan in enumerate(
            EXPECTED_INITIAL_PLANS
        ):  # Assuming EXPECTED_INITIAL_PLANS is defined
            assert (
                seeded_plans_in_test_db[i][0] == expected_plan[0]
            ), f"Plan name mismatch: Expected '{expected_plan[0]}', got '{seeded_plans_in_test_db[i][0]}'"
            assert (
                seeded_plans_in_test_db[i][1] == expected_plan[1]
            ), f"Plan duration mismatch for '{expected_plan[0]}': Expected {expected_plan[1]}, got {seeded_plans_in_test_db[i][1]}"
            assert (
                seeded_plans_in_test_db[i][2] == expected_plan[2]
            ), f"Plan default_amount mismatch for '{expected_plan[0]}': Expected {expected_plan[2]}, got {seeded_plans_in_test_db[i][2]}"
            assert (
                seeded_plans_in_test_db[i][3] == expected_plan[3]
            ), f"Plan display_name mismatch for '{expected_plan[0]}': Expected {expected_plan[3]}, got {seeded_plans_in_test_db[i][3]}"

    except Exception as e:
        pytest.fail(f"initialize_database test failed: {e}")
    finally:
        if conn:
            conn.close()
        # Cleanup: pytest's tmp_path fixture handles directory cleanup automatically.
        # If test_db_file was outside tmp_path, manual os.remove(test_db_file) and possibly os.rmdir() would be needed.
        # Since we are using tmp_path, this is mostly handled.
        # We explicitly removed test_db_file if it existed before the test.
        # initialize_database creates DB_FILE in dirname(DB_FILE)
        # So if test_db_dir was created by the test, tmp_path cleans it.
        # If test_db_file specifically needs removal and it's not in tmp_path, do it here.
        # For now, relying on tmp_path for cleanup of test_db_dir and its contents.

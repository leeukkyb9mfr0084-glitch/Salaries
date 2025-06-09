import sqlite3
import pytest
from reporter.database import create_database, seed_initial_plans

# Expected table names
EXPECTED_TABLES = ["members", "plans", "transactions"]
EXPECTED_INITIAL_PLANS = [
    ("Monthly - Unrestricted", 30),
    ("3 Months - Unrestricted", 90),
    ("Annual - Unrestricted", 365)
]

def test_create_database_tables():
    """
    Tests if create_database function correctly creates all specified tables.
    """
    db_name = ':memory:'
    conn = None # Initialize conn here to ensure it's available in finally
    try:
        conn = create_database(db_name)  # Create tables and get connection
        assert conn is not None, "create_database(':memory:') should return a connection."
        cursor = conn.cursor()

        # Query sqlite_master table for existing table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        # Assert that all expected tables are present
        for table_name in EXPECTED_TABLES:
            assert table_name in tables, f"Table '{table_name}' not found in database."

        # For good measure, check that no other unexpected tables are present (owned by us)
        # sqlite_sequence is an internal table sqlite creates for AUTOINCREMENT
        non_expected_tables = [t for t in tables if t not in EXPECTED_TABLES and t != 'sqlite_sequence']
        assert not non_expected_tables, f"Unexpected tables found: {non_expected_tables}"

    except sqlite3.Error as e:
        pytest.fail(f"Database operation failed: {e}")
    finally:
        if conn:
            conn.close()

def test_seed_initial_plans():
    """
    Tests if seed_initial_plans correctly inserts the default plans.
    """
    db_name = ':memory:'
    conn = None # Initialize conn here to ensure it's available in finally
    try:
        conn = create_database(db_name)  # Create tables and get connection
        assert conn is not None, "create_database(':memory:') should return a connection."

        # seed_initial_plans expects a connection object
        seed_initial_plans(conn)

        cursor = conn.cursor()
        cursor.execute("SELECT plan_name, duration_days FROM plans ORDER BY duration_days;")
        seeded_plans = cursor.fetchall()

        assert len(seeded_plans) == len(EXPECTED_INITIAL_PLANS), \
            f"Expected {len(EXPECTED_INITIAL_PLANS)} plans, but found {len(seeded_plans)}."

        for i, expected_plan in enumerate(EXPECTED_INITIAL_PLANS):
            assert seeded_plans[i][0] == expected_plan[0], \
                f"Plan name mismatch: Expected '{expected_plan[0]}', got '{seeded_plans[i][0]}'"
            assert seeded_plans[i][1] == expected_plan[1], \
                f"Plan duration mismatch for '{expected_plan[0]}': Expected {expected_plan[1]}, got {seeded_plans[i][1]}"

    except sqlite3.Error as e:
        pytest.fail(f"Database operation failed during seeding or verification: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # This allows running tests directly with `python reporter/tests/test_database.py`
    # though `pytest` is the recommended way.
    pytest.main()

import os
import sqlite3
import unittest
from unittest.mock import patch

from reporter.migrate_historical_data import migrate_historical_data, GC_MEMBERS_CSV, PT_MEMBERS_CSV
from reporter.database import DB_FILE, create_database
from reporter.database_manager import DatabaseManager

# Define paths to test CSV files
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data_migrate")
TEST_GC_CSV = os.path.join(TEST_DATA_DIR, "test_gc_data_for_migration.csv")
TEST_PT_CSV = os.path.join(TEST_DATA_DIR, "test_pt_data_for_migration.csv")
TEST_DB_FILE = os.path.join(TEST_DATA_DIR, "test_migration_data.db")


class TestMigrateHistoricalData(unittest.TestCase):

    def setUp(self):
        # Ensure a clean database for each test
        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)
        # Create a new database for the test
        # Ensure the directory for TEST_DB_FILE exists
        os.makedirs(os.path.dirname(TEST_DB_FILE), exist_ok=True)
        self.conn = create_database(TEST_DB_FILE)
        self.db_mngr = DatabaseManager(connection=self.conn)

    def tearDown(self):
        # Close the connection and remove the test database
        if self.conn:
            self.conn.close()
        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)
        # Remove dummy CSVs if they were created by tests (though here they are static)

    @patch('reporter.migrate_historical_data.DB_FILE', TEST_DB_FILE)
    @patch('reporter.migrate_historical_data.GC_MEMBERS_CSV', TEST_GC_CSV)
    @patch('reporter.migrate_historical_data.PT_MEMBERS_CSV', TEST_PT_CSV)
    def test_migration_with_dummy_data(self):
        # Ensure test CSV files exist
        if not os.path.exists(TEST_GC_CSV):
            self.fail(f"Test GC CSV file not found: {TEST_GC_CSV}")
        if not os.path.exists(TEST_PT_CSV):
            self.fail(f"Test PT CSV file not found: {TEST_PT_CSV}")

        migrate_historical_data()

        # Add assertions here to check the database content
        cursor = self.conn.cursor()

        # Check members table
        cursor.execute("SELECT name, phone, email, join_date FROM members ORDER BY name")
        members_rows = cursor.fetchall()
        members = [tuple(row) for row in members_rows] # Convert rows to tuples

        # Expected members: Test User One, Test User Three, Test User Two (sorted by name)
        self.assertEqual(len(members), 3, f"Expected 3 members, got {len(members)}")

        self.assertEqual(members[0][0], "Test User One")
        self.assertEqual(members[0][1], "1234567890")
        self.assertIsNone(members[0][2]) # Email is not in CSVs, should be None
        self.assertEqual(members[0][3], "2024-01-01") # Earliest: GC start 01/01, PT payment 02/01

        self.assertEqual(members[1][0], "Test User Three")
        self.assertEqual(members[1][1], "1122334455")
        self.assertIsNone(members[1][2])
        self.assertEqual(members[1][3], "2024-02-10") # Only PT payment date

        self.assertEqual(members[2][0], "Test User Two")
        self.assertEqual(members[2][1], "0987654321")
        self.assertIsNone(members[2][2])
        self.assertEqual(members[2][3], "2024-01-15") # Only GC start date


        # Check group_plans table
        cursor.execute("SELECT name, duration_days, default_amount FROM group_plans ORDER BY name") # Changed price to default_amount
        group_plans_rows = cursor.fetchall()
        group_plans = [tuple(row) for row in group_plans_rows] # Convert rows to tuples
        self.assertEqual(len(group_plans), 2, f"Expected 2 group plans, got {len(group_plans)}")
        self.assertEqual(group_plans[0], ("MMA Focus", 90, 2500.0)) # Assertion data is correct
        self.assertEqual(group_plans[1], ("MMA Mastery", 30, 1000.0)) # Assertion data is correct

        # Check group_class_memberships table
        cursor.execute("SELECT id FROM members WHERE phone = '1234567890'") # Test User One
        member_one_id_row = cursor.fetchone()
        self.assertIsNotNone(member_one_id_row, "Test User One not found in members table")
        member_one_id = member_one_id_row[0]

        cursor.execute("SELECT id FROM members WHERE phone = '0987654321'") # Test User Two
        member_two_id_row = cursor.fetchone()
        self.assertIsNotNone(member_two_id_row, "Test User Two not found in members table")
        member_two_id = member_two_id_row[0]

        cursor.execute("SELECT id FROM group_plans WHERE name = 'MMA Mastery' AND duration_days = 30")
        mma_mastery_plan_id_row = cursor.fetchone()
        self.assertIsNotNone(mma_mastery_plan_id_row, "MMA Mastery plan not found")
        mma_mastery_plan_id = mma_mastery_plan_id_row[0]

        cursor.execute("SELECT id FROM group_plans WHERE name = 'MMA Focus' AND duration_days = 90")
        mma_focus_plan_id_row = cursor.fetchone()
        self.assertIsNotNone(mma_focus_plan_id_row, "MMA Focus plan not found")
        mma_focus_plan_id = mma_focus_plan_id_row[0]

        cursor.execute("SELECT member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type FROM group_class_memberships ORDER BY member_id, start_date")
        gc_memberships_rows = cursor.fetchall()
        gc_memberships = [tuple(row) for row in gc_memberships_rows] # Convert rows to tuples
        self.assertEqual(len(gc_memberships), 2, f"Expected 2 GC memberships, got {len(gc_memberships)}")
        # Member One, MMA Mastery
        self.assertEqual(gc_memberships[0], (member_one_id, mma_mastery_plan_id, "2024-01-01", "2024-01-30", 1000.0, "2024-01-01", "New"))
        # Member Two, MMA Focus
        self.assertEqual(gc_memberships[1], (member_two_id, mma_focus_plan_id, "2024-01-15", "2024-04-13", 2500.0, "2024-01-15", "New"))

        # Check pt_memberships table
        cursor.execute("SELECT id FROM members WHERE phone = '1122334455'") # Test User Three
        member_three_id_row = cursor.fetchone()
        self.assertIsNotNone(member_three_id_row, "Test User Three not found in members table")
        member_three_id = member_three_id_row[0]

        cursor.execute("SELECT member_id, purchase_date, amount_paid, sessions_total, sessions_remaining FROM pt_memberships ORDER BY member_id, purchase_date")
        pt_memberships_rows = cursor.fetchall()
        pt_memberships = [tuple(row) for row in pt_memberships_rows] # Convert rows to tuples
        self.assertEqual(len(pt_memberships), 2, f"Expected 2 PT memberships, got {len(pt_memberships)}")
        # Test User One PT data
        self.assertEqual(pt_memberships[0], (member_one_id, "2024-01-02", 500.0, 10, 10))
        # Test User Three PT data
        self.assertEqual(pt_memberships[1], (member_three_id, "2024-02-10", 1500.0, 20, 20))


if __name__ == "__main__":
    # This allows running the tests directly from the command line
    # For example: python -m reporter.tests.test_migrate_historical_data
    # Make sure the reporter directory is in PYTHONPATH or you run from the project root.
    unittest.main(module='reporter.tests.test_migrate_historical_data')

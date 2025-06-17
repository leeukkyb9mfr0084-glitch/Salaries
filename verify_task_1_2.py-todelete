import os
from reporter.main import handle_database_migration
from reporter.database import DB_FILE

print("Running verification for Task 1.2...")
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

handle_database_migration()

if os.path.exists(DB_FILE):
    print(f"SUCCESS: Database file '{DB_FILE}' was created by the handler.")
    os.remove(DB_FILE)
else:
    print(f"FAILURE: Database file '{DB_FILE}' was not created.")

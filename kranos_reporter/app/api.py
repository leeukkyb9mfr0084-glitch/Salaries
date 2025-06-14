import os
from flask import Flask, request, jsonify
# To import DatabaseManager, we need to ensure the kranos_reporter directory is in PYTHONPATH
# or use relative imports carefully. Given typical project structures,
# if api.py is in kranos_reporter/app, and database_manager.py is also in kranos_reporter/app,
# the import would be:
from .database_manager import DatabaseManager
# However, if running this script directly (__name__ == '__main__'), relative imports
# beyond the current package can be problematic.
# For simplicity in this step, and assuming it might be run directly for testing,
# I might adjust this if issues arise, or rely on the execution environment (like a test runner or WSGI server)
# to handlePYTHONPATH correctly.
# A common workaround for direct script execution is to add the project root to sys.path.
import sys
# Assuming the script is in kranos_reporter/app, to access kranos_reporter.app.database_manager
# we might need to go up one level to kranos_reporter, then into app.
# Let's try a direct relative import first, as it's cleaner if the execution context supports it.

# --- Path setup for DatabaseManager ---
# Determine the base directory (kranos_reporter) to construct the DB_PATH
# Assuming this script (api.py) is in kranos_reporter/app/
# So, ../db/kranos_gym.db would be the path from this script's location.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_NAME = "kranos_gym.db"
DB_PATH = os.path.join("db", DB_NAME) # Path relative to BASE_DIR for DatabaseManager

app = Flask(__name__)

# --- DatabaseManager Instantiation ---
# For simplicity, a global instance.
# Consider Flask's application context for more complex scenarios (g object)
# or specific Flask extensions like Flask-SQLAlchemy if using SQLAlchemy.
# The DatabaseManager class itself takes a path relative to the kranos_reporter directory.
try:
    db_manager = DatabaseManager(db_path=DB_PATH)
except Exception as e:
    # If DatabaseManager fails to initialize (e.g., DB file structure issues),
    # the app shouldn't run. Log this critical error.
    print(f"CRITICAL: Failed to initialize DatabaseManager: {e}")
    # In a real app, you might exit or have a fallback. For now, db_manager will be None.
    db_manager = None

@app.teardown_appcontext
def shutdown_session(exception=None):
    """Closes the database connection at the end of the request."""
    if db_manager:
        # db_manager.close() # Assuming DatabaseManager has a close method.
        # The current DatabaseManager opens and closes connection per query via pandas.
        # If it were a persistent connection, this is where you'd close it.
        pass

@app.route('/api/reports/renewal', methods=['GET'])
def get_renewal_report():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503

    try:
        days_ahead_str = request.args.get('days_ahead', default='30')
        if not days_ahead_str.isdigit():
            return jsonify({"error": "Invalid 'days_ahead' parameter. Must be an integer."}), 400
        days_ahead = int(days_ahead_str)
        if days_ahead < 0:
            return jsonify({"error": "'days_ahead' must be a non-negative integer."}), 400

    except ValueError: # Should be caught by isdigit, but as a safeguard.
        return jsonify({"error": "Invalid 'days_ahead' parameter. Must be an integer."}), 400

    try:
        report_df = db_manager.generate_renewal_report(days_ahead)
        if report_df is None:
            # This case might occur if db_manager.generate_renewal_report itself has an issue
            # not caught as a sqlite3.Error (e.g., connection was None initially)
            return jsonify({"error": "Failed to generate renewal report due to an internal issue."}), 500

        # Convert DataFrame to JSON
        # df.to_dict(orient='records') is good for a list of JSON objects
        report_json = report_df.to_dict(orient='records')
        return jsonify(report_json)

    except Exception as e:
        # Log the exception e
        app.logger.error(f"Error generating renewal report: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # For direct execution, ensure Python can find 'database_manager'
    # If kranos_reporter/app/api.py and kranos_reporter/app/database_manager.py,
    # and you run `python api.py` from `kranos_reporter/app/`,
    # `from .database_manager import DatabaseManager` should work.
    # If you run `python kranos_reporter/app/api.py` from the project root,
    # you might need to adjust sys.path or use `python -m kranos_reporter.app.api`

    # Let's adjust sys.path for the __main__ case to make it more robust
    # when running `python kranos_reporter/app/api.py` from project root.
    if BASE_DIR not in sys.path:
         sys.path.insert(0, BASE_DIR)
    # Now, `from app.database_manager import DatabaseManager` should work if previous import failed.
    # However, the initial `from .database_manager import DatabaseManager` is preferred for package use.
    # The current code uses `from .database_manager import DatabaseManager`.
    # If running `python -m kranos_reporter.app.api` this should be fine.
    # If running `python kranos_reporter/app/api.py` directly from root, it might fail.
    # For now, let's assume it's run as a module or PYTHONPATH is set.

    if not db_manager:
        print("Cannot start Flask app: DatabaseManager failed to initialize.")
    else:
        app.run(debug=True, port=5000)

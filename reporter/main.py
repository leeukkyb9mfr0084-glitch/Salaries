import sys
import os
# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Ensure other necessary imports like importlib.util, subprocess are also present at the top.
# The original script already had import os, subprocess, sys, importlib.util
# So the primary change is the sys.path manipulation.

import importlib.util
import subprocess
# os and sys were already imported by the new snippet

from reporter.database import DB_FILE, initialize_database  # Updated database import
from reporter.migrate_historical_data import migrate_historical_data

# Removed old imports:
# import sqlite3 # No longer directly used here
# from reporter.database import create_database, seed_initial_plans # Replaced by initialize_database


def handle_database_migration():
    """
    Checks for a data migration script and runs it if found.
    """
    print("Attempting data migration by calling migrate_historical_data()...")
    try:
        # Call the imported function directly
        migrate_historical_data()
        print("Data migration function executed successfully.")
    except ImportError as e:
        print(
            f"ImportError during migration: {e}. This might mean migrate_historical_data is not defined or importable."
        )
    except Exception as e:
        print(f"An exception occurred while trying to run the migration function: {e}")


def check_and_install_requirements():
    """
    Checks if packages in requirements.txt are installed and installs them if not.
    """
    # Path to the requirements.txt file, make it absolute from script's location
    requirements_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
    )

    if not os.path.exists(requirements_path):
        print(
            f"Warning: '{requirements_path}' not found. Cannot check or install dependencies."
        )
        return

    with open(requirements_path, "r") as f:
        # Read package names, ignore comments and empty lines
        required_packages = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]

    missing_packages = []
    for package in required_packages:
        # Check if the package is installed
        # For packages that have different import names than pip names (e.g., Pillow vs PIL),
        # this might need adjustment or a mapping. For common cases, this works.
        if (
            package.lower() == "customtkinter"
        ):  # customtkinter uses 'customtkinter' as import name
            package_import_name = "customtkinter"
        # Add other mappings here if necessary, e.g., for 'python-dateutil' use 'dateutil'
        # elif package.lower() == "another-pip-name":
        #    package_import_name = "another_import_name"
        else:
            package_import_name = (
                package.split("==")[0].split(">")[0].split("<")[0]
            )  # Get base package name

        spec = importlib.util.find_spec(package_import_name)
        if spec is None:
            missing_packages.append(
                package
            )  # Append the original package name for installation

    if missing_packages:
        print(f"Installing missing packages: {', '.join(missing_packages)}")
        # Use sys.executable to ensure pip from the correct Python environment is used
        python_executable = sys.executable
        try:
            # Run pip to install the missing packages
            # Added --user flag to avoid permission issues in some environments
            subprocess.check_call(
                [python_executable, "-m", "pip", "install", *missing_packages],
                stdout=subprocess.DEVNULL,
            )
            print("Packages installed successfully.")

            # Restart the script to ensure new packages are loaded into memory
            print("Restarting the application...")
            os.execv(python_executable, [python_executable] + sys.argv)

        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to install packages: {e}")
            print(
                "Please install the missing packages manually and restart the application."
            )
            sys.exit(1)


if __name__ == "__main__":
    check_and_install_requirements()  # THIS IS THE NEW LINE

    # Print Python executable and version information
    print(f"Running with Python executable: {sys.executable}")
    print(
        f"Python version: {sys.version.splitlines()[0]}"
    )  # Print only the first line of the version

    # Ensure the data directory exists (DB_FILE imported from database_manager)
    data_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created data directory: {data_dir}")

    # Initialize the database using the consistent function
    initialize_database()
    print(f"Database initialized at: {DB_FILE}")

    handle_database_migration()  # Call the refactored function

    print("Launching Streamlit app...")
    # Construct the absolute path to streamlit_ui/app.py
    # __file__ in main.py is reporter/main.py
    # os.path.dirname(__file__) is reporter/
    # project_root was defined at the top as os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # So, streamlit_app_path should be constructed carefully.
    # The project_root variable should already be available if the first step was applied correctly.
    # If not, it might need to be re-defined or ensure it's in scope.
    # For simplicity, let's re-evaluate path based on __file__ for this specific subprocess call.

    # Path to the streamlit app, relative to the project root
    streamlit_app_module_path = "reporter.streamlit_ui.app"

    # The 'project_root' variable should be defined from the snippet added in step 1.
    # If it's not in the scope of if __name__ == "__main__":, we might need to pass it
    # or re-calculate it. Assuming it is available or can be recalculated.
    # For robustness, let's use the previously defined project_root.
    # The first part of the plan adds:
    # project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # So it should be available in the global scope of main.py

    streamlit_app_path = os.path.join(os.path.dirname(__file__), "streamlit_ui", "app.py")


    # Use sys.executable to ensure we're using the python from the current environment
    # Using -m streamlit run is generally preferred.
    command_to_run = [sys.executable, "-m", "streamlit", "run", streamlit_app_path]

    print(f"Project root for Streamlit app: {project_root}")
    print(f"Running command: {' '.join(command_to_run)}")

    try:
        # subprocess.run is generally preferred over subprocess.call for more control.
        # check=True will raise a CalledProcessError if streamlit returns a non-zero exit code.
        subprocess.run(command_to_run, cwd=project_root, check=True)
    except FileNotFoundError:
        print(f"Error: Streamlit command not found. Ensure Streamlit is installed and in PATH.")
        print(f"Attempted to run from: {sys.executable}")
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit app: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while trying to launch Streamlit: {e}")

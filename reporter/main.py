import sys
import subprocess
import os

# Add the project root to sys.path
# This allows 'from reporter.database...' to work correctly after restart
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import importlib.util
import flet as ft # Added Flet import
from reporter.database import initialize_database, DB_FILE # Updated database import
from reporter.gui import main as start_flet_gui # Import main from the new gui.py

# Removed old imports:
# import sqlite3 # No longer directly used here
# from reporter.database import create_database, seed_initial_plans # Replaced by initialize_database

def check_and_install_requirements():
    """
    Checks if packages in requirements.txt are installed and installs them if not.
    """
    # Path to the requirements.txt file, make it absolute from script's location
    requirements_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'requirements.txt'))

    if not os.path.exists(requirements_path):
        print(f"Warning: '{requirements_path}' not found. Cannot check or install dependencies.")
        return

    with open(requirements_path, 'r') as f:
        # Read package names, ignore comments and empty lines
        required_packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    missing_packages = []
    for package in required_packages:
        # Check if the package is installed
        # For packages that have different import names than pip names (e.g., Pillow vs PIL),
        # this might need adjustment or a mapping. For common cases, this works.
        if package.lower() == "customtkinter": # customtkinter uses 'customtkinter' as import name
            package_import_name = "customtkinter"
        # Add other mappings here if necessary, e.g., for 'python-dateutil' use 'dateutil'
        # elif package.lower() == "another-pip-name":
        #    package_import_name = "another_import_name"
        else:
            package_import_name = package.split('==')[0].split('>')[0].split('<')[0] # Get base package name

        spec = importlib.util.find_spec(package_import_name)
        if spec is None:
            missing_packages.append(package) # Append the original package name for installation

    if missing_packages:
        print(f"Installing missing packages: {', '.join(missing_packages)}")
        # Use sys.executable to ensure pip from the correct Python environment is used
        python_executable = sys.executable
        try:
            # Run pip to install the missing packages
            # Added --user flag to avoid permission issues in some environments
            subprocess.check_call([python_executable, '-m', 'pip', 'install', *missing_packages], stdout=subprocess.DEVNULL)
            print("Packages installed successfully.")

            # Restart the script to ensure new packages are loaded into memory
            print("Restarting the application...")
            os.execv(python_executable, [python_executable] + sys.argv)

        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to install packages: {e}")
            print("Please install the missing packages manually and restart the application.")
            sys.exit(1)

if __name__ == '__main__':
    check_and_install_requirements() # THIS IS THE NEW LINE

    # Print Python executable and version information
    print(f"Running with Python executable: {sys.executable}")
    print(f"Python version: {sys.version.splitlines()[0]}") # Print only the first line of the version

    # Ensure the data directory exists (DB_FILE imported from database_manager)
    data_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created data directory: {data_dir}")

    # Initialize the database using the consistent function
    initialize_database()
    print(f"Database initialized at: {DB_FILE}")

    # Start the Flet application
    print("Starting Flet application...")
    ft.app(target=start_flet_gui)

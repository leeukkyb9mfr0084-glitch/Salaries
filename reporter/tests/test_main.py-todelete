import os
import sys
import subprocess
import pytest  # Using pytest for consistency if other tests use it, can also use unittest.mock
from unittest.mock import patch, MagicMock

# Add project root to sys.path to allow direct import of reporter.main
# This might be needed if running pytest from the root or if PYTHONPATH isn't set up
# Adjust path as necessary based on your test execution environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Now we can import the function from reporter.main
try:
    from reporter.main import handle_database_migration
except ImportError as e:
    # This might happen if the path isn't set correctly or if there's an issue in main.py
    # For testing purposes, we'll raise a more informative error.
    raise ImportError(
        f"Could not import handle_database_migration from reporter.main. Error: {e}. Check sys.path and reporter/main.py."
    )


# Determine the expected path to migrate_data.py relative to main.py
# Assuming main.py is in 'reporter/' directory.
# __file__ for test_main.py is reporter/tests/test_main.py
# main_py_dir would be os.path.dirname(reporter.main.__file__) if reporter.main could be imported to get __file__
# For now, let's assume reporter.main.__file__ would be <some_path>/reporter/main.py
# So, os.path.dirname(reporter.main.__file__) is <some_path>/reporter
# And the migrate_script_path is <some_path>/reporter/migrate_data.py

# To robustly get the directory of main.py without importing it directly for its __file__ at module level:
# We are testing the *function* handle_database_migration, which itself uses __file__ (referring to main.py)
# So, the patches need to target 'reporter.main.os.path.exists', etc.
# The argument to os.path.exists in the original function is:
# os.path.join(os.path.dirname(__file__), 'migrate_data.py') where __file__ is main.py's path.

# We need to determine what that path would be for assertion.
# Let's assume the test runner is smart enough or that the path for `reporter.main.__file__`
# will be correctly resolved when the function `handle_database_migration` is called.
# The key is that `patch` targets names in the module where they are looked up.
# `handle_database_migration` looks up `os.path.exists` in `reporter.main`'s scope.

EXPECTED_MIGRATE_SCRIPT_PATH_IN_MAIN = (
    "reporter/migrate_data.py"  # This needs to be accurate based on main.py's __file__
)


@patch("reporter.main.subprocess.run")
@patch("reporter.main.os.path.exists")
def test_migration_runs_if_script_exists(mock_exists, mock_run):
    """
    Tests that the migration script is run if it exists and returns success.
    """
    # Dynamically determine the expected path as it would be calculated in handle_database_migration
    # This assumes reporter.main module can be found and has a __file__ attribute.
    # This part is tricky because reporter.main might not be fully imported if it has top-level code for Flet.
    # For the purpose of this test, we'll assume that when handle_database_migration is called,
    # os.path.dirname(__file__) within that function correctly points to the 'reporter' directory.
    # The assertion for mock_exists.assert_called_with(...) will verify this.

    mock_exists.return_value = True
    mock_run.return_value = MagicMock(
        returncode=0, stdout="Migration successful", stderr=""
    )

    handle_database_migration()

    # Assert that os.path.exists was called correctly
    # The path used inside handle_database_migration is os.path.join(os.path.dirname(__file__), 'migrate_data.py')
    # We need to know what os.path.dirname(__file__) will be from within reporter.main module.
    # If main.py is in <root>/reporter/main.py, then dirname is <root>/reporter.
    # For now, we trust the call within the function and check that it was called.
    # A more robust way would be to import reporter.main and get its __file__ attribute.
    # However, since we are patching os.path.exists *within* reporter.main, its internal call is what matters.
    mock_exists.assert_called_once()
    # The first argument of the first call to mock_exists:
    called_path_for_exists = mock_exists.call_args[0][0]
    assert called_path_for_exists.endswith(
        "reporter/migrate_data.py"
    ), f"os.path.exists called with unexpected path: {called_path_for_exists}"

    mock_run.assert_called_once_with(
        [sys.executable, "-m", "reporter.migrate_data"],
        capture_output=True,
        text=True,
        check=False,
    )


@patch("reporter.main.subprocess.run")
@patch("reporter.main.os.path.exists")
def test_migration_handles_failure(mock_exists, mock_run, capsys):
    """
    Tests that a failure in the migration script (non-zero return code) is handled.
    """
    mock_exists.return_value = True
    mock_run.return_value = MagicMock(
        returncode=1, stdout="Output before error", stderr="Migration error details"
    )

    handle_database_migration()

    mock_exists.assert_called_once()
    called_path_for_exists = mock_exists.call_args[0][0]
    assert called_path_for_exists.endswith("reporter/migrate_data.py")

    mock_run.assert_called_once_with(
        [sys.executable, "-m", "reporter.migrate_data"],
        capture_output=True,
        text=True,
        check=False,
    )

    # Check if error messages were printed (optional, but good for CLI tools)
    captured = capsys.readouterr()
    assert "Data migration script failed with error" in captured.out
    assert "Migration error details" in captured.out
    assert "Output before error" in captured.out  # stdout should also be printed


@patch("reporter.main.subprocess.run")
@patch("reporter.main.os.path.exists")
def test_migration_skipped_if_script_missing(mock_exists, mock_run, capsys):
    """
    Tests that the migration script is skipped if it does not exist.
    """
    mock_exists.return_value = False

    handle_database_migration()

    mock_exists.assert_called_once()
    called_path_for_exists = mock_exists.call_args[0][0]
    assert called_path_for_exists.endswith("reporter/migrate_data.py")

    mock_run.assert_not_called()

    # Check if skipping message was printed
    captured = capsys.readouterr()
    assert "not found. Skipping migration" in captured.out


# To run these tests with pytest, navigate to the directory containing 'reporter'
# and run `pytest`. Ensure __init__.py files are in 'reporter' and 'reporter/tests'.
# Example: if project root is 'my_project/', and tests are in 'my_project/reporter/tests/',
# run `pytest` from 'my_project/'.
# Make sure `PYTHONPATH` includes your project root or use editable install (`pip install -e .`).
# The sys.path.insert above helps, but proper packaging or PYTHONPATH is more robust.
# The test file should be named test_*.py or *_test.py for pytest to discover it.
# This file is named test_main.py, so it should be discovered.
# Adding a simple `if __name__ == '__main__': pytest.main()` is also possible for direct run.
if __name__ == "__main__":
    pytest.main(
        [__file__]
    )  # Allows running this test file directly using pytest engine

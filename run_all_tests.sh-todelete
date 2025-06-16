#!/bin/bash

# Ensure script exits on error
set -e

# Initialize LOG_FILE for test results
LOG_FILE="test_results.log"
# Clear the log file at the beginning of the script run
rm -f ${LOG_FILE}
echo "Logging results to ${LOG_FILE}" # Announce log file at the very start

echo "Installing dependencies..." | tee -a ${LOG_FILE}

# Install python3.10-tk specifically
echo "Installing python3.10-tk..." | tee -a ${LOG_FILE}
sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3.10-tk

# Install customtkinter and other dependencies
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt --user
else
  pip install customtkinter --user
fi

# Add .local/bin to PATH if it's not already there, for scripts installed by pip --user
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
    echo "Updated PATH: $PATH"
fi

echo "Dependencies installed."

echo "Setting up Xvfb for headless GUI tests..."
sudo apt-get install -y xvfb

# Clean up previous Xvfb lock file and processes
echo "Cleaning up any existing Xvfb processes and lock files..."
sudo rm -f /tmp/.X99-lock
# Kill any processes that might be listening on the X11 port for display 99
# Use pkill to find processes associated with Xvfb display 99
sudo pkill -f "Xvfb :99" || echo "No existing Xvfb process found for display 99."
sleep 1 # Give a moment for processes to terminate

export DISPLAY=:99
echo "Starting Xvfb on display $DISPLAY..."
Xvfb $DISPLAY -screen 0 1280x1024x24 &
XVFB_PID=$!
# Wait a bit for Xvfb to start
sleep 3
# Check if Xvfb started successfully
if ! ps -p $XVFB_PID > /dev/null; then
    echo "Xvfb failed to start. Check Xorg.0.log or similar for errors."
    # Attempt to read Xorg log if it exists for more details
    if [ -f "/var/log/Xorg.0.log" ]; then # Path might vary
        echo "Contents of /var/log/Xorg.0.log:"
        cat /var/log/Xorg.0.log >> ${LOG_FILE}
    fi
    exit 1
fi
echo "Xvfb started with PID $XVFB_PID."

echo "Directly testing tkinter import with /usr/bin/python3..." | tee -a ${LOG_FILE}
if /usr/bin/python3 -c "import tkinter; print('tkinter imported successfully')" >> ${LOG_FILE} 2>&1; then
    echo "Direct tkinter import successful." | tee -a ${LOG_FILE}
else
    echo "CRITICAL: Direct tkinter import FAILED." | tee -a ${LOG_FILE}
    echo "Python version: $(/usr/bin/python3 --version)" | tee -a ${LOG_FILE}
    echo "Sys Path: " >> ${LOG_FILE}
    /usr/bin/python3 -c "import sys; print(sys.path)" >> ${LOG_FILE} 2>&1
    echo "Exiting due to tkinter import failure." | tee -a ${LOG_FILE}
    exit 1
fi

echo "Starting test execution..."

# Note: Old log file deletion for pattern 'test_results_*.log' is removed.
# LOG_FILE is now consistently 'test_results.log' and cleared at the start.

echo "
--- Running Pytest Unit & Integration Tests ---" | tee -a ${LOG_FILE}
# Ensure pytest runs from the project root so 'reporter.tests' is found.
# Add -v for verbose output, and --tb=short for shorter tracebacks.
# Explicitly use /usr/bin/python3 to ensure system tkinter is accessible
# All output (stdout and stderr) is redirected to LOG_FILE, overwriting it.
/usr/bin/python3 -m pytest -v --tb=short reporter/tests/ > ${LOG_FILE} 2>&1
PYTEST_EXIT_CODE=$? # Capture pytest exit code

echo "Pytest execution finished." | tee -a ${LOG_FILE} # Also log this message

# 4. Run simulation scripts and append output to log
echo "
--- Running UI Flow Simulation Tests ---" | tee -a ${LOG_FILE}

SIMULATION_SCRIPTS_DIR="reporter/simulations"
SIMULATION_SUCCESS=true # Flag to track overall simulation success

# Check if simulation directory exists
if [ -d "${SIMULATION_SCRIPTS_DIR}" ]; then
    # This loop runs all python scripts starting with 'simulate_' in the ${SIMULATION_SCRIPTS_DIR}
    for script in ${SIMULATION_SCRIPTS_DIR}/simulate_*.py; do
        if [ -f "${script}" ]; then
            echo "
--- Running simulation: ${script} ---" | tee -a ${LOG_FILE}
            python "${script}" >> ${LOG_FILE} 2>&1
            SCRIPT_EXIT_CODE=$?
            if [ ${SCRIPT_EXIT_CODE} -ne 0 ]; then
                echo "ERROR: Simulation script ${script} failed with exit code ${SCRIPT_EXIT_CODE}." | tee -a ${LOG_FILE}
                SIMULATION_SUCCESS=false # Mark failure
            else
                echo "Simulation ${script} completed." | tee -a ${LOG_FILE}
            fi
        else
            echo "Warning: No script found matching ${script}" | tee -a ${LOG_FILE}
        fi
    done
else
    echo "Warning: Simulation directory ${SIMULATION_SCRIPTS_DIR} not found." | tee -a ${LOG_FILE}
    SIMULATION_SUCCESS=false # Consider this a failure if dir is missing
fi

echo "UI Flow Simulation tests execution finished."

# 5. Final status
echo "
--- Test Execution Summary ---" | tee -a ${LOG_FILE}
if [ ${PYTEST_EXIT_CODE} -eq 0 ] && [ "${SIMULATION_SUCCESS}" = true ]; then
    echo "All tests and simulations passed successfully." | tee -a ${LOG_FILE}
    # Echo final success message to stdout directly, not just log file
    echo "SUCCESS: All tests passed."
else
    echo "One or more tests or simulations failed. Please check ${LOG_FILE} for details." | tee -a ${LOG_FILE}
    # Echo final failure message to stdout directly, not just log file
    echo "FAILURE: Some tests failed. Check ${LOG_FILE} for details."
fi

echo "Test execution complete. See ${LOG_FILE} for details." | tee -a ${LOG_FILE} # Log this too

# Clean up Xvfb
echo "Stopping Xvfb..."
kill $XVFB_PID || echo "Xvfb already stopped or failed to stop."

#!/bin/bash

echo "Starting test execution..."

# 1. Delete old log files
# Use find to delete only files matching the pattern to avoid deleting other .log files
find . -maxdepth 1 -name 'test_results_*.log' -delete
echo "Old test_results_*.log files deleted."

# 2. Set up a new timestamped log file
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="test_results_${TIMESTAMP}.log"

echo "Logging results to ${LOG_FILE}"

# 3. Run pytest and append output to log
echo "
--- Running Pytest Unit & Integration Tests ---" | tee -a ${LOG_FILE}
# Ensure pytest runs from the project root so 'reporter.tests' is found.
# Add -v for verbose output, and --tb=short for shorter tracebacks.
pytest -v --tb=short reporter/tests/ >> ${LOG_FILE} 2>&1
PYTEST_EXIT_CODE=$? # Capture pytest exit code

echo "Pytest execution finished."

# 4. Run simulation scripts and append output to log
echo "
--- Running UI Flow Simulation Tests ---" | tee -a ${LOG_FILE}

SIMULATION_SCRIPTS_DIR="reporter/simulations"
SIMULATION_SUCCESS=true # Flag to track overall simulation success

# Check if simulation directory exists
if [ -d "${SIMULATION_SCRIPTS_DIR}" ]; then
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
    echo "SUCCESS: All tests passed."
else
    echo "One or more tests or simulations failed. Please check ${LOG_FILE} for details." | tee -a ${LOG_FILE}
    echo "FAILURE: Some tests failed."
fi

echo "Test execution complete. See ${LOG_FILE} for details."

#!/bin/bash

# Define the log file
LOG_FILE="test_results.log"

echo "--- Starting Validation: $(date) ---" > $LOG_FILE
echo "Deleting old test logs..." | tee -a $LOG_FILE

# Run the full pytest suite and log all output
echo "
--- Running Automated Tests ---" >> $LOG_FILE
python3 -m pytest >> $LOG_FILE 2>&1

# Capture the exit code of pytest
PYTEST_EXIT_CODE=$?

echo "
--- Pytest finished with exit code: $PYTEST_EXIT_CODE ---" >> $LOG_FILE
echo "Test results have been saved to $LOG_FILE"

# Check if the app launches
echo "
--- Checking if application launches ---" >> $LOG_FILE
python3 -m reporter.main >> $LOG_FILE 2>&1 &
APP_PID=$!
sleep 5 # Wait 5 seconds to see if it crashes

# Check if the process is still running
if ps -p $APP_PID > /dev/null; then
   echo "Application launched successfully." | tee -a $LOG_FILE
   kill $APP_PID
else
   echo "Application failed to launch. Check $LOG_FILE for errors." | tee -a $LOG_FILE
fi

echo "
--- Validation Complete ---" >> $LOG_FILE

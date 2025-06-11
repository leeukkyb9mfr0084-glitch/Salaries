#!/bin/bash

LOG_FILE="test_run_log.txt"

# Clean up old logs
echo "Deleting old log file..."
rm -f $LOG_FILE

# Install dependencies
echo "Installing dependencies..." | tee -a $LOG_FILE
pip install flet pandas openpyxl &>> $LOG_FILE
if [ $? -ne 0 ]; then
    echo "Dependency installation failed. Check $LOG_FILE for details." | tee -a $LOG_FILE
    exit 1
fi
echo "Dependencies installed successfully." | tee -a $LOG_FILE

# Run the full test suite and log the output
echo "Running pytest suite..."
pytest &>> $LOG_FILE

# Check if tests failed
if [ $? -ne 0 ]; then
    echo "Pytest suite failed. Check $LOG_FILE for details."
    exit 1
fi

echo "Pytest suite passed successfully." | tee -a $LOG_FILE

# Check if the application launches
echo "Attempting to launch the application..." | tee -a $LOG_FILE
python -m reporter.main &
APP_PID=$!
sleep 5 # Wait for the app to initialize

if ps -p $APP_PID > /dev/null; then
    echo "Application launch successful." | tee -a $LOG_FILE
    kill $APP_PID
else
    echo "Application failed to launch. Check $LOG_FILE." | tee -a $LOG_FILE
    exit 1
fi

echo "Validation complete."

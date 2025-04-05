#!/bin/bash

# Run tests with pytest
echo "Running tests for Team Logo Combiner..."

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "pytest not found. Installing required packages..."
    pip install -r requirements.txt
fi

# Run the tests
pytest

# Check the exit code
if [ $? -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests failed. Please check the output above for details."
    exit 1
fi

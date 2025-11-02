#!/bin/bash

# Go to root folder
cd "$(dirname "$0")"/.. || exit

# Check for print statements
echo "Checking for print statements..."
remove-print-statements --dry-run --verbose ./*/*.py

# If there are issues, exit with non-zero status
if ! remove-print-statements --dry-run --verbose ./*/*.py; then
  echo "You have print statements in your code, please remove them."
  exit 1
fi

echo "No issues with print statements."
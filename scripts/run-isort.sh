#!/bin/bash

# Go to root folder
cd "$(dirname "$0")"/.. || exit

# Check for issues
echo "Checking for issues with Python isort..."
isort --check .

# If there are issues, fix them
if ! isort .; then
  echo "Fixing issues with Python isort..."
  isort .
fi

echo "No issues with Python isort."

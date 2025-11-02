#!/bin/sh

# Go to root folder
cd "$(dirname "$0")"/.. || exit

# Check for issues
echo "Checking for issues with Python Black..."
black --check .

# If there are issues, fix them
if ! black .; then
  echo "Fixing issues with Python Black..."
  black .
fi

echo "No issues with Python Black."

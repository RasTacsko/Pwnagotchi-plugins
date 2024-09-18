#!/bin/bash

# Variables
REPO_URL="https://github.com/RasTacsko/pwnagotchi_dipslayWIP.git"
CLONE_DIR="/tmp/DisplayDrivers"   # Temporary directory to clone the repository
TARGET_FILE="/usr/local/lib/python3.11/dist-packages/pwnagotchi/utils.py"  # The file to overwrite
TARGET_DIR="/usr/local/lib/python3.11/dist-packages/pwnagotchi/ui/"    # The directory to overwrite
SOURCE_FILE="/pwnagotchi/utils.py"     # Source file from the repo
SOURCE_DIR="/pwnagotchi/ui/"       # Source folder from the repo

# Clone the repository
echo "Cloning repository..."
git clone "$REPO_URL" "$CLONE_DIR"

# Check if clone was successful
if [ $? -ne 0 ]; then
    echo "Failed to clone repository!"
    exit 1
fi

# Copy the file and folder to the target location
echo "Copying file and folder to target location..."

# Copy the file
sudo cp -f "$CLONE_DIR/$SOURCE_FILE" "$TARGET_FILE"

# Copy the folder (with overwriting existing content)
sudo cp -rf "$CLONE_DIR/$SOURCE_DIR" "$TARGET_DIR"

# Clean up the cloned repo
echo "Cleaning up..."
rm -rf "$CLONE_DIR"

echo "Done! File and folder have been copied and overwritten."

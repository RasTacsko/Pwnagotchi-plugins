#!/bin/bash
# Exit immediately if any command fails
set -e

# Variables
REPO_URL="https://github.com/RasTacsko/pwnagotchi_dipslayWIP.git"
CLONE_DIR="/tmp/DisplayDrivers"   # Temporary directory to clone the repository
SOURCE_FILE="pwnagotchi/utils.py"  # Source file from the repo (relative to CLONE_DIR)
SOURCE_DIR="pwnagotchi/ui/"        # Source folder from the repo (relative to CLONE_DIR)

# Prompt for OS architecture
echo "Is this system 32-bit or 64-bit?"
read -p "(Enter 32 or 64): " ARCH

# Set target paths based on user input
if [ "$ARCH" == "32" ]; then
    TARGET_FILE="/usr/local/lib/python3.9/dist-packages/pwnagotchi/utils.py"  # The file to overwrite
    TARGET_DIR="/usr/local/lib/python3.9/dist-packages/pwnagotchi/ui/"        # The directory to overwrite
elif [ "$ARCH" == "64" ]; then
    TARGET_FILE="/usr/local/lib/python3.11/dist-packages/pwnagotchi/utils.py" # The file to overwrite
    TARGET_DIR="/usr/local/lib/python3.11/dist-packages/pwnagotchi/ui/"       # The directory to overwrite
else
    echo "Invalid input. Please enter 32 or 64."
    exit 1
fi

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

# Copy the contents of the folder (without copying the folder itself)
sudo cp -rf "$CLONE_DIR/$SOURCE_DIR"* "$TARGET_DIR"

# Clean up the cloned repo
echo "Cleaning up..."
rm -rf "$CLONE_DIR"

# Ensure the script exits successfully
echo "Done! File and folder have been copied and overwritten."
exit 0
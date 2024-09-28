#!/bin/bash

# Exit immediately if any command fails
set -e

# Backup the sshd_config file before modifying
SSH_CONFIG="/etc/ssh/sshd_config"
echo "Creating backup of sshd_config..."
sudo cp "$SSH_CONFIG" "${SSH_CONFIG}.bak"

# Modify the sshd_config to enable root login
echo "Modifying sshd_config to allow root login..."
sudo sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin yes/' "$SSH_CONFIG"

# Restart the SSH service to apply changes
echo "Restarting SSH service..."
sudo /etc/init.d/ssh restart

# Check if root password is set, and prompt the user to set one if not
ROOT_PASSWD_STATUS=$(sudo passwd -S root | awk '{print $2}')
if [ "$ROOT_PASSWD_STATUS" != "P" ]; then
    echo "Root password is not set or locked. Setting a root password now..."
    sudo passwd root
else
    echo "Root password is already set."
fi

# Script complete
echo "Root login via SSH has been enabled and the SSH service restarted."

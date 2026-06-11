#!/bin/bash

# Copyright 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This script can be used to set up the Btrfs filesystem on Linux in order to
# create low-overhead "workspaces" (aka. "workdirs") to develop git changes
# in without creating multiple full git checkouts. See also
# depot_tools/gclient-new-workdir.py to pick up where this setup script leaves
# off.
#
# Example invocation:
#   depot_tools/setup_btrfs_loop.sh

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
IMAGE_SIZE="1T"                 # Size of the Btrfs image file (e.g., 500G, 1T, 2T)
IMAGE_DIR="/var/lib/btrfs"
IMAGE_FILE="${IMAGE_DIR}/btrfs.img"
MOUNT_POINT="/usr/local/btrfs_mount"
FSTAB_OPTS="loop,nofail,compress=zstd:3,discard=async,user_subvol_rm_allowed"

echo "--- Starting Btrfs file-backed filesystem setup ---"

# --- Safety Checks ---
# Check if the mount point is already in use
if mountpoint -q "${MOUNT_POINT}"; then
  echo "ERROR: ${MOUNT_POINT} is already a mount point."
  mount | grep "${MOUNT_POINT}"
  echo "Please unmount it or choose a different MOUNT_POINT in the script. Aborting."
  exit 1
fi

# Check if running as root, sudo will be used for most commands
if [[ $EUID -eq 0 ]]; then
   echo "ERROR: This script should not be run as root, but it will use sudo."
   exit 1
fi

# --- 1. Create Directories ---
echo "Creating directories (if they don't exist)..."
sudo mkdir -p "${IMAGE_DIR}"
sudo mkdir -p "${MOUNT_POINT}"
echo "Directories ensured: ${IMAGE_DIR}, ${MOUNT_POINT}"

# --- 2. Create or Confirm Sparse Image File ---
if [ -f "${IMAGE_FILE}" ]; then
  echo "WARNING: Image file ${IMAGE_FILE} already exists."
  read -p "Do you want to reformat ${IMAGE_FILE}? (THIS WILL DELETE ITS CONTENTS) (y/N): " confirm
  if [[ ! "$confirm" =~ ^[yY]$ ]]; then
      echo "Aborting without changes to the existing image file."
      exit 1
  fi
  echo "Proceeding to reformat ${IMAGE_FILE}."
else
  echo "Creating ${IMAGE_SIZE} sparse image file: ${IMAGE_FILE}..."
  sudo truncate -s "${IMAGE_SIZE}" "${IMAGE_FILE}"
  echo "Image file created."
fi

# --- 3. Format the Image File with Btrfs ---
echo "Formatting ${IMAGE_FILE} with Btrfs..."
sudo mkfs.btrfs -f -L chromium_btrfs "${IMAGE_FILE}"
echo "Btrfs filesystem created."

# --- 4. Update /etc/fstab ---
FSTAB_LINE="${IMAGE_FILE} ${MOUNT_POINT} btrfs ${FSTAB_OPTS} 0 0"
echo "Checking /etc/fstab for ${MOUNT_POINT}..."

if grep -qE " ${MOUNT_POINT} " /etc/fstab; then
  echo "Found an existing entry for ${MOUNT_POINT} in /etc/fstab."
  if grep -qF "${FSTAB_LINE}" /etc/fstab; then
    echo "The existing entry matches the desired configuration."
  else
    echo "WARNING: The existing fstab entry for ${MOUNT_POINT} differs."
    echo "  Yours: $(grep -E " ${MOUNT_POINT} " /etc/fstab)"
    echo "  Script would add: ${FSTAB_LINE}"
    echo "Please check /etc/fstab manually to ensure the correct configuration."
    read -p "Do you want to replace the existing entry? (y/N): " replace_fstab
    if [[ "$replace_fstab" =~ ^[yY]$ ]]; then
        echo "Backing up /etc/fstab to /etc/fstab.bak..."
        sudo cp /etc/fstab /etc/fstab.bak
        echo "Removing old entry and adding new one..."
        sudo sed -i -E "\| ${MOUNT_POINT} |d" /etc/fstab
        echo "${FSTAB_LINE}" | sudo tee -a /etc/fstab
        echo "Fstab entry updated."
    else
        echo "Leaving fstab as is."
    fi
  fi
else
  echo "Adding new entry to /etc/fstab:"
  echo "${FSTAB_LINE}" | sudo tee -a /etc/fstab
  echo "Fstab entry added."
fi

# --- 5. Mount the Filesystem ---
echo "Reloading systemd manager configuration..."
sudo systemctl daemon-reload
echo "Mounting ${MOUNT_POINT}..."
sudo mount "${MOUNT_POINT}"

# --- 6. Set Ownership ---
echo "Setting ownership of ${MOUNT_POINT} to $(whoami)..."
sudo chown $(whoami): "${MOUNT_POINT}"

# --- 7. Verification ---
echo "--- Verification ---"
if mount | grep -q "${MOUNT_POINT}"; then
  echo "SUCCESS: Filesystem is mounted!"
  mount | grep "${MOUNT_POINT}"
  echo ""
  df -hT "${MOUNT_POINT}"
  echo ""
  echo "Your Btrfs filesystem is ready at ${MOUNT_POINT}"
  echo "You can now 'cd ${MOUNT_POINT}' to use it."
else
  echo "ERROR: Mounting failed. Please check the output, logs, and /etc/fstab."
  exit 1
fi

echo "--- Btrfs Setup Complete ---"
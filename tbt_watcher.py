#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Monitor Thunderbolt dock connections by reading sysfs attributes."""

import pyudev
import subprocess
import os
import time

DSC_SCRIPT_PATH = "/opt/tbt-watcher/dsc.py"

# Keywords expected in vendor_name and device_name
EXPECTED_KEYWORDS = ["lenovo", "thinkpad", "dock"]

def call_dsc_script():
    if not os.path.isfile(DSC_SCRIPT_PATH):
        print(f"DSC script not found at {DSC_SCRIPT_PATH}, skipping.")
        return
    print(f"Calling DSC script: {DSC_SCRIPT_PATH}")
    result = subprocess.run(
        ["python3", DSC_SCRIPT_PATH],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("DSC script completed successfully:")
        print(result.stdout)
    else:
        print("DSC script failed:")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

def read_sysfs_property(device_sys_path, property_name):
    """Helper to read a property file from sysfs."""
    prop_path = os.path.join(device_sys_path, property_name)
    try:
        with open(prop_path, 'r') as f:
            value = f.read().strip()
            return value
    except Exception:
        return ''

def is_target_dock(device_sys_path):
    """Detect if a Thunderbolt device is the target Lenovo dock."""
    vendor = read_sysfs_property(device_sys_path, "vendor_name").lower()
    model = read_sysfs_property(device_sys_path, "device_name").lower()
    print(f"○ sysfs read: vendor_name='{vendor}', device_name='{model}'")

    combined = f"{vendor} {model}"
    return all(keyword in combined for keyword in EXPECTED_KEYWORDS)

def monitor_tbt_events():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by('thunderbolt')

    print("Listening for Thunderbolt device events...")
    for device in iter(monitor.poll, None):
        subsystem = device.subsystem or "unknown"
        action = device.action or "unknown"
        devpath = device.sys_path or "unknown"
        print(f"Event: action={action}, subsystem={subsystem}, sys_path={devpath}")

        if action == 'add':
            if is_target_dock(devpath):
                print("Target Lenovo ThinkPad Dock detected!")
                print("Waiting 5 seconds for monitors to enumerate...")
                time.sleep(5)
                call_dsc_script()
            else:
                print("○ Device is not the target dock. Ignoring.")


if __name__ == "__main__":
    try:
        monitor_tbt_events()
    except KeyboardInterrupt:
        print("\nExiting monitor_tbt.py...")

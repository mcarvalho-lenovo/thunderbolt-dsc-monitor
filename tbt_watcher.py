"""
monitor_tbt.py

Listens for Thunderbolt hot-plug (add/remove) events using pyudev.
When a TBT device is plugged in, it calls the DSC script.
"""
import pyudev
import subprocess
import os

DSC_SCRIPT_PATH = "/opt/tbt-watcher/dsc.py"

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

def monitor_tbt_events():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by('thunderbolt')
    print("Listening for Thunderbolt device events...")
    for device in iter(monitor.poll, None):
        if device.action == 'add':
            print(f"TBT Device plugged in: {device}")
            call_dsc_script()
        elif device.action == 'remove':
            print(f"TBT Device unplugged: {device}")

if __name__ == "__main__":
    try:
        monitor_tbt_events()
    except KeyboardInterrupt:
        print("\nExiting tbt_watcher.py...")

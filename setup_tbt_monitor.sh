
---

## 2. `setup_tbt_monitor.sh`

```bash
#!/usr/bin/env bash
#
# setup_tbt_monitor.sh
#
# Installs Python dependencies, sets up a Python script to monitor
# Thunderbolt hot-plug events, installs a systemd service to run
# the script continuously, and packages the files for download.

set -e

SERVICE_NAME="tbt-monitor"
PY_SCRIPT_NAME="monitor_tbt.py"
UNIT_FILE="${SERVICE_NAME}.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run this script as root (e.g., sudo ./setup_tbt_monitor.sh)."
  exit 1
fi

echo "==> Installing Python3, pip, and pyudev..."
apt-get update -y
apt-get install -y python3 python3-pip
pip3 install pyudev

INSTALL_DIR="/opt/tbt-monitor"
mkdir -p "$INSTALL_DIR"

# Create monitor_tbt.py
cat << 'EOF' > "${INSTALL_DIR}/${PY_SCRIPT_NAME}"
#!/usr/bin/env python3
"""
monitor_tbt.py

Listens for Thunderbolt hot-plug (add/remove) events using pyudev.
When a TBT device is plugged in, it calls the DSC script.
"""
import pyudev
import subprocess
import os

# Update this path if dsc.py is installed elsewhere
DSC_SCRIPT_PATH = "/opt/tbt-monitor/dsc.py"

def call_dsc_script():
    """
    Call the external DSC script that toggles DSC on eDP panels at DPCD 0x160.
    """
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
        print("\nExiting monitor_tbt.py...")
EOF

chmod +x "${INSTALL_DIR}/${PY_SCRIPT_NAME}"

# Copy (or create) the DSC script into /opt/tbt-monitor
cat << 'EOF' > "${INSTALL_DIR}/dsc.py"
#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
dsc.py

Toggles DSC at DPCD address 0x160 on eDP panels via drm_dp_aux_dev.
If the value is 0, writes 1; if it's already 1, does nothing.
"""
import sys
import os

DSC_SUPPORT = {
    0: "DSC Off",
    1: "DSC On",
}

def decode_dsc(f):
    f.seek(0x160)
    data = f.read(1)
    if len(data) < 1:
        print("Could not read DPCD[0x160].")
        return None
    val = data[0]
    desc = DSC_SUPPORT.get(val, f"Unknown (0x{val:02X})")
    print(f"○ Current DSC value: {desc} (0x{val:02X})")
    return val

def enable_dsc_if_off(f):
    current_val = decode_dsc(f)
    if current_val is None:
        return
    if current_val == 0:
        print("DSC is off; enabling DSC by writing 1 to DPCD[0x160].")
        f.seek(0x160)
        f.write(bytes([1]))
        print("○ DSC write complete.")
    elif current_val == 1:
        print("DSC is already on; nothing to do.")
    else:
        print(f"DSC is in an unknown state (0x{current_val:02X}); leaving as is.")

def get_dmcub():
    base = "/sys/kernel/debug/dri"
    if not os.path.isdir(base):
        return
    for num in range(0, 10):
        fw_info = os.path.join(base, str(num), "amdgpu_firmware_info")
        if not os.path.exists(fw_info):
            continue
        with open(fw_info, "r") as f:
            for line in f:
                if "DMCUB" in line:
                    version = line.strip().split()[-1]
                    print(f"DRI device {num} DMCUB F/W version: {version}")

def discover_gpu():
    try:
        from pyudev import Context
    except ModuleNotFoundError:
        sys.exit("Missing pyudev, please install it (e.g., sudo pip3 install pyudev).")
    gpus = []
    context = Context()
    for dev in context.list_devices(subsystem="drm_dp_aux_dev"):
        if "eDP" in dev.sys_path:
            gpus.append(dev.device_node)
    return gpus

if __name__ == "__main__":
    gpus = discover_gpu()
    if not gpus:
        sys.exit("Failed to find any /dev/drm_dp_aux* device node for eDP.")

    get_dmcub()

    for gpu in gpus:
        print(f"\nExamining GPU AUX node: {gpu}")
        try:
            with open(gpu, "r+b") as f:
                try:
                    enable_dsc_if_off(f)
                except OSError:
                    print("Could not read/write DPCD. If the panel is off, turn it on and try again.")
        except PermissionError:
            sys.exit("Permission denied. Please run as root or use sudo.")
EOF

chmod +x "${INSTALL_DIR}/dsc.py"

# Create the systemd service
cat << EOF > "/etc/systemd/system/${UNIT_FILE}"
[Unit]
Description=Monitor Thunderbolt Hot-Plug Events
After=network.target

[Service]
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/${PY_SCRIPT_NAME}
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "==> Enabling and starting the ${SERVICE_NAME} service..."
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl start "${SERVICE_NAME}"

PACKAGE_NAME="tbt_monitor_package.tar.gz"
echo "==> Creating a tar.gz package of the installed files: ${PACKAGE_NAME}"

tar -czf "${PACKAGE_NAME}" \
  -C "${INSTALL_DIR}" "${PY_SCRIPT_NAME}" "dsc.py" \
  -C "/etc/systemd/system" "${UNIT_FILE}"

echo "==> Installation complete."
echo "------------------------------------------------------------------"
echo "Systemd service: /etc/systemd/system/${UNIT_FILE}"
echo "Python script:   ${INSTALL_DIR}/${PY_SCRIPT_NAME}"
echo "DSC script:      ${INSTALL_DIR}/dsc.py"
echo "Package created: ${PACKAGE_NAME}"
echo "------------------------------------------------------------------"
echo "Service status:"
systemctl status "${SERVICE_NAME}" --no-pager || true
echo "------------------------------------------------------------------"
echo "To stop the service:   sudo systemctl stop ${SERVICE_NAME}"
echo "To disable the service: sudo systemctl disable ${SERVICE_NAME}"
echo "------------------------------------------------------------------"

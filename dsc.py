#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Force DSC bit enable for all connected external monitors."""

import sys
import os
import glob

def write_enable_dsc(dev_path):
    """Writes 0x01 to 0x160 to force enabling DSC support."""
    try:
        with open(dev_path, "rb+") as f:
            f.seek(0x160)
            f.write(bytes([0x01]))
            print(f"○ [SUCCESS] Wrote 0x01 to DPCD 0x160 for {dev_path}")
    except PermissionError:
        sys.exit("Permission denied while writing. Please run as root.")
    except Exception as e:
        print(f"○ [ERROR] Failed to write DSC bit for {dev_path}: {e}")

def discover_connected_monitors():
    """Discover all connected external monitors by reading /sys/class/drm/card*-*/status."""
    connected_monitors = []
    drm_base = "/sys/class/drm/"
    connector_paths = glob.glob(os.path.join(drm_base, "card*-*"))

    for connector in connector_paths:
        if "eDP" in connector:
            continue  # Skip internal displays (laptop screen)

        status_path = os.path.join(connector, "status")
        aux_glob = os.path.join(connector, "drm_dp_aux*")

        if not os.path.exists(status_path):
            continue

        try:
            with open(status_path, "r") as f:
                status = f.read().strip()
                if status == "connected":
                    aux_list = glob.glob(aux_glob)
                    for aux in aux_list:
                        aux_dev = os.path.join("/dev", os.path.basename(aux))
                        if os.path.exists(aux_dev):
                            connected_monitors.append((connector, aux_dev))
        except Exception:
            continue

    return connected_monitors

def main():
    monitors = discover_connected_monitors()
    if not monitors:
        sys.exit("No connected external monitors with AUX channels found.")

    for connector, monitor in monitors:
        print(f"\n○ Processing monitor {monitor} ({connector})...")
        write_enable_dsc(monitor)

if __name__ == "__main__":
    main()

#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""DSC bit value checker and enabler for daisy-chained external monitors"""

import sys
import os
import glob

DSC_FLAGS = {
    0: "DSC Not Supported",
    1: "DSC Supported",
}

def read_dsc_support(f):
    """Reads 0x160 DPCD register to check DSC support."""
    f.seek(0x160)
    val = int.from_bytes(f.read(1), "little")
    supported = val & 0x01  # Bit 0 = DSC supported
    return supported, val

def write_enable_dsc(dev_path):
    """Writes to 0x160 to try enabling DSC support."""
    try:
        with open(dev_path, "rb+") as f:
            f.seek(0x160)
            f.write(bytes([0x01]))
            print("○ Wrote 0x01 to DPCD 0x160 (forced DSC support flag)")
    except PermissionError:
        sys.exit("Permission denied while writing. Please run as root.")
    except Exception as e:
        print(f"○ Failed to write: {e}")

def is_daisy_chain(connector_name):
    """Returns True if connector name suggests a daisy-chained MST output."""
    # Examples: card1-DP-1-1, card1-DP-1-2
    parts = connector_name.split('-')
    return len(parts) >= 4 and parts[-2].startswith('DP') and parts[-1].isdigit()

def discover_connected_monitors():
    """Discover all connected monitors by reading /sys/class/drm/card*-*/status."""
    connected_monitors = []
    drm_base = "/sys/class/drm/"
    connector_paths = glob.glob(os.path.join(drm_base, "card*-*"))

    for connector in connector_paths:
        if "eDP" in connector:
            continue  # skip internal displays

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
        print(f"\nChecking {monitor} ({connector})...")
        try:
            with open(monitor, "rb") as f:
                try:
                    supported, raw_val = read_dsc_support(f)
                    print(f"○ DSC Support: {DSC_FLAGS.get(supported, 'Unknown')} (Raw: {raw_val:#04x})")
                    
                    if supported == 0:
                        if is_daisy_chain(connector):
                            print("● Daisy-chained monitor detected. Forcing DSC bit enable...")
                            write_enable_dsc(monitor)
                            # Re-read after writing
                            with open(monitor, "rb") as f_verify:
                                supported_new, raw_val_new = read_dsc_support(f_verify)
                                print(f"○ New DSC Support status: {DSC_FLAGS.get(supported_new, 'Unknown')} (Raw: {raw_val_new:#04x})")
                        else:
                            print("○ DSC not supported and not a daisy-chained monitor. No action taken.")
                except OSError:
                    print("○ Could not read DPCD. Try turning the monitor on and retry.")
                    continue
        except PermissionError:
            sys.exit("Permission denied opening AUX. Please run as root.")

if __name__ == "__main__":
    main()

#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""DSC identification script for AMD systems"""
import sys
import os
import subprocess
from pyudev import Context

def read_and_update_dpcd_value(f, device_name):
    """Reads the DPCD value at the given address and writes 1 if it is 0."""
    f.seek(0x160)
    value = f.read(1)
    
    print(f"Device {device_name}: DSC value read at address 0x160 is {value.hex()}.")
    
    if value == b'\x00':
        f.seek(0x160)
        f.write(b'\x01')
        f.seek(0x160)
        value = f.read(1)
        print(f"After writing: {value.hex()}")
        print(f"Device {device_name}: DSC bit was 0 and has been changed to 1.")
        return True
    else:
        print(f"Device {device_name}: DSC bit was already 1.")
        return False

def discover_gpu(connected_gpus):
    """Discover all GPUs with drm_dp_aux_dev subsystem."""
    gpus = []
    
    if not isinstance(connected_gpus, (list, set)):
        raise ValueError("connected_gpus must be a list or set.")
    
    context = Context()
    
    # Discover the GPU devices with drm_dp_aux_dev
    for dev in context.list_devices(subsystem="drm_dp_aux_dev"):
        newDev = str(dev).split("/")[-2]
        
        if "eDP" in dev.sys_path:
            continue
        
        if len(newDev) > 4 and any(connected_gpu in newDev for connected_gpu in connected_gpus):
            gpus.append(dev.device_node)
    
    return gpus

def get_connected_gpus():
    """Filter GPUs by their connection status."""
    connected_gpus = []
    
    try:
        result = subprocess.check_output('for dev in /sys/class/drm/*/status; do echo "$(basename $(dirname $dev)) - $(cat $dev)"; done', shell=True, text=True)
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error running shell command: {e}")
    
    for line in result.splitlines():
        device, status = line.split(" - ")
        if "connected" == status and "eDP" not in device:
            connected_gpus.append(device)
    
    if not connected_gpus:
        sys.exit("No connected monitors found.")
    
    return connected_gpus

if __name__ == "__main__":

    connected_gpus = get_connected_gpus()  # Get only the connected GPUs

    print(f"Connected GPUs: {connected_gpus}")  # Debug output

    gpus = discover_gpu(connected_gpus)  # Discover all GPUs
    
    if not connected_gpus:
        sys.exit("No connected GPUs found.")
    
    changed_devices = [] 

    # Process only the connected GPUs
    for gpu in gpus:
        device_name = gpu
        try:
            with open(gpu, "r+b") as f:
                try:
                    if read_and_update_dpcd_value(f, device_name):
                        changed_devices.append(device_name)
                except OSError as e:
                    continue
        except PermissionError:
            sys.exit("Run as root")
        except OSError as e:
            continue

    if changed_devices:
        print("\nDevices with DSC bit changed to 1:")
        for device in changed_devices:
            print(f"- {device}")
    else:
        print("\nNo devices had the DSC bit changed.")

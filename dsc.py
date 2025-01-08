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

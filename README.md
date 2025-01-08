# Thunderbolt DSC Monitor Setup

This repository helps automatically **monitor Thunderbolt hot-plug events** and **enable Display Stream Compression (DSC)** when needed. A common use case is **Lenovo docks** with a **daisy chain setup**, where you sometimes cannot drive two monitors at 60Hz simultaneously unless DSC is enabled at the panel level.

## How It Works

- **`setup_tbt_monitor.sh`** installs dependencies, copies `monitor_tbt.py` and `dsc.py` into `/opt/tbt-monitor/`, creates a systemd service (`tbt-monitor.service`), and archives the two files into a `.tar.gz`.
- **`monitor_tbt.py`** listens for Thunderbolt hot-plug events. When a device is plugged in, it calls `dsc.py`.
- **`dsc.py`** reads from DPCD address `0x160` (commonly associated with DSC). If DSC is off (`0`), it writes `1` to enable DSC, which can address the inability to run two displays at 60Hz on certain docks (e.g., Lenovo) in a daisy chain configuration.

## Why This Helps

Many users encounter a limitation with **daisy-chained monitors** on certain docks:  
- Without DSC, you may only get **30Hz** on dual-monitor daisy chains.  
- By enabling DSC at the panel level (via `dsc.py`), the link bandwidth usage is reduced, allowing both external monitors to operate at **60Hz**.

> **Warning**  
> Toggling DSC via DPCD may conflict with the kernel’s own DP link management. Only use this approach if you are comfortable adjusting hardware registers directly.

## Setup Instructions

1. **Clone or Download** this repository.
2. **Make the setup script executable**:
   ```bash
   chmod +x setup_tbt_monitor.sh

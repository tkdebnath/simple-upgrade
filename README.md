# simple-upgrade

A Python package for network device firmware upgrades, supporting Cisco IOS-XE devices via a clean, stageable pipeline.

## Features

- Connect to network devices via SSH (scrapli) and unicon (pyATS/genie)
- Gather detailed device information (manufacturer, hardware model, version, serial, TACACS source interface)
- Stageable upgrade workflow with shared state:
  - **Sync** — Gather device info
  - **Readiness** — Validate flash space, version, platform
  - **Pre-check** — Snapshot pre-upgrade state
  - **Distribute** — Download firmware image via HTTP/HTTPS
  - **Activate** — `install add / activate / commit` workflow with dialog handling
  - **Wait** — Post-reload stabilisation delay
  - **Ping** — Reachability verification
  - **Post-check** — Snapshot post-upgrade state
  - **Verification** — Confirm installed version matches target
- Three connection modes: `normal`, `mock`, `dry_run`
- Case-insensitive hardware model matching against device profiles
- Smart download: skips re-download if file already exists with correct size/MD5

## Supported Devices

| Manufacturer | Platform (`device_type`) | Hardware Models |
|---|---|---|
| Cisco | `cisco_iosxe` / `cisco_xe` | C9300, C9300L, C9300X, C9300UX, C9400, C9500, Catalyst 3650/3850/9200/9200XL/9300X |

> **Note:** Juniper and Arista device profile files exist but manufacturer upgrade modules are not yet implemented. Only Cisco IOS-XE is production-ready.

## Connection Modes

| Mode | Description |
|------|-------------|
| `normal` | Real SSH connection with full upgrade execution |
| `mock` | Simulate entire pipeline without any real connections (testing/CI) |
| `dry_run` | Connect to device but only execute show commands; mock upgrade commands |

## Installation

```bash
pip install simple-upgrade
```

## Quick Start

### Using `UpgradePackage` (Recommended)

```python
from simple_upgrade import UpgradePackage

upgrade = UpgradePackage(
    host="192.168.1.1",
    username="admin",
    password="password123",
    device_type="cisco_iosxe",
    golden_image={
        "version": "17.9.4",
        "image_name": "cat9k_iosxe.17.09.04.SPA.bin"
    },
    file_server={
        "ip": "10.0.0.10",
        "protocol": "http",
        "base_path": "/images",
        "source_interface": "GigabitEthernet0/0"  # optional
    }
)

(upgrade
    .sync()
    .readiness()
    .pre_check()
    .distribute()
    .activate()
    .wait()
    .ping()
    .post_check()
    .verification()
)

if upgrade.success:
    print("Upgrade successful!")
else:
    print(f"Failed at stage: {upgrade.failed_stage}")
    print(f"Errors: {upgrade.errors}")
```

### Mock Mode (No Real Connection)

```python
upgrade = UpgradePackage(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_iosxe",
    connection_mode="mock",
    golden_image={"version": "17.9.4", "image_name": "cat9k_iosxe.17.09.04.SPA.bin"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/images"}
)

upgrade.sync().readiness().distribute().activate()

print(upgrade.stage_results['distribute']['message'])
# [MOCK] Would execute: copy http://10.0.0.10/images/cat9k_iosxe.17.09.04.SPA.bin flash:cat9k_iosxe.17.09.04.SPA.bin

print(upgrade.stage_results['activate']['message'])
# [MOCK] Would execute: install add file flash:cat9k_iosxe.17.09.04.SPA.bin activate commit
```

### Dry-Run Mode (Real Connection, No Upgrade)

```python
upgrade = UpgradePackage(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_iosxe",
    connection_mode="dry_run",
    golden_image={"version": "17.9.4", "image_name": "cat9k_iosxe.17.09.04.SPA.bin"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/images"}
)

upgrade.sync().readiness().distribute().activate()

print(upgrade.stage_results['distribute']['message'])
# [DRY-RUN] Would execute: copy http://10.0.0.10/images/cat9k_iosxe.17.09.04.SPA.bin flash:cat9k_iosxe.17.09.04.SPA.bin
```

## Upgrade Workflow Stages

| # | Stage | Connection | Description |
|---|-------|------------|-------------|
| 1 | `sync` | scrapli | Fetch device info (model, version, serial, TACACS source interface) |
| 2 | `readiness` | scrapli | Check flash space, platform, version |
| 3 | `pre_check` | scrapli | Snapshot pre-upgrade state |
| 4 | `distribute` | unicon | Download firmware via HTTP/HTTPS |
| 5 | `activate` | unicon | `install add file / activate / commit` with reload dialog |
| 6 | `wait` | — | Sleep + ping loop until device is reachable |
| 7 | `ping` | — | Verify device is reachable |
| 8 | `post_check` | scrapli | Snapshot post-upgrade state |
| 9 | `verification` | scrapli | Confirm installed version matches target |

## `golden_image` Parameters

| Key | Required | Description |
|-----|----------|-------------|
| `version` | Yes | Target software version (e.g. `17.9.4`) |
| `image_name` | Yes | Image filename only — **no `flash:` prefix** (e.g. `cat9k_iosxe.17.09.04.SPA.bin`) |

## `file_server` Parameters

| Key | Required | Description |
|-----|----------|-------------|
| `ip` | Yes | HTTP/HTTPS server IP address |
| `protocol` | Yes | `http` or `https` |
| `base_path` | Yes | Base URL path (e.g. `/images`) |
| `source_interface` | No | Source interface for HTTP client (e.g. `GigabitEthernet0/0`) |

## `device_type` Values

| Value | Description |
|-------|-------------|
| `cisco_iosxe` | Cisco IOS-XE (preferred) |
| `cisco_xe` | Cisco IOS-XE alias |
| `cisco_ios` | Cisco IOS |

> **Note:** `device_type` is the **software platform** (OS), not the hardware model. Hardware model (e.g. C9300) is auto-detected from the device via `show version` during `sync()`.

## `ConnectionManager` (Advanced)

```python
from simple_upgrade import ConnectionManager

cm = ConnectionManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_iosxe",
    enable_password="enable123",  # for privileged mode
    enable_mode=True,
    connection_timeout=30
)

sc = cm.get_connection(channel='scrapli')
uc = cm.get_connection(channel='unicon')
cm.disconnect()
```

| Channel | Library | Used for |
|---------|---------|----------|
| `scrapli` | scrapli | Readiness, pre/post checks, verification |
| `unicon` | pyATS/genie | Distribute, activate (interactive dialogs) |

## `SyncManager` — Device Info Fields

```python
from simple_upgrade import ConnectionManager, SyncManager

cm = ConnectionManager(host="192.168.1.1", username="admin",
                       password="password", device_type="cisco_iosxe")
conn = cm.get_connection(channel='scrapli')
platform = cm.get_platform(channel='scrapli')

sync = SyncManager(connection_manager=cm, platform=platform)
info = sync.fetch_info()
```

| Field | Description |
|-------|-------------|
| `manufacturer` | e.g. `Cisco` |
| `model` | Hardware model, e.g. `C9300` |
| `version` | Software version, e.g. `17.9.4` |
| `hostname` | Device hostname |
| `serial_number` | Chassis serial number |
| `uptime` | Device uptime string |
| `boot_method` | Boot image path |
| `config_register` | Config register value |
| `tacacs_source_interface` | TACACS+ source interface, if configured |
| `flash_size` | Flash storage size |
| `memory_size` | DRAM size |

## Device Profiles

Hardware model profiles are located in `device_profiles/cisco/`. Model matching is **case-insensitive**.

```python
from simple_upgrade import match_model_to_profile

profile = match_model_to_profile('C9300', 'cisco')
# Also matches: 'c9300', 'C9300L', 'C9300X', 'C9300UX'
```

## Requirements

- Python 3.10+
- `scrapli` — SSH connections (readiness, checks, verification)
- `genie` / `pyats` / `unicon` — File distribution and activation

## License

Apache License 2.0

## Author

Tarani Debnath

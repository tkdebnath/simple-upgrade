# simple-upgrade Usage Guide

## Table of Contents

- [Quick Start](#quick-start)
- [Connection Modes](#connection-modes)
- [UpgradePackage Reference](#upgradepackage-reference)
- [Stage Reference](#stage-reference)
- [Image and File Server Config](#image-and-file-server-config)
- [ConnectionManager](#connectionmanager)
- [SyncManager](#syncmanager)
- [Device Profiles and Model Matching](#device-profiles-and-model-matching)
- [Checks and Report](#checks-and-report)

---

## Quick Start

```python
from simple_upgrade import UpgradePackage

upgrade = UpgradePackage(
    host="192.168.1.1",
    username="admin",
    password="password123",
    device_type="cisco_iosxe",
    golden_image={
        "version": "17.9.4",
        "image_name": "cat9k_iosxe.17.09.04.SPA.bin"   # no flash: prefix
    },
    file_server={
        "ip": "10.0.0.10",
        "protocol": "http",
        "base_path": "/images"
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
    print(f"Failed at: {upgrade.failed_stage}")
    print(f"Errors: {upgrade.errors}")
```

---

## Connection Modes

### Normal Mode

Full upgrade with real device connections.

```python
upgrade = UpgradePackage(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_iosxe",
    connection_mode="normal",   # default
    golden_image={"version": "17.9.4", "image_name": "cat9k_iosxe.17.09.04.SPA.bin"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/images"}
)

upgrade.sync().readiness().distribute().activate().wait().ping().post_check().verification()
```

### Mock Mode

No real connections. All stages simulated. Returns the exact CLI commands that would run.

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

upgrade.sync().distribute().activate()

# Result shows what would run
print(upgrade.stage_results['distribute']['message'])
# [MOCK] Would execute: copy http://10.0.0.10/images/cat9k_iosxe.17.09.04.SPA.bin flash:cat9k_iosxe.17.09.04.SPA.bin

print(upgrade.stage_results['activate']['message'])
# [MOCK] Would execute: install add file flash:cat9k_iosxe.17.09.04.SPA.bin activate commit
```

> **Note:** In mock mode, `device.model` is populated by `MockSyncManager`. Hardware model comes from `device.model` set after `sync()` — it is **never** inferred from `device_type`.

### Dry-Run Mode

Connects to a real device via SSH. Executes show commands for real (readiness, pre/post checks). Mocks all upgrade commands (distribute, activate).

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

upgrade.sync().readiness().pre_check().distribute().activate()

print(upgrade.stage_results['distribute']['message'])
# [DRY-RUN] Would execute: copy http://10.0.0.10/images/cat9k_iosxe.17.09.04.SPA.bin flash:cat9k_iosxe.17.09.04.SPA.bin
```

| Feature | `normal` | `mock` | `dry_run` |
|---------|----------|--------|-----------|
| Real SSH | Yes | No | Yes |
| Show commands | Real | Simulated | Real |
| Upgrade commands | Real | Simulated | Simulated |
| Unicon connection | Yes | No | No |

---

## UpgradePackage Reference

### Constructor Parameters

```python
UpgradePackage(
    host: str,
    username: str,
    password: str,
    device_type: str,                  # cisco_iosxe, cisco_xe, cisco_ios
    golden_image: dict,
    file_server: dict,
    port: int = 22,
    connection_mode: str = "normal",   # normal | mock | dry_run
    **device_kwargs                    # passed to ConnectionManager
)
```

### Chaining Stages

All stage methods return `self`, enabling method chaining:

```python
(upgrade
    .sync()          # → populates device_info (model, version, hostname, serial, ...)
    .readiness()     # → checks flash space, platform, version
    .pre_check()     # → saves pre-upgrade snapshots to output/
    .distribute()    # → copies image to flash via HTTP/HTTPS (unicon)
    .activate()      # → install add/activate/commit + reload (unicon)
    .wait()          # → sleep + ping loop (10 min default)
    .ping()          # → final reachability check
    .post_check()    # → saves post-upgrade snapshots to output/
    .verification()  # → confirms version matches target
)
```

### Result Inspection

```python
# Overall
upgrade.success           # bool
upgrade.failed_stage      # str | None
upgrade.errors            # list[str]
upgrade.device_info       # dict — populated after sync()

# Per-stage
upgrade.stage_results['sync']
upgrade.stage_results['readiness']
upgrade.stage_results['distribute']
upgrade.stage_results['activate']
# Each has: {'success': bool, 'message': str, ...}
```

---

## Stage Reference

### `sync()`

Fetches device information. In mock mode, uses `MockSyncManager`. In dry-run/normal mode, connects via scrapli and runs `show version`, `show inventory`, `show run | include tacacs`.

```python
upgrade.sync()
print(upgrade.device_info['model'])      # e.g. 'C9300' (hardware model from show version)
print(upgrade.device_info['version'])    # e.g. '17.9.3'
print(upgrade.device_info['hostname'])   # e.g. 'hkd-swi-cat9k-01'
```

### `distribute()`

Downloads firmware from file server to device flash using unicon. Uses `connection_manager.get_connection('unicon')`.

**Pre-download behaviour:**
- If the file already exists on flash with correct size and MD5 — skips download
- Pushes `ip http client source-interface <interface>` before download if source interface is set

**Copy command format:**
```
copy http://<server_ip>/<base_path>/<image_name> flash:<image_name>
```

**Verification (3-tier):**
1. Output contains byte count
2. File size matches golden_image config
3. MD5 checksum matches

### `activate()`

Runs the full Catalyst 9K install workflow via unicon:

```
install add file flash:<image> activate commit
```

- Handles interactive prompts (`Do you want to proceed?`, `Reload this box?`)
- 3600s timeout on install command
- Checks output for `Error` / `Failed` / `%` prefix

### `wait()`

Sleeps for a configurable time (default 600s) then pings until device is reachable. Maximum wait 10 minutes.

### `verification()`

Connects via scrapli and runs `show version` to confirm running version matches `golden_image['version']`.

---

## Image and File Server Config

### `golden_image`

```python
golden_image = {
    "version": "17.9.4",                           # target version string
    "image_name": "cat9k_iosxe.17.09.04.SPA.bin"  # filename only — NO flash: prefix
}
```

> Do **not** include `flash:/` or `flash:` in `image_name`. The library strips any such prefix automatically, but it is cleaner to omit it.

### `file_server`

```python
file_server = {
    "ip": "10.0.0.10",
    "protocol": "http",        # http or https only
    "base_path": "/images",    # URL path on the server
    "source_interface": "GigabitEthernet0/0"   # optional
}
```

> Only `http` and `https` are supported. TFTP, SCP, and FTP are intentionally disabled.

---

## ConnectionManager

Provides unified scrapli / unicon connections.

```python
from simple_upgrade import ConnectionManager

cm = ConnectionManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_iosxe",
    enable_password="enable123",
    enable_mode=True,
    connection_timeout=30,
    auth_strict_key=False
)

# scrapli — for show commands, checks, verification
sc = cm.get_connection(channel='scrapli')
output = sc.send_command("show version")
print(output.result)

# unicon — for interactive commands (copy, install)
uc = cm.get_connection(channel='unicon')
uc.configure(["no boot system", "boot system flash:packages.conf"])

cm.disconnect()
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | str | — | Device IP or hostname |
| `username` | str | — | SSH username |
| `password` | str | — | SSH password |
| `device_type` | str | — | Platform — `cisco_iosxe`, `cisco_xe`, `cisco_ios` |
| `port` | int | 22 | SSH port |
| `timeout` | int | 30 | Command timeout (seconds) |
| `connection_timeout` | int | 30 | Connection timeout (seconds) |
| `enable_mode` | bool | False | Enter enable mode |
| `enable_password` | str | None | Enable password |
| `auth_strict_key` | bool | False | Strict SSH host-key checking |

> **Note:** Use `enable_password`, not `secret`. Passing `secret` has no effect.

---

## SyncManager

```python
from simple_upgrade import ConnectionManager, SyncManager

cm = ConnectionManager(host="192.168.1.1", username="admin",
                       password="password", device_type="cisco_iosxe")
conn = cm.get_connection(channel='scrapli')
conn.open()

platform = cm.get_platform(channel='scrapli')
sync = SyncManager(connection_manager=cm, platform=platform)
info = sync.fetch_info()
```

### Using the standalone function

```python
from simple_upgrade import sync_device

info = sync_device(
    host="192.168.1.1",
    username="admin",
    password="password",
    platform="cisco_iosxe"
)
```

### Returned Fields

| Field | Description |
|-------|-------------|
| `manufacturer` | `Cisco` |
| `model` | Hardware model (e.g. `C9300`) — from `show version` |
| `version` | Software version (e.g. `17.9.4`) |
| `hostname` | Device hostname |
| `serial_number` | Chassis serial |
| `uptime` | Uptime string |
| `boot_method` | Boot image path |
| `config_register` | Config register |
| `tacacs_source_interface` | TACACS+ source interface, if configured |
| `flash_size` | Flash storage |
| `memory_size` | DRAM |

---

## Device Profiles and Model Matching

Device profiles live in `device_profiles/cisco/`. Model matching is **case-insensitive**.

```python
from simple_upgrade import match_model_to_profile

profile = match_model_to_profile('C9300', 'cisco')   # matches
profile = match_model_to_profile('c9300', 'cisco')   # also matches
profile = match_model_to_profile('C9300L', 'cisco')  # matches via models list
```

### Cisco Profiles

| Profile file | Primary model | Also matches |
|---|---|---|
| `c9300.json` | `c9300` | C9300, C9300L, C9300X, C9300UX |
| `c9400.json` | `C9400` | — |
| `c9500.json` | `c9500` | — |
| `catalyst_9200.json` | `catalyst_9200` | — |
| `catalyst_9200xl.json` | `catalyst_9200xl` | — |
| `catalyst_9300x.json` | `catalyst_9300x` | — |
| `catalyst_3650.json` | `catalyst_3650` | — |
| `catalyst_3850.json` | `catalyst_3850` | — |

> **Platform vs Model:** `device_type` is the **software platform** (e.g. `cisco_iosxe`). Hardware model (e.g. `C9300`) is a separate concept populated from `show version` during `sync()`. Never infer hardware model from `device_type`.

---

## Checks and Report

### Pre/Post Checks

```python
from simple_upgrade import Checks

checks = Checks(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_iosxe",
    secret="enable123"   # maps to enable_password
)

results = checks.run_all()
checks.save_to_file("output/pre_check")
```

### Report Generator

Compare pre and post check results:

```python
from simple_upgrade import ReportGenerator

generator = ReportGenerator(
    pre_checks=pre_results,
    post_checks=post_results
)

report = generator.generate_report()
generator.save_report(report, "upgrade_report.txt")
```

---

## Summary

| Concept | Value |
|---------|-------|
| Primary API | `UpgradePackage` |
| Distribute/Activate library | unicon (pyATS/genie) |
| Readiness/Checks library | scrapli |
| Supported OS | Cisco IOS-XE only (production) |
| Transfer protocols | HTTP and HTTPS only |
| Model matching | Case-insensitive, via `device_profiles/cisco/*.json` |
| Hardware model source | `show version` (not inferred from `device_type`) |

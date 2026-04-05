# simple-upgrade — Usage Guide

## Table of Contents

- [Full Constructor Reference](#full-constructor-reference)
- [Connection Modes](#connection-modes)
- [Stage-by-Stage Execution](#stage-by-stage-execution)
- [Device Profile System](#device-profile-system)
- [File Transfer Protocols](#file-transfer-protocols)
- [Post-Activation Wait Tuning](#post-activation-wait-tuning)
- [Logging and Output](#logging-and-output)
- [Diagnostic Reports](#diagnostic-reports)
- [Advanced: ConnectionManager](#advanced-connectionmanager)
- [Troubleshooting](#troubleshooting)

---

## Full Constructor Reference

```python
from simple_upgrade import UpgradePackage

pkg = UpgradePackage(
    # ═══════════════════════════════════════════
    #  REQUIRED PARAMETERS
    # ═══════════════════════════════════════════
    host="172.20.20.11",                        # Device IP or hostname
    username="admin",                           # SSH username
    password="admin",                           # SSH password
    platform="cisco_iosxe",                     # Software platform

    # ═══════════════════════════════════════════
    #  OPTIONAL — Connection & Authentication
    # ═══════════════════════════════════════════
    port=22,                                    # SSH port (default: 22)
    manufacturer="cisco",                       # Manufacturer key (default: "cisco")
    connection_mode="normal",                   # "normal" | "mock" | "dry_run"
    enable_password="admin",                    # Enable / privilege-exec secret

    # ═══════════════════════════════════════════
    #  OPTIONAL — Routing & Connectivity
    # ═══════════════════════════════════════════
    source_interface="GigabitEthernet0/0",      # Source interface for file transfer
    source_vrf="Mgmt-vrf",                      # VRF context for file transfer routing

    # ═══════════════════════════════════════════
    #  OPTIONAL — Post-Activation Wait Timers
    # ═══════════════════════════════════════════
    post_wait_delay=600,                        # Seconds before SSH polling starts (default: 600)
    post_wait_retries=120,                      # Max SSH probe attempts × 15s each (default: 120)
    post_wait_convergence=30,                   # Routing/STP convergence wait (default: 30)

    # ═══════════════════════════════════════════
    #  GOLDEN IMAGE (target firmware)
    # ═══════════════════════════════════════════
    golden_image={
        "version": "17.13.1",                   # Target software version string
        "image_name": "cat9k_iosxe.17.13.01.SPA.bin",  # Filename only (no flash: prefix)
        "image_size": 1234567890,               # Expected file size in bytes
        "md5": "abc123def456...",                # MD5 checksum for verification
        "sha256": "def456ghi789...",             # Optional SHA-256 checksum
    },

    # ═══════════════════════════════════════════
    #  FILE SERVER (image source)
    # ═══════════════════════════════════════════
    file_server={
        "protocol": "http",                     # http | https | tftp | ftp | scp
        "ip": "192.168.29.73",                  # Server IP address
        "port": 5000,                           # Server port (optional — omit for default)
        "base_path": "/Cisco/C9XXX/",           # URL path on the server
        "username": "ftpuser",                  # FTP/SCP username (optional)
        "password": "ftppassword",              # FTP/SCP password (optional)
        # "source_interface": "Gi0/0",          # Can also be set here instead of top-level
        # "source_vrf": "Mgmt-vrf",             # Can also be set here instead of top-level
    }
)
```

### Parameter Precedence

`source_interface` and `source_vrf` can be set in **two places**:

1. **Top-level** (recommended): `UpgradePackage(source_interface="Gi0/0")`
2. **Inside `file_server`**: `file_server={"source_interface": "Gi0/0"}`

Top-level values are transparently proxied into `file_server` at initialization. If both are set, the `file_server` value takes precedence to allow explicit overrides.

---

## Connection Modes

### Normal Mode (Production Upgrade)

```python
pkg = UpgradePackage(
    host="172.20.20.11",
    username="admin",
    password="admin",
    platform="cisco_iosxe",
    connection_mode="normal",
    golden_image={...},
    file_server={...}
)
```

### Mock Mode (No Device Connection)

```python
pkg = UpgradePackage(
    host="192.168.1.1",
    username="admin",
    password="admin",
    platform="cisco_iosxe",
    connection_mode="mock",
    golden_image={"version": "17.13.1", "image_name": "cat9k.bin", "image_size": 1, "md5": "x"},
    file_server={"ip": "10.0.0.10", "base_path": "/images"}
)

result = pkg.run_stage("distribute")
print(result.message)
# [MOCK] Would execute: copy http://10.0.0.10/images/cat9k.bin flash:/cat9k.bin
```

### Dry-Run Mode (Real Connection, No Changes)

```python
pkg = UpgradePackage(
    host="172.20.20.11",
    username="admin",
    password="admin",
    platform="cisco_iosxe",
    connection_mode="dry_run",
    golden_image={...},
    file_server={...}
)

# sync, readiness, pre_check run for real
# distribute, activate are simulated
```

| Feature | `normal` | `mock` | `dry_run` |
|---------|----------|--------|-----------|
| Real SSH | ✓ | ✗ | ✓ |
| Show commands | Real | Simulated | Real |
| Copy/Install | Real | Simulated | Simulated |
| Post-reload wait | Real TCP sweep | Instant | Instant |

---

## Stage-by-Stage Execution

### Interactive Mode

```python
import json

for stage in pkg.STAGES:
    if pkg.ctx.failed_stage and stage != 'diff':
        print(f"[-] Skipping '{stage}' (halted at '{pkg.ctx.failed_stage}')")
        continue

    action = input(f"Run '{stage}'? [Enter/q]: ").strip().lower()
    if action == 'q':
        break

    result = pkg.run_stage(stage)
    print(json.dumps(result.model_dump(), indent=2))
```

### Automatic Mode

```python
results = pkg.execute()  # Runs all stages sequentially, stops on failure
```

### Stage Details

#### 1. `sync`
Connects via Scrapli, runs `show version`, regex-matches hardware model to a JSON device profile. The resolved profile is stored in `ctx.device_info.extra['device_profile']` and drives all subsequent stages.

#### 2. `readiness`
Parses `show file systems` via Genie to validate flash space (requires 2.5× image size free). Compares current version against golden image — blocks if already running target or a higher version.

#### 3. `pre_check`
Iterates over the `commands` dictionary from the resolved JSON profile. Each command output is saved to `output/<hostname>/precheck/<command_key>.txt`.

#### 4. `distribute`
Resolves `copy_image` template from JSON profile, injects runtime values (`{protocol}`, `{server}`, `{path}`, `{image}`), and executes via Unicon with dialog handling. Applies `source_interface` configuration before transfer. Runs `install remove inactive` for flash cleanup.

**Smart-skip logic:** If the file already exists on flash with matching size and MD5, the download is skipped entirely.

#### 5. `activate`
Resolves `install_add` template from JSON profile. If `boot_commands` are defined in the profile, they are applied and saved to NVRAM before activation. Handles all interactive reload prompts.

#### 6. `post_activation_wait`
Disconnects existing SSH sessions, then polls TCP port 22 every 15 seconds until the device responds. Waits for routing convergence after SSH restores.

**Tunable via kwargs:**
```python
post_wait_delay=30,        # Wait before polling starts
post_wait_retries=60,      # Max polling attempts (× 15s = 15 min max)
post_wait_convergence=60,  # STP/routing settle time
```

#### 7. `post_check`
Identical to `pre_check` but saves to `output/<hostname>/postcheck/`.

#### 8. `verification`
Compares running version against `golden_image.version` using strict semantic comparison.

#### 9. `diff`
Generates per-command diffs between pre and post checks. Bundles everything into `output/<hostname>_upgrade_report.zip`.

---

## Device Profile System

### How Profile Resolution Works

1. `sync` runs `show version` → extracts hardware **model** and **platform**
2. The engine scans all JSON files under `device_profiles/cisco/`
3. Each profile's `models` list contains regex patterns (e.g. `"C9300-.*"`)
4. The first profile where a model pattern matches the discovered hardware is selected
5. If the profile has a `group` key, the group template is loaded and merged (profile overrides group)
6. The merged profile is stored in `ctx.device_info.extra['device_profile']`

### Creating a New Device Profile

```json
{
  "manufacturer": "Cisco",
  "model": "catalyst_9300",
  "models": ["C9300-.*", "C9300X-.*", "C9300L-.*", "C9KV-UADP-8P"],
  "group": "install_mode",
  "mode": "switch",
  "series": "Catalyst 9300",
  "platform": ["IOS-XE", "cisco_xe"],
  "device_type": "cisco_iosxe",
  "description": "Cisco Catalyst 9300 Series",
  "flash_size": "16GB"
}
```

### Group Template Example (`groups/install_mode.json`)

```json
{
  "commands": {
    "show_version": "show version",
    "show_inventory": "show inventory",
    "show_running_config": "show running-config",
    "show_ip_route": "show ip route",
    "show_boot": "show boot"
  },
  "upgrade_commands": {
    "copy_image": "copy {protocol}://{server}/{path}/{image} flash:/{image}",
    "verify_image": "verify /md5 flash:/{image} {md5}",
    "install_add": "install add file flash:/{image} activate commit",
    "flash_cleanup": "install remove inactive"
  },
  "boot_commands": [
    "no boot system",
    "boot system flash:packages.conf",
    "no boot manual",
    "no system ignore startupconfig switch all"
  ],
  "default_image_location": "flash:/"
}
```

### Inheritance Rules

- Device profile fields **override** group fields with the same key
- If a device profile has no `commands` block, it inherits entirely from the group
- Remove the `"group"` key to create a standalone profile with no inheritance

---

## File Transfer Protocols

The `source_interface` parameter triggers protocol-specific device configuration before file transfer:

| Protocol | Device Configuration Applied |
|----------|------------------------------|
| `http` / `https` | `ip http client source-interface <intf>` |
| `tftp` | `ip tftp source-interface <intf>` |
| `ftp` | `ip ftp source-interface <intf>` + username/password |
| `scp` | `ip scp server enable` + `ip ssh source-interface <intf>` |

The `source_vrf` parameter prepends `vrf <name>` to the copy command for TFTP/FTP/SCP protocols. HTTP/HTTPS do not support VRF in the copy command syntax — routing is handled via the source interface's VRF membership.

---

## Post-Activation Wait Tuning

The `post_activation_wait` stage uses TCP socket polling for intelligent reload detection:

```
Phase 1: Disconnect SSH sessions
Phase 2: Wait `post_wait_delay` seconds for device to go offline
Phase 3: Probe TCP port 22 every 15 seconds (max `post_wait_retries` attempts)
Phase 4: Wait `post_wait_convergence` seconds for routing convergence
```

### Scenarios

| Environment | `post_wait_delay` | `post_wait_retries` | `post_wait_convergence` |
|-------------|-------------------|---------------------|-------------------------|
| Lab (vIOS) | `10` | `20` | `10` |
| Standard C9300 | `60` | `60` | `60` |
| Large Stack | `120` | `120` | `120` |
| Production (conservative) | `600` | `120` | `30` |

---

## Logging and Output

### Automatic Dual Logging

When `UpgradePackage` is initialized, the framework automatically enables dual logging:

1. **`output/<host>/execution_log.json`** — Structured JSON with full pipeline results, device info, and all stage data including executed commands
2. **`output/<host>/execution_cli.log`** — Timestamped text log capturing all terminal output including Unicon/Scrapli CLI dialogues

The CLI log transparently intercepts `sys.stdout` and the Python `logging` module. Lines that already contain timestamps (e.g. from Unicon) are preserved as-is; plain text output receives automatic timestamps.

### Example CLI Log Output

```
================================================================================
=== DEPLOYMENT STARTED: 2026-04-04 22:01:15 ===
================================================================================

2026-04-04 22:01:16,234: %UNICON-INFO: +++ 172.20.20.11: executing command 'show version' +++
show version
Cisco IOS XE Software, Version 17.12.01prd9
...
2026-04-04 22:01:20,567: [framework] [distribute] Starting native transfer sequence: copy http://...
```

---

## Diagnostic Reports

After completing the pipeline, run the `diff` stage to generate a diagnostic bundle:

```python
result = pkg.run_stage("diff")
print(result.data)
# {'diff_count': 24, 'zip_path': 'output/hkd-swi-cat9k-01_upgrade_report.zip'}
```

The ZIP archive contains:
- All pre-check command outputs
- All post-check command outputs
- Per-command text diffs
- `execution_log.json`

---

## Advanced: ConnectionManager

For low-level access to the SSH connections:

```python
from simple_upgrade import ConnectionManager

cm = ConnectionManager(
    host="172.20.20.11",
    username="admin",
    password="admin",
    platform="cisco_iosxe",
    enable_password="admin",
    connection_mode="normal"
)

# Scrapli — for show commands and structured parsing
sc = cm.get_connection(channel='scrapli')
output = sc.send_command("show version")
parsed = output.genie_parse_output()

# Unicon — for interactive commands (copy, install, reload)
uc = cm.get_connection(channel='unicon')
uc.configure(["no boot system", "boot system flash:packages.conf"])

cm.disconnect()
```

| Channel | Library | Used For |
|---------|---------|----------|
| `scrapli` | scrapli + genie | Show commands, structured parsing, readiness, checks |
| `unicon` | pyATS/unicon | Interactive prompts (copy dialogs, install, reload) |

---

## Troubleshooting

### Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `ProfileValidationError` | Overlapping model patterns in JSON profiles | Ensure each model regex is unique across all profile files |
| `invalid version number` | Experimental/non-standard version string | Expected with vIOS lab devices — verification stage uses strict semver parsing |
| `name 'dest' is not defined` | Profile missing `default_image_location` | Add `"default_image_location": "flash:/"` to the profile or group JSON |
| Double-slash in copy URL | Empty `base_path` (e.g. `"/"`) | Fixed in framework — slashes are dynamically collapsed |
| HTTP transfer fails | File server unreachable from device | Set `source_interface` to the management interface in the device's VRF |
| `_clean_inactive_files` error | Missing `flash_cleanup` in profile | Add `"flash_cleanup": "install remove inactive"` to `upgrade_commands` |

### Validating JSON Profiles

The `ProfileValidator` runs automatically at startup. To test manually:

```python
from simple_upgrade.config_validator import ProfileValidator

validator = ProfileValidator("src/simple_upgrade/device_profiles")
validator.validate_all()  # Raises ProfileValidationError on issues
```

---

## Summary

| Concept | Value |
|---------|-------|
| Primary API | `UpgradePackage` |
| Distribution/Activation | Unicon (pyATS) |
| Readiness/Checks | Scrapli |
| Command definitions | JSON device profiles (not hardcoded) |
| Supported OS | Cisco IOS-XE |
| Transfer protocols | HTTP, HTTPS, TFTP, FTP, SCP |
| Model matching | Regex-based, case-insensitive |
| Hardware model source | `show version` (auto-detected during `sync`) |
| Logging | Dual: JSON structured + CLI text |
| Post-reload detection | TCP socket polling on SSH port 22 |

# simple-upgrade

A modular, profile-driven Python orchestrator for network device firmware upgrades. Built for Cisco IOS-XE with a dynamic JSON device-profile architecture that eliminates hardcoded CLI strings.

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                 UpgradePackage                   │
│  (Orchestrator — runs stages sequentially)       │
├──────────┬──────────┬───────────┬───────────────┤
│   sync   │readiness │ pre_check │  distribute   │
│          │          │           │               │
│ activate │post_acti-│post_check │ verification  │
│          │vation_wait│          │     diff      │
├──────────┴──────────┴───────────┴───────────────┤
│              ExecutionContext (ctx)               │
│  Carries: device_info, golden_image, file_server │
│           device_profile, stage_results          │
├─────────────────────────────────────────────────┤
│  Device Profiles (JSON)    │   TaskRegistry      │
│  groups/ → inheritance     │   @register_stage   │
│  models → regex matching   │   manufacturer map  │
└─────────────────────────────────────────────────┘
```

## Key Features

- **Profile-Driven Execution** — All CLI commands (show, copy, verify, install, boot) are defined in JSON device profiles, not hardcoded in Python
- **Group Inheritance** — Device profiles inherit commands from shared group templates (e.g. `install_mode.json`)
- **Automatic Profile Matching** — Hardware model detected via `show version` is regex-matched to the correct JSON profile
- **Configuration Integrity Validation** — JSON profiles are statically linted at startup for schema errors and overlapping model patterns
- **Smart Download** — Skips re-download if file already exists with matching size and MD5
- **Flash Cleanup** — Automatically runs `install remove inactive` before file transfer
- **TCP Socket Polling** — Post-reload wait uses intelligent SSH port probing instead of blind sleep timers
- **Dual Logging** — Structured JSON execution log + timestamped CLI text log capturing all Unicon/Scrapli output
- **Diagnostic Bundling** — Pre/post check diffs packaged into a ZIP archive for audit

## Pipeline Stages

| # | Stage | Engine | Description |
|---|-------|--------|-------------|
| 1 | `sync` | Scrapli | Discover device hardware, match to JSON profile |
| 2 | `readiness` | Scrapli | Validate flash space, compare running version |
| 3 | `pre_check` | Scrapli | Snapshot device state (commands from JSON profile) |
| 4 | `distribute` | Unicon | Transfer firmware image with MD5 verification |
| 5 | `activate` | Unicon | Execute install command with reload dialog handling |
| 6 | `post_activation_wait` | Socket | TCP sweep on SSH port until device returns online |
| 7 | `post_check` | Scrapli | Snapshot post-upgrade state |
| 8 | `verification` | Scrapli | Confirm running version matches golden image |
| 9 | `diff` | — | Generate pre/post diffs and ZIP bundle |

## Installation

```bash
pip install simple-upgrade
```

## Quick Start

```python
from simple_upgrade import UpgradePackage

pkg = UpgradePackage(
    # ── Required Parameters ──
    host="172.20.20.11",
    username="admin",
    password="admin",
    platform="cisco_iosxe",

    # ── Optional Parameters ──
    port=22,                                    # SSH port (default: 22)
    manufacturer="cisco",                       # Manufacturer key (default: "cisco")
    connection_mode="normal",                   # "normal" | "mock" | "dry_run"
    enable_password="admin",                    # Enable/privilege-exec secret
    source_interface="GigabitEthernet0/0",      # Source interface for file transfers
    source_vrf="Mgmt-vrf",                      # VRF for routing file transfers

    # ── Post-Activation Wait Timers ──
    post_wait_delay=30,                         # Seconds before starting SSH probe (default: 600)
    post_wait_retries=60,                       # Max SSH probe attempts at 15s intervals (default: 120)
    post_wait_convergence=60,                   # STP/routing settle time after SSH returns (default: 30)

    # ── Golden Image ──
    golden_image={
        "version": "17.13.1",                   # Target software version
        "image_name": "cat9k_iosxe.17.13.01.SPA.bin",  # Filename (no flash: prefix)
        "image_size": 1234567890,               # Expected file size in bytes
        "md5": "abc123def456...",                # Expected MD5 checksum
        "sha256": "def456ghi789...",             # Optional SHA-256 checksum
    },

    # ── File Server ──
    file_server={
        "protocol": "http",                     # http | https | tftp | ftp | scp
        "ip": "192.168.29.73",                  # File server IP
        "port": 80,                             # Server port (optional)
        "base_path": "/Cisco/C9XXX/",           # URL path on server
        "username": "ftpuser",                  # FTP/SCP username (optional)
        "password": "ftppassword",              # FTP/SCP password (optional)
    }
)

# Run all stages interactively
for stage in pkg.STAGES:
    result = pkg.run_stage(stage)
    print(f"{stage}: {'✓' if result.success else '✗'} — {result.message}")

# Or run the full pipeline automatically
# results = pkg.execute()
```

## Constructor Parameters

### Required

| Parameter | Type | Description |
|-----------|------|-------------|
| `host` | `str` | Device IP address or hostname |
| `username` | `str` | SSH username |
| `password` | `str` | SSH password |
| `platform` | `str` | Software platform: `cisco_iosxe`, `cisco_xe`, `iosxe` |

### Optional

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `port` | `int` | `22` | SSH port |
| `manufacturer` | `str` | `"cisco"` | Manufacturer key for profile lookup |
| `connection_mode` | `str` | `"normal"` | `normal`, `mock`, or `dry_run` |
| `enable_password` | `str` | `None` | Enable / privilege-exec secret |
| `source_interface` | `str` | `None` | Source interface for file transfer routing (e.g. `GigabitEthernet0/0`) |
| `source_vrf` | `str` | `None` | VRF name for file transfer routing (e.g. `Mgmt-vrf`) |
| `post_wait_delay` | `int` | `600` | Seconds to wait before starting SSH sweep after activation |
| `post_wait_retries` | `int` | `120` | Max SSH probe attempts (at 15-second intervals) |
| `post_wait_convergence` | `int` | `30` | Seconds to wait for routing/STP convergence after SSH restores |

### `golden_image` Dictionary

| Key | Required | Type | Description |
|-----|----------|------|-------------|
| `version` | Yes | `str` | Target software version (e.g. `17.13.1`) |
| `image_name` | Yes | `str` | Filename only — no `flash:` prefix |
| `image_size` | Yes | `int` | Expected file size in bytes |
| `md5` | Yes | `str` | Expected MD5 checksum |
| `sha256` | No | `str` | Optional SHA-256 checksum |

### `file_server` Dictionary

| Key | Required | Type | Description |
|-----|----------|------|-------------|
| `ip` | Yes | `str` | File server IP address |
| `protocol` | No | `str` | Transfer protocol: `http`, `https`, `tftp`, `ftp`, `scp` (default: `http`) |
| `base_path` | Yes | `str` | URL path on the server (e.g. `/Cisco/C9XXX/`) |
| `port` | No | `int` | Server port (omit to use protocol default) |
| `username` | No | `str` | FTP/SCP username |
| `password` | No | `str` | FTP/SCP password |

> **Note:** `source_interface` and `source_vrf` can be specified either as top-level parameters or inside `file_server`. Top-level values take priority.

## Connection Modes

| Mode | SSH | Show Commands | Upgrade Commands | Use Case |
|------|-----|---------------|------------------|----------|
| `normal` | Real | Real | Real | Production upgrades |
| `mock` | None | Simulated | Simulated | CI/CD testing |
| `dry_run` | Real | Real | Simulated | Pre-flight validation |

## Device Profile Architecture

Device profiles are JSON files in `device_profiles/cisco/` that define all commands the orchestrator will execute. No CLI strings are hardcoded in Python.

### Structure

```
device_profiles/
└── cisco/
    ├── groups/
    │   ├── install_mode.json      # Shared template for install-mode devices
    │   └── lab_vios.json          # Lab-specific overrides
    ├── catalyst_9300x.json        # Device profile → inherits from install_mode
    └── catalyst_VIOS.json         # Device profile → inherits from lab_vios
```

### Profile Fields

| Field | Type | Description |
|-------|------|-------------|
| `manufacturer` | `str` | `"Cisco"` |
| `model` | `str` | Profile identifier |
| `models` | `list[str]` | Regex patterns matched against `show version` model |
| `platform` | `list[str]` | Platform identifiers (e.g. `["IOS-XE", "cisco_xe"]`) |
| `group` | `str` | Parent group template to inherit from |
| `commands` | `dict` | Show commands for pre/post checks |
| `upgrade_commands` | `dict` | Copy, verify, install templates with `{placeholders}` |
| `boot_commands` | `list[str]` | Boot config commands applied before activation |
| `default_image_location` | `str` | Target filesystem (e.g. `flash:/`) |

### Template Placeholders

The `upgrade_commands` block supports dynamic placeholders:

| Placeholder | Resolved From |
|-------------|---------------|
| `{protocol}` | `file_server.protocol` |
| `{server}` | `file_server.ip:port` |
| `{path}` | `file_server.base_path` |
| `{image}` | `golden_image.image_name` |
| `{md5}` | `golden_image.md5` |

## Output Files

After execution, the following files are generated in `output/<hostname>/`:

| File | Format | Description |
|------|--------|-------------|
| `execution_log.json` | JSON | Structured pipeline results with all stage data |
| `execution_cli.log` | Text | Timestamped CLI transcript of all terminal output |
| `precheck/*.txt` | Text | Individual pre-check command outputs |
| `postcheck/*.txt` | Text | Individual post-check command outputs |
| `diff/*.txt` | Text | Per-command pre/post diffs |
| `<hostname>_upgrade_report.zip` | ZIP | Bundled diagnostic archive |

## Supported Devices

| Profile | Models Matched | Group |
|---------|---------------|-------|
| `catalyst_9300` | `C9300.*`, `C9300X.*`, `C9300L.*`, `C9KV-UADP-8P` | `install_mode` |
| `catalyst_VIOS` | `IOSv` | `lab_vios` |

> Additional profiles can be added by creating a new JSON file in `device_profiles/cisco/` with appropriate `models` regex patterns and an optional `group` reference.

## Requirements

- Python 3.12+
- `scrapli` — SSH connections (readiness, checks, verification)
- `genie` / `pyats` / `unicon` — File distribution and activation (interactive dialogs)
- `netutils` — Version comparison utilities
- `pydantic` — Data model validation

## License

Apache License 2.0

## Author

Tarani Debnath

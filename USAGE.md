# simple-upgrade Usage Guide

This guide covers all usage patterns for the simple-upgrade library.

## Table of Contents

- [Quick Start](#quick-start)
- [Connection Modes](#connection-modes)
  - [Normal Mode (Real Upgrade)](#normal-mode-real-upgrade)
  - [Mock Mode (Pipeline Simulation)](#mock-mode-pipeline-simulation)
  - [Dry-Run Mode (Real Connection, Mock Commands)](#dry-run-mode-real-connection-mock-commands)
- [Manufacturer-Specific Behavior](#manufacturer-specific-behavior)
- [Execution Path Tracking](#execution-path-tracking)
- [Device Model Inference](#device-model-inference)

---

## Quick Start

```python
from simple_upgrade import UpgradeManager

# Create upgrade manager
manager = UpgradeManager(
    host="192.168.1.1",
    username="admin",
    password="password123",
    device_type="cisco_xe",
    golden_image={
        "version": "17.9.4",
        "image_name": "flash:c9300-universalk9.17.9.4.SPA.bin"
    },
    file_server={
        "ip": "10.0.0.10",
        "protocol": "http",
        "base_path": "/tftpboot"
    }
)

# Execute upgrade
result = manager.upgrade()

# Check results
if result['success']:
    print("Upgrade successful!")
else:
    print("Upgrade failed:", result['errors'])
```

---

## Connection Modes

The library supports three connection modes for different use cases.

### Normal Mode (Real Upgrade)

Executes the full upgrade pipeline with real SSH connections to the device.

```python
from simple_upgrade import UpgradeManager

manager = UpgradeManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_xe",
    connection_mode="normal",  # Default
    golden_image={"version": "17.9.4", "image_name": "flash:c9300.bin"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/tftpboot"}
)

result = manager.upgrade()
print(result['success'])
```

**Stage Execution:**
1. Readiness - Validate device can be upgraded
2. Pre-check - Run pre-upgrade validations
3. Distribute - Download firmware image
4. Activate - Apply new firmware
5. Wait - Wait for stabilization
6. Ping - Verify device is reachable
7. Post-check - Run post-upgrade validations
8. Verification - Confirm version matches target

---

### Mock Mode (Pipeline Simulation)

Simulates the entire upgrade pipeline without any real connections. Use for testing, CI/CD validation, or planning.

```python
from simple_upgrade import UpgradeManager

manager = UpgradeManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_xe",
    connection_mode="mock",  # Mock mode
    golden_image={"version": "17.9.4", "image_name": "flash:c9300.bin"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/tftpboot"}
)

result = manager.upgrade()

# View the simulated pipeline
print(f"Success: {result['success']}")
print(f"Manufacturer: {result['manufacturer']}")
print(f"Model: {result['model']}")
print(f"Commands that would execute: {result['commands_executed']}")
print(f"Execution path: {result['execution_path']}")
```

**Key Features:**
- No actual SSH connection to device
- Simulates all stages with manufacturer-specific outputs
- Returns `commands_executed` list showing what would run
- Returns `execution_path` for tracking class -> function -> line
- Returns `manufacturer`, `model`, and `platform` information

**Mock Output by Manufacturer:**

| Manufacturer | Readiness | Distribute | Activate |
|--------------|-----------|------------|----------|
| Cisco | "Cisco readiness check: Device is ready for upgrade" | `copy http://10.0.0.10/tftpboot/image.bin flash:/image.bin` | `install add file image.bin activate commit` |
| Juniper | "Juniper readiness check: Device is ready for upgrade" | `request system software add http://10.0.0.10/tftpboot/image.bin` | `request system software add image.bin reboot` |
| Arista | "Arista readiness check: Device is ready for upgrade" | `copy http://10.0.0.10/tftpboot/image.bin flash:/image.bin` | `install image flash:/image.bin` |

---

### Dry-Run Mode (Real Connection, Mock Commands)

Connects to the real device but only executes `show` commands; all upgrade commands are mocked. Use for testing without risking an actual upgrade.

```python
from simple_upgrade import UpgradeManager

manager = UpgradeManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_xe",
    connection_mode="dry_run",  # Dry-run mode
    golden_image={"version": "17.9.4", "image_name": "flash:c9300.bin"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/tftpboot"}
)

result = manager.upgrade()

# View what would happen
print(f"Success: {result['success']}")
print(f"Show commands executed: {result['show_commands']}")
print(f"Mocked upgrade commands: {result['mocked_commands']}")
print(f"Execution path: {result['execution_path']}")
```

**Key Features:**
- Establishes real SSH connection to device
- Executes `show version`, `show inventory`, `dir` etc. with real output
- Mocks upgrade commands (`copy`, `install`, `activate`, `commit`)
- Returns `execution_path` showing full call stack
- Returns `show_commands_executed` and `mocked_commands` separately

**Dry-Run Execution Path Example:**

```python
{
    "execution_path": [
        {"class": "DryRunConnection", "function": "open", "line": 169, "stage": ""},
        {"class": "DryRunConnection", "function": "send_command", "line": 183, "stage": "readiness"},
        {"class": "DryRunUpgradeWorkflow", "function": "_run_stage", "line": 405, "stage": "readiness"},
        {"class": "DryRunUpgradeWorkflow", "function": "_mock_readiness", "line": 450, "stage": "readiness"},
        {"class": "DryRunConnection", "function": "send_command", "line": 183, "stage": "distribute"},
        {"class": "DryRunUpgradeWorkflow", "function": "_run_stage", "line": 405, "stage": "distribute"},
        {"class": "DryRunUpgradeWorkflow", "function": "_mock_distribute", "line": 477, "stage": "distribute"},
        # ... continues through all stages
    ]
}
```

---

## Manufacturer-Specific Behavior

The library automatically detects the manufacturer and uses manufacturer-specific commands.

### Cisco Devices (IOS, IOS-XE, NX-OS)

**Detection:** `device_type` contains 'cisco'

**Readiness Check:**
```
Cisco readiness check: Device is ready for upgrade
```

**Distribute Command:**
```
copy http://10.0.0.10/tftpboot/image.bin flash:/image.bin
```

**Activate Command (IOS-XE):**
```
install add file image.bin activate commit
```

**Activate Command (NX-OS):**
```
install image image.bin
```

### Juniper Devices (Junos)

**Detection:** `device_type` contains 'juniper' or 'junos'

**Readiness Check:**
```
Juniper readiness check: Device is ready for upgrade
```

**Distribute Command:**
```
request system software add http://10.0.0.10/tftpboot/image.bin
```

**Activate Command:**
```
request system software add image.bin reboot
```

### Arista Devices (EOS)

**Detection:** `device_type` contains 'arista' or 'eos'

**Readiness Check:**
```
Arista readiness check: Device is ready for upgrade
```

**Distribute Command:**
```
copy http://10.0.0.10/tftpboot/image.bin flash:/image.bin
```

**Activate Command:**
```
install image flash:/image.bin
```

---

## Execution Path Tracking

The execution path feature allows you to trace which classes and functions would be executed during a real run.

### Example: Mock Mode Execution Path

```python
from simple_upgrade import UpgradeManager

manager = UpgradeManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_xe_c9300",
    connection_mode="mock",
    golden_image={"version": "17.9.4", "image_name": "flash:c9300.bin"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/tftpboot"}
)

result = manager.upgrade()

# Print execution path
for step in result['execution_path']:
    print(f"{step['class']} -> {step['function']} (line {step['line']}) [{step['stage']}]")
```

**Output:**
```
MockUpgradeWorkflow -> __init__ (line 268) []
MockUpgradeWorkflow -> _get_manufacturer (line 292) []
MockUpgradeWorkflow -> _get_model (line 306) []
MockUpgradeWorkflow -> _get_platform (line 359) []
MockUpgradeWorkflow -> _init_stages (line 374) []
MockUpgradeWorkflow -> _run_stage (line 396) [readiness]
MockUpgradeWorkflow -> _mock_readiness (line 444) [readiness]
MockUpgradeWorkflow -> _run_stage (line 396) [pre_check]
MockUpgradeWorkflow -> _mock_pre_check (line 458) [pre_check]
MockUpgradeWorkflow -> _run_stage (line 396) [distribute]
MockUpgradeWorkflow -> _mock_distribute (line 471) [distribute]
MockUpgradeWorkflow -> _run_stage (line 396) [activate]
MockUpgradeWorkflow -> _mock_activate (line 497) [activate]
MockUpgradeWorkflow -> _run_stage (line 396) [wait]
MockUpgradeWorkflow -> _mock_wait (line 519) [wait]
MockUpgradeWorkflow -> _run_stage (line 396) [ping]
MockUpgradeWorkflow -> _mock_ping (line 529) [ping]
MockUpgradeWorkflow -> _run_stage (line 396) [post_check]
MockUpgradeWorkflow -> _mock_post_check (line 538) [post_check]
MockUpgradeWorkflow -> _run_stage (line 396) [verification]
MockUpgradeWorkflow -> _mock_verification (line 543) [verification]
```

### Example: Dry-Run Mode Execution Path

```python
manager = UpgradeManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="juniper_junos",
    connection_mode="dry_run",
    golden_image={"version": "22.4R1", "image_name": "junos-juniper-srx-22.4R1.tgz"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/tftpboot"}
)

result = manager.upgrade()

# Print execution path
for step in result['execution_path']:
    print(f"{step['class']} -> {step['function']} (line {step['line']}) [{step['stage']}]")
```

**Output shows both DryRunConnection and DryRunUpgradeWorkflow class interactions:**
```
DryRunConnection -> open (line 169) []
DryRunConnection -> send_command (line 183) [readiness]
DryRunUpgradeWorkflow -> _run_stage (line 405) [readiness]
DryRunUpgradeWorkflow -> _mock_readiness (line 447) [readiness]
DryRunConnection -> send_command (line 183) [readiness]
DryRunConnection -> send_command (line 183) [distribute]
DryRunUpgradeWorkflow -> _run_stage (line 405) [distribute]
DryRunUpgradeWorkflow -> _mock_distribute (line 477) [distribute]
DryRunConnection -> send_command (line 183) [activate]
DryRunUpgradeWorkflow -> _run_stage (line 405) [activate]
DryRunUpgradeWorkflow -> _mock_activate (line 499) [activate]
...
```

---

## Device Model Inference

The library automatically infers the device model from `device_type` - no need to specify exact model.

### Cisco Models

| Device Type | Inferred Model |
|-------------|----------------|
| `cisco_xe_c9300` | C9300 |
| `cisco_xe_c9400` | C9400 |
| `cisco_xe_c9500` | C9500 |
| `cisco_xe_isr4400` | ISR4400 |
| `cisco_xe_isr4300` | ISR4300 |
| `cisco_nxos_n9k` | N9K |
| `cisco_xe` (default) | C9300 |

### Juniper Models

| Device Type | Inferred Model |
|-------------|----------------|
| `juniper_junos_mx` | MX |
| `juniper_junos_qfx` | QFX |
| `juniper_junos_srx` | SRX |
| `juniper_junos_ptx` | PTX |
| `juniper_junos` (default) | MX |

### Arista Models

| Device Type | Inferred Model |
|-------------|----------------|
| `arista_eos_7050` | 7050 |
| `arista_eos_7280` | 7280 |
| `arista_eos_7500` | 7500 |
| `arista_eos` (default) | 7050 |

### Example: Automatic Model Inference

```python
from simple_upgrade import UpgradeManager

# Model is automatically inferred from device_type
manager = UpgradeManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_xe_c9400",  # Model inferred as C9400
    connection_mode="mock",
    golden_image={"version": "17.9.4", "image_name": "flash:c9400.bin"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/tftpboot"}
)

result = manager.upgrade()
print(f"Model: {result['model']}")  # Output: C9400
print(f"Manufacturer: {result['manufacturer']}")  # Output: Cisco
```

---

## Device Model Mapping

The library supports a flexible system for mapping multiple device model names to a single device profile.

### Device Profile Models List

Device profiles can include a `models` list that defines all model names that should match this profile:

```json
{
  "manufacturer": "Cisco",
  "model": "c9300",
  "models": ["C9300", "C9300L", "C9300X", "C9300UX"],
  "mode": "switch",
  "series": "Catalyst 9300",
  ...
}
```

### Using `match_model_to_profile()`

The `match_model_to_profile()` function finds the profile for a given model:

```python
from simple_upgrade import match_model_to_profile

# Match C9300 to its profile
profile = match_model_to_profile('C9300', 'cisco')
print(profile['series'])  # Output: Catalyst 9300

# Match C9300L (in models list) to the same profile
profile = match_model_to_profile('C9300L', 'cisco')
print(profile['series'])  # Output: Catalyst 9300
```

### Using `find_device_profile()` with Model

The `find_device_profile()` function also checks the models list:

```python
from simple_upgrade import find_device_profile

# Find profile for any C9300 variant
profiles = find_device_profile(manufacturer='cisco', model='C9300X')
if profiles:
    profile = profiles[0]
    print(profile['model'])  # Output: c9300
```

### Benefits of Models List

- **Flexibility**: One profile can cover multiple model variants
- **Simplified maintenance**: Update one profile for similar devices
- **Backward compatibility**: Old model names can still work

### Example: Using Model Mapping in Mock Mode

```python
from simple_upgrade import UpgradeManager

# All these model types will use the same c9300 profile
for model in ['C9300', 'C9300L', 'C9300X', 'C9300UX']:
    manager = UpgradeManager(
        host="192.168.1.1",
        username="admin",
        password="password",
        device_type="cisco_xe",
        connection_mode="mock",
        golden_image={"version": "17.9.4", "image_name": f"flash:{model}.bin"},
        file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/tftpboot"}
    )
    manager.connect()
    result = manager.upgrade()
    print(f"{model}: {result['manufacturer']} {result['model']}")
```

---

## Complete Example: Mock Mode with Execution Path

## Complete Example: Mock Mode with Execution Path

```python
from simple_upgrade import UpgradeManager
import json

# Setup upgrade manager in mock mode
manager = UpgradeManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="juniper_junos_mx",
    connection_mode="mock",
    golden_image={
        "version": "22.4R1",
        "image_name": "junos-juniper-srx-22.4R1.tgz"
    },
    file_server={
        "ip": "10.0.0.10",
        "protocol": "http",
        "base_path": "/tftpboot"
    }
)

# Execute upgrade
result = manager.upgrade()

# Print detailed results
print("=" * 60)
print("UPGRADE SIMULATION RESULT")
print("=" * 60)
print(f"Success: {result['success']}")
print(f"Manufacturer: {result['manufacturer']}")
print(f"Model: {result['model']}")
print(f"Platform: {result['platform']}")

print("\nSTAGES:")
for name, stage in result['stages'].items():
    print(f"  {name}: {stage['status']} - {stage['message']}")

print("\nCOMMANDS EXECUTED:")
for cmd in result['commands_executed']:
    print(f"  [{cmd.get('stage', 'N/A')}] {cmd.get('command', 'N/A')}")

print("\nEXECUTION PATH:")
for step in result['execution_path']:
    print(f"  {step['class']} -> {step['function']} (line {step['line']})")

# Save results to file
with open('upgrade_simulation.json', 'w') as f:
    json.dump(result, f, indent=2)
```

---

## Complete Example: Dry-Run Mode with Execution Path

```python
from simple_upgrade import UpgradeManager
import json

# Setup upgrade manager in dry-run mode
manager = UpgradeManager(
    host="192.168.1.1",  # Real device IP
    username="admin",
    password="password",
    device_type="arista_eos_7280",
    connection_mode="dry_run",
    golden_image={
        "version": "4.28.3F",
        "image_name": "EPE-4.28.3F.swi"
    },
    file_server={
        "ip": "10.0.0.10",
        "protocol": "http",
        "base_path": "/tftpboot"
    }
)

# Execute dry-run
result = manager.upgrade()

print("=" * 60)
print("DRY-RUN RESULT")
print("=" * 60)
print(f"Success: {result['success']}")

print("\nSHOW COMMANDS EXECUTED (REAL):")
for cmd in result.get('show_commands', []):
    print(f"  {cmd}")

print("\nUPGRADE COMMANDS (MOCKED):")
for cmd in result.get('mocked_commands', []):
    print(f"  {cmd}")

print("\nEXECUTION PATH:")
for step in result['execution_path']:
    print(f"  {step['class']} -> {step['function']} (line {step['line']}) [{step['stage']}]")
```

---

## Summary

| Mode | Connection | Use Case |
|------|------------|----------|
| `normal` | Real SSH | Actual firmware upgrade |
| `mock` | None | Testing, CI/CD, planning |
| `dry_run` | Real (show only) | Safety check without upgrade |

| Feature | Mock Mode | Dry-Run Mode | Normal Mode |
|---------|-----------|--------------|-------------|
| Real SSH | No | Yes | Yes |
| Show commands | Mocked | Real | Real |
| Upgrade commands | Mocked | Mocked | Real |
| Execution path | Yes | Yes | No |
| Manufacturer-specific | Yes | Yes | Yes |
| Model inference | Yes | Yes | Yes |

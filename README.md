# simple-upgrade

A simple Python package for network device firmware upgrades.

## Features

- Connect to network devices via SSH
- Gather device information (manufacturer, model, version)
- Execute upgrade workflow stages:
  - Readiness checks
  - Pre-upgrade validations
  - Firmware distribution
  - Firmware activation
  - Post-upgrade verification
- Support for Cisco IOS, IOS-XE, NX-OS, and more

## Connection Modes

The package supports three connection modes:

| Mode | Description |
|------|-------------|
| `normal` | Real SSH connection with full upgrade execution |
| `mock` | Simulate entire pipeline without real connections (testing/CI/CD) |
| `dry_run` | Connect to device but only execute show commands; mock upgrade commands |

See [USAGE.md](USAGE.md) for detailed documentation on all connection modes.

## Connection Management

The package includes a `ConnectionManager` class that provides a unified interface
to create connection objects for multiple libraries:

```python
from simple_upgrade import ConnectionManager

conn = ConnectionManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_xe"
)

# Get scrapli connection
sc = conn.get_connection(channel='scrapli')

# Get netmiko connection
nm = conn.get_connection(channel='netmiko')

# Get unicon connection
uc = conn.get_connection(channel='unicon')

conn.disconnect()
```

| Channel | Library | Use Case |
|---------|---------|----------|
| `scrapli` | scrapli | Modern async SSH connections |
| `netmiko` | netmiko | Classic network automation |
| `unicon` | genie/pyats | Genie/Unicon connections |

## Installation

```bash
pip install simple-upgrade
```

## Quick Start

```python
from simple_upgrade import UpgradeManager

# Create upgrade manager
# device_type is REQUIRED - specify the platform
# Supported: cisco_ios, cisco_xe, cisco_nxos, juniper_junos, arista_eos, etc.
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

### Mock Mode (Pipeline Simulation - No Real Connection)

Simulate the upgrade pipeline without connecting to any device:

```python
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
print(f"Pipeline would succeed: {result['success']}")
print(f"Manufacturer: {result['manufacturer']}")
print(f"Commands that would execute: {result['commands_executed']}")
```

### Dry-Run Mode (Real Connection, Mock Upgrade Commands)

Connect to the device but only execute show commands; mock upgrade commands:

```python
manager = UpgradeManager(
    host="192.168.1.1",  # Real device
    username="admin",
    password="password",
    device_type="cisco_xe",
    connection_mode="dry_run",  # Dry-run mode
    golden_image={"version": "17.9.4", "image_name": "flash:c9300.bin"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/tftpboot"}
)

result = manager.upgrade()
print(f"Show commands executed: {result['show_commands']}")
print(f"Upgrade commands mocked: {result['mocked_commands']}")
print(f"Execution path: {result['execution_path']}")
```

See [USAGE.md](USAGE.md) for complete documentation on all connection modes.

## Usage

### 1. Connect to Device

```python
manager = UpgradeManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    port=22,
    device_type="cisco_xe"  # REQUIRED: device type/platform
)
manager.connect()
```

### 2. Get Device Information

```python
device_info = manager.device.gather_info()
print(f"Model: {device_info['model']}")
print(f"Version: {device_info['version']}")
```

### 3. Sync Device Information (Detailed)

Use the `SyncManager` to fetch detailed device information including version, model, uptime, boot method, serial, and more. Also includes `tacacs_source_interface` if configured.

```python
from simple_upgrade import ConnectionManager, SyncManager

# Get connection and platform
cm = ConnectionManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_xe"
)
conn = cm.get_connection(channel='scrapli')

# Get platform from connection manager
platform = cm.get_platform(channel='scrapli')

# Fetch detailed device info
sync = SyncManager(connection_manager=cm, platform=platform)
device_info = sync.fetch_info()

print(f"Manufacturer: {device_info['manufacturer']}")
print(f"Model: {device_info['model']}")
print(f"Version: {device_info['version']}")
print(f"Hostname: {device_info['hostname']}")
print(f"Serial: {device_info['serial_number']}")
print(f"Uptime: {device_info['uptime']}")
print(f"Boot Method: {device_info['boot_method']}")
print(f"Flash Size: {device_info['flash_size']}")
print(f"Memory Size: {device_info['memory_size']}")
print(f"TACACS Source Interface: {device_info['tacacs_source_interface']}")
```

### 4. Run Upgrade

```python
result = manager.upgrade()

# Check individual stage results
for stage_name, stage_result in result['stages'].items():
    print(f"{stage_name}: {'OK' if stage_result['success'] else 'FAIL'}")
```

### 5. Disconnect

```python
manager.disconnect()
```

## Upgrade Workflow

The upgrade process follows these stages:

1. **Readiness** - Validate device can be upgraded
2. **Pre-check** - Run pre-upgrade validations
3. **Distribute** - Download firmware image from file server
4. **Activate** - Apply new firmware
5. **Wait** - Wait for device stabilization
6. **Ping** - Verify device is reachable
7. **Post-check** - Run post-upgrade validations
8. **Verification** - Confirm version matches target

## Supported Devices

- Cisco IOS
- Cisco IOS-XE (recommended: c9300 series only)
- Juniper Junos
- Arista EOS
- Palo Alto PAN-OS

**Note:** For Cisco devices, only c9300 series models are currently supported. The device_type must be `cisco_iosxe`.

## Manufacturer-Specific Behavior

The library automatically detects the manufacturer and uses manufacturer-specific commands:

| Manufacturer | Readiness | Distribute | Activate |
|--------------|-----------|------------|----------|
| Cisco | Cisco readiness check | `copy http://... flash:/...` | `install add file ... activate commit` |
| Juniper | Juniper readiness check | `request system software add ...` | `request system software add ... reboot` |
| Arista | Arista readiness check | `copy http://... flash:/...` | `install image flash:/...` |
| Palo Alto | PAN-OS readiness check | `download...` | `request system software...` |

## Device Model Inference

The library automatically infers the device model from `device_type`. No need to specify exact model.

**Note:** For Cisco IOS-XE, only c9300 series models are supported (C9300, C9300L, C9300X, etc.).

| Device Type | Inferred Model |
|-------------|----------------|
| `cisco_xe_c9300` | C9300 |
| `cisco_xe_c9300l` | C9300L |
| `cisco_xe_c9300x` | C9300X |
| `juniper_junos_mx` | MX |
| `arista_eos_7280` | 7280 |

See [USAGE.md](USAGE.md) for more details.

## Requirements

- Python 3.10+
- scrapli (for SSH connections)
- genie/pyats (for unicon library)

## device_type

The `device_type` parameter is **required** when creating an `UpgradeManager`.
It tells scrapli which driver to use for the connection.

| Device Type | Scrapli Platform | Netmiko Platform | Unicon OS |
|-------------|------------------|------------------|-----------|
| `cisco_ios` | `cisco_ios` | `cisco_ios` | `ios` |
| `cisco_xe` | `cisco_iosxe` | `cisco_ios` | `iosxe` |
| `cisco_nxos` | `cisco_nxos` | `cisco_nxos` | `nxos` |
| `juniper_junos` | `juniper_junos` | `juniper` | `junos` |
| `arista_eos` | `arista_eos` | `arista_eos` | `eos` |
| `paloalto_panos` | `paloalto_panos` | `paloalto_panos` | `panos` |

**Note:** The package automatically maps the `device_type` to the appropriate
platform names for each library. You only need to provide `device_type` (e.g., `cisco_xe`).

## ConnectionManager

The `ConnectionManager` class provides a unified interface for creating connections
using different libraries.

### Parameters

| Parameter | Description |
|-----------|-------------|
| `host` | IP address or hostname |
| `username` | SSH username |
| `password` | SSH password |
| `device_type` | Device type/platform (required for scrapli) |
| `port` | SSH port (default: 22) |
| `timeout` | Command timeout in seconds (default: 30) |
| `connection_timeout` | Connection timeout in seconds (default: 30) |
| `enable_mode` | Whether to enter enable mode (default: False) |
| `enable_password` | Enable password if required |
| `secret` | Secret/enable password for privileged mode (optional) |
| `auth_strict_key` | Strict SSH key checking (default: False) |
| `transport` | Transport type (default: "ssh") |

### Methods

| Method | Description |
|--------|-------------|
| `get_connection(channel)` | Get connection object for scrapli/netmiko/unicon |
| `disconnect(channel)` | Disconnect from device (optional channel param) |
| `is_connected(channel)` | Check if connected |
| `get_active_channel()` | Get currently active connection |
| `get_platform(channel)` | Get platform name for channel |
| `get_connection_with_platform(channel)` | Get connection and platform together |

### Supported Channels

| Channel | Library |
|---------|---------|
| `scrapli` | scrapli (SSH connections) |
| `netmiko` | netmiko (classic network automation) |
| `unicon` | genie/pyats (device operations) |

**Note:** The package primarily uses scrapli for connections. Unicon is used internally for file distribution and activation commands.

## SyncManager

The `SyncManager` class fetches detailed device information using platform-specific commands.

### Device Information Attributes

| Attribute | Description |
|-----------|-------------|
| `manufacturer` | Device manufacturer (Cisco, Juniper, Arista, Palo Alto) |
| `model` | Device model |
| `version` | Parsed software version |
| `current_version` | Current software version |
| `hostname` | Device hostname |
| `serial` / `serial_number` | Device serial number |
| `platform` | Platform name (cisco_ios, cisco_iosxe, etc.) |
| `uptime` | Device uptime |
| `boot_method` | How the device boots (image file, config register) |
| `boot_mode` | Boot mode (NX-OS specific) |
| `ios_image` | IOS image path |
| `config_register` | Configuration register value |
| `flash_size` | Flash memory size |
| `memory_size` | System memory size |

### Usage

```python
from simple_upgrade import ConnectionManager, SyncManager

cm = ConnectionManager(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_xe"
)
conn = cm.get_connection(channel='scrapli')

platform = cm.get_platform(channel='scrapli')
sync = SyncManager(connection_manager=cm, platform=platform)
device_info = sync.fetch_info()
```

### Standalone Function

You can also use `sync_device()` for a simpler approach:

```python
from simple_upgrade import sync_device

device_info = sync_device(
    host="192.168.1.1",
    username="admin",
    password="password",
    platform="cisco_iosxe"
)
```

## SyncManager Output

The `SyncManager.fetch_info()` returns the following device information:

| Attribute | Description |
|-----------|-------------|
| `manufacturer` | Device manufacturer (Cisco, Juniper, Arista) |
| `model` | Device model |
| `version` | Software version |
| `hostname` | Device hostname |
| `serial_number` | Device serial number |
| `uptime` | Device uptime |
| `boot_method` | Boot image path |
| `config_register` | Configuration register |
| `tacacs_source_interface` | TACACS+ source interface (if configured) |
| `flash_size` | Flash memory size |
| `memory_size` | System memory size |

## UpgradePackage Class

For a more object-oriented approach, use the `UpgradePackage` class which maintains shared state across stages:

```python
from simple_upgrade import UpgradePackage

upgrade = UpgradePackage(
    host="192.168.1.1",
    username="admin",
    password="password",
    device_type="cisco_xe",
    golden_image={"version": "17.9.4", "image_name": "flash:c9300.bin"},
    file_server={"ip": "10.0.0.10", "protocol": "http", "base_path": "/tftpboot"}
)

upgrade.sync()           # Updates device_info
upgrade.readiness()      # Updates readiness_result
upgrade.pre_check()      # Updates pre_check_result
upgrade.activate()       # Updates activate_result
upgrade.wait()           # Updates wait_result
upgrade.post_check()     # Updates post_check_result
upgrade.verification()   # Updates verification_result

if upgrade.success:
    print("Upgrade successful")
else:
    print(f"Failed at stage: {upgrade.failed_stage}")
```

## License

Apache License 2.0

## Author

Tarani Debnath

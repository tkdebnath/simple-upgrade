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

Use the `SyncManager` to fetch detailed device information including version, model, uptime, boot method, serial, and more:

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
- Cisco IOS-XE
- Cisco NX-OS
- Juniper Junos (coming soon)
- Arista EOS (coming soon)

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
| `scrapli` | scrapli |
| `netmiko` | netmiko |
| `unicon` | genie/pyats |

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

## License

Apache License 2.0

## Author

Tarani Debnath

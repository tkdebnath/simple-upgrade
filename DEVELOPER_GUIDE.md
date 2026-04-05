# Developer Guide — Adding New Models & Manufacturers

This guide explains how to extend the `simple-upgrade` framework to support new hardware models and new manufacturers (e.g., Arista, Juniper).

---

## Table of Contents

- [Adding a New Hardware Model (Same Manufacturer)](#adding-a-new-hardware-model-same-manufacturer)
- [Adding a New Manufacturer](#adding-a-new-manufacturer)
- [Architecture Reference](#architecture-reference)

---

## Adding a New Hardware Model (Same Manufacturer)

Adding a new Cisco model (e.g., Catalyst 9500) requires **zero Python changes**. It is purely a JSON configuration task.

### Step 1: Decide on Group Inheritance

Check if an existing group template already covers your device's upgrade workflow:

```
src/simple_upgrade/device_profiles/cisco/groups/
├── install_mode.json     # Standard "install add/activate/commit" devices
└── lab_vios.json         # Lab virtual IOS overrides
```

- If your new model uses `install add file flash:/<image> activate commit` → reuse `install_mode`
- If it uses a completely different workflow (e.g., `request platform software install`, bundle mode) → create a new group file

### Step 2: Create the Device Profile JSON

Create a new file in `src/simple_upgrade/device_profiles/cisco/`:

```bash
# Example: src/simple_upgrade/device_profiles/cisco/catalyst_9500.json
```

```json
{
  "manufacturer": "Cisco",
  "model": "catalyst_9500",
  "models": [
    "C9500.*",
    "C9500-16X",
    "C9500-32C",
    "C9500-48Y4C"
  ],
  "group": "install_mode",
  "mode": "switch",
  "series": "Catalyst 9500",
  "platform": ["IOS-XE", "cisco_xe"],
  "device_type": "cisco_iosxe",
  "description": "Cisco Catalyst 9500 Series High-Performance Switch",
  "flash_size": "16GB",
  "verification_commands": {
    "check_version": "show version | include Version",
    "check_uptime": "show version | include uptime",
    "check_model": "show version | include Processor",
    "check_serial": "show inventory | include PID"
  },
  "config_commands": {
    "enter_config": "configure terminal",
    "exit_config": "end",
    "save_config": "write memory",
    "reload_device": "reload"
  }
}
```

#### Key fields explained:

| Field | What it does |
|-------|--------------|
| `model` | Unique identifier for this profile (used in logs and reports) |
| `models` | **List of regex patterns** matched against the model string from `show version`. The first profile where any pattern matches wins |
| `group` | Name of the group template in `groups/` to inherit from. Omit this key to create a standalone profile |
| `platform` | List of platform identifiers matched against the device's reported OS. Supports multiple variants for flexibility |
| `commands` | If omitted, all check commands are inherited from the group. Override here to add or replace individual commands |

### Step 3: (Optional) Override Specific Commands

If your model needs most commands from the group but a few different ones, add only the overrides. The profile's `commands` block **completely replaces** the group's `commands` block (it does not merge key-by-key).

To add a model-specific command while keeping the group's commands, copy the full `commands` block from the group and add your extras:

```json
{
  "model": "catalyst_9500",
  "group": "install_mode",
  "commands": {
    "show_version": "show version",
    "show_inventory": "show inventory",
    "show_running_config": "show running-config",
    "show_environment": "show environment all",
    "show_module": "show module",
    "show_redundancy": "show redundancy switchover",
    "// ... everything from install_mode plus your extras": ""
  }
}
```

### Step 4: (Optional) Create a New Group

If your model requires a fundamentally different upgrade workflow, create a new group:

```bash
# Example: src/simple_upgrade/device_profiles/cisco/groups/bundle_mode.json
```

```json
{
  "commands": {
    "show_version": "show version",
    "show_boot": "show boot",
    "show_file_systems": "show file systems"
  },
  "upgrade_commands": {
    "copy_image": "copy {protocol}://{server}/{path}/{image} flash:/{image}",
    "verify_image": "verify /md5 flash:/{image} {md5}",
    "install_add": "request platform software package install switch all file flash:/{image} auto-copy",
    "flash_cleanup": "request platform software package clean switch all"
  },
  "boot_commands": [
    "no boot system",
    "boot system flash:/{image}"
  ],
  "default_image_location": "flash:/"
}
```

### Step 5: Validate

The `ProfileValidator` runs automatically when `UpgradePackage` is initialized. It will catch:

- **Missing required fields** in your JSON
- **Overlapping model patterns** across profiles (e.g., if two profiles both claim `C9500.*`)
- **Invalid JSON syntax**

You can also validate manually:

```python
from simple_upgrade.config_validator import ProfileValidator

validator = ProfileValidator("src/simple_upgrade/device_profiles")
validator.validate_all()  # Raises ProfileValidationError on issues
print("All profiles valid ✓")
```

### Step 6: Test

```python
from simple_upgrade import UpgradePackage

pkg = UpgradePackage(
    host="10.0.0.1",
    username="admin",
    password="admin",
    platform="cisco_iosxe",
    connection_mode="dry_run",    # safe — no changes to device
    golden_image={
        "version": "17.13.1",
        "image_name": "cat9k_iosxe.17.13.01.SPA.bin",
        "image_size": 1000000000,
        "md5": "abc123"
    },
    file_server={"ip": "10.0.0.10", "base_path": "/images"}
)

# sync will detect model and match to your new profile
result = pkg.run_stage("sync")
print(result.data.get("device_profile_id"))
# Should print: "catalyst_9500"
```

### Checklist — New Model

- [ ] JSON profile created in `device_profiles/cisco/`
- [ ] `models` list contains regex patterns covering all hardware variants
- [ ] `group` references a valid group template (or omitted for standalone)
- [ ] `platform` list covers all OS identifiers the device may report
- [ ] No overlapping model patterns with existing profiles
- [ ] Validated with `ProfileValidator`
- [ ] Tested with `connection_mode="dry_run"` on a real device

---

## Adding a New Manufacturer

Adding a new manufacturer (e.g., Arista, Juniper) requires changes across four layers:

### Overview of Required Changes

```
Step 1: Device Profiles         → device_profiles/arista/
Step 2: Manufacturer Module     → manufacturers/arista/
Step 3: Module Registration     → manufacturers/__init__.py
Step 4: Platform Whitelist      → upgrade_package.py
```

### Step 1: Create Device Profiles

```bash
mkdir -p src/simple_upgrade/device_profiles/arista/groups/
```

Create a group template:

```bash
# src/simple_upgrade/device_profiles/arista/groups/eos_standard.json
```

```json
{
  "commands": {
    "show_version": "show version",
    "show_inventory": "show inventory",
    "show_running_config": "show running-config",
    "show_interfaces_status": "show interfaces status",
    "show_ip_route": "show ip route summary",
    "show_ip_bgp_summary": "show ip bgp summary",
    "show_boot": "show boot-config",
    "show_extensions": "show extensions",
    "show_stp": "show spanning-tree"
  },
  "upgrade_commands": {
    "copy_image": "copy {protocol}://{server}/{path}/{image} flash:/{image}",
    "verify_image": "verify /md5 flash:/{image}",
    "install_add": "install source flash:/{image}",
    "flash_cleanup": "delete flash:/{image}"
  },
  "boot_commands": [
    "boot system flash:/{image}"
  ],
  "default_image_location": "flash:/"
}
```

Create a device profile:

```bash
# src/simple_upgrade/device_profiles/arista/7050x.json
```

```json
{
  "manufacturer": "Arista",
  "model": "arista_7050x",
  "models": ["DCS-7050.*", "7050TX.*", "7050CX.*"],
  "group": "eos_standard",
  "mode": "switch",
  "series": "Arista 7050X",
  "platform": ["eos", "arista_eos"],
  "device_type": "arista_eos",
  "description": "Arista 7050X Series Data Center Switch",
  "flash_size": "4GB"
}
```

### Step 2: Create the Manufacturer Module

Create the module directory:

```bash
mkdir -p src/simple_upgrade/manufacturers/arista/
```

#### 2a. `__init__.py` — Module Registration

```python
# src/simple_upgrade/manufacturers/arista/__init__.py
"""
Arista manufacturer package.
"""

from . import sync
from . import readiness
from . import distribution
from . import activation
from . import checks
from . import verification
from . import diff

SUPPORTED_PLATFORMS = ['arista_eos', 'eos']
```

#### 2b. `sync.py` — Device Discovery

This is the most critical file. It must parse `show version` output and populate `ctx.device_info`:

```python
# src/simple_upgrade/manufacturers/arista/sync.py
"""
Arista sync task — device discovery and profile matching.
"""

import re
from ...registry import register_stage
from ...base import BaseTask, StageResult


@register_stage('sync', 'arista')     # ← 'arista' maps to manufacturer key
class AristaSyncTask(BaseTask):
    @property
    def name(self) -> str: return "sync"

    def run(self, **kwargs) -> StageResult:
        """Fetch Arista device information and match to JSON profile."""

        if self.ctx.connection_mode != "normal":
            self.ctx.device_info.hostname = "MOCK-ARISTA"
            self.ctx.device_info.manufacturer = "Arista"
            self.ctx.device_info.model = "DCS-7050TX-MOCK"
            self.ctx.device_info.version = "4.28.0F"
            return self._success("[MOCK] Arista device info synced")

        # 1. Send 'show version' via Scrapli
        res = self.scrapli.send_command("show version")

        # 2. Parse output (use Genie or regex)
        output = res.result
        # ... parse model, version, hostname, serial from output ...

        # 3. Populate context
        self.ctx.device_info.manufacturer = "Arista"
        self.ctx.device_info.model = parsed_model
        self.ctx.device_info.version = parsed_version
        self.ctx.device_info.hostname = parsed_hostname
        self.ctx.device_info.serial = parsed_serial

        # 4. Match to JSON profile (reuse the profile loader)
        self._match_device_profile()

        return self._success(f"Discovered Arista {parsed_model}")

    def _match_device_profile(self):
        """Scan device_profiles/arista/ for a matching profile."""
        import os, json

        profiles_dir = os.path.join(
            os.path.dirname(__file__), '..', '..', 'device_profiles', 'arista'
        )
        model = self.ctx.device_info.model or ""

        for filename in os.listdir(profiles_dir):
            if not filename.endswith('.json') or filename == '__init__.py':
                continue

            filepath = os.path.join(profiles_dir, filename)
            with open(filepath) as f:
                profile = json.load(f)

            for pattern in profile.get('models', []):
                if re.match(pattern, model, re.IGNORECASE):
                    # Load group inheritance
                    if 'group' in profile:
                        group_path = os.path.join(profiles_dir, 'groups', f"{profile['group']}.json")
                        if os.path.exists(group_path):
                            with open(group_path) as gf:
                                group = json.load(gf)
                            group.update(profile)
                            profile = group

                    self.ctx.device_info.extra['device_profile'] = profile
                    return

        self._log(f"Warning: no profile matched model '{model}'")
```

> **Critical:** The `@register_stage('sync', 'arista')` decorator is what makes the registry dispatch to this class when `manufacturer="arista"`.

#### 2c. Remaining Stage Files

Each stage follows the same pattern. Here's the minimal skeleton for each:

```python
# src/simple_upgrade/manufacturers/arista/checks.py
from ...registry import register_stage
from ...base import BaseTask, StageResult

@register_stage('pre_check', 'arista')
@register_stage('post_check', 'arista')
class AristaCheckTask(BaseTask):
    @property
    def name(self) -> str: return self.ctx.current_stage  # "pre_check" or "post_check"

    def run(self, **kwargs) -> StageResult:
        profile = self.ctx.device_info.extra.get('device_profile', {})
        commands = profile.get('commands', {})
        # ... iterate commands, save outputs to files ...
        return self._success(f"Captured {len(commands)} commands")
```

```python
# src/simple_upgrade/manufacturers/arista/readiness.py
@register_stage('readiness', 'arista')
class AristaReadinessTask(BaseTask):
    ...
```

```python
# src/simple_upgrade/manufacturers/arista/distribution.py
@register_stage('distribute', 'arista')
class AristaDistributeTask(BaseTask):
    ...
```

```python
# src/simple_upgrade/manufacturers/arista/activation.py
@register_stage('activate', 'arista')
class AristaActivationTask(BaseTask):
    ...
```

```python
# src/simple_upgrade/manufacturers/arista/verification.py
@register_stage('verification', 'arista')
class AristaVerificationTask(BaseTask):
    ...
```

```python
# src/simple_upgrade/manufacturers/arista/diff.py
@register_stage('diff', 'arista')
class AristaDiffTask(BaseTask):
    ...
```

> **Tip:** If your manufacturer shares identical logic for certain stages (e.g., diff, checks), you can register the existing Cisco class under the new manufacturer key, or create a `generic` implementation.

### Step 3: Register the Module

Edit `src/simple_upgrade/manufacturers/__init__.py`:

```python
"""
Manufacturers - Plugin-based registry for manufacturer-specific logic.
"""

from . import cisco
from . import arista     # ← Add this line
```

This import triggers all `@register_stage` decorators in the Arista module, populating the global registry.

### Step 4: Update the Platform Whitelist

Edit `src/simple_upgrade/upgrade_package.py` — find the `SUPPORTED_DEVICES` dictionary and add the new manufacturer:

```python
SUPPORTED_DEVICES = {
    "cisco": ["cisco-ios-xe", "cisco_xe", "cisco_iosxe", "iosxe"],
    "arista": ["arista_eos", "eos"],       # ← Add this line
}
```

### Step 5: Test

```python
from simple_upgrade import UpgradePackage

pkg = UpgradePackage(
    host="10.0.0.50",
    username="admin",
    password="admin",
    platform="arista_eos",          # ← New platform
    manufacturer="arista",          # ← New manufacturer
    connection_mode="dry_run",
    golden_image={
        "version": "4.30.1F",
        "image_name": "EOS-4.30.1F.swi",
        "image_size": 500000000,
        "md5": "def456..."
    },
    file_server={"ip": "10.0.0.10", "base_path": "/arista"}
)

result = pkg.run_stage("sync")
print(f"Manufacturer: {pkg.ctx.device_info.manufacturer}")
print(f"Model:        {pkg.ctx.device_info.model}")
print(f"Profile:      {pkg.ctx.device_info.extra.get('device_profile', {}).get('model')}")
```

### Checklist — New Manufacturer

- [ ] Device profiles created in `device_profiles/<manufacturer>/`
- [ ] Group template(s) created in `device_profiles/<manufacturer>/groups/`
- [ ] Manufacturer module created at `manufacturers/<manufacturer>/`
- [ ] All 7 stage files created with `@register_stage` decorators:
  - [ ] `sync.py` — device discovery + profile matching
  - [ ] `readiness.py` — pre-flight validation
  - [ ] `checks.py` — pre/post check snapshots
  - [ ] `distribution.py` — file transfer
  - [ ] `activation.py` — install/upgrade execution
  - [ ] `verification.py` — post-upgrade version check
  - [ ] `diff.py` — pre/post comparison
- [ ] `manufacturers/__init__.py` updated with `from . import <manufacturer>`
- [ ] `upgrade_package.py` → `SUPPORTED_DEVICES` updated with new platform strings
- [ ] Profile validation passes (`ProfileValidator`)
- [ ] Tested with `connection_mode="dry_run"` or `connection_mode="mock"`

---

## Architecture Reference

### How the Registry Dispatches Stages

```
UpgradePackage.run_stage("distribute")
        │
        ▼
TaskRegistry.execute_stage("distribute", ctx)
        │
        ├── Looks up key: ("distribute", "cisco")
        │         │
        │         ▼
        │   CiscoDistributeTask (registered via @register_stage)
        │         │
        │         ▼
        │   task.execute() → task.run() → StageResult
        │
        └── If not found: looks up ("distribute", "generic")
                  │
                  ▼
            Falls back to generic implementation or raises ValueError
```

### The `@register_stage` Decorator

```python
from simple_upgrade.registry import register_stage

@register_stage('distribute', 'cisco')
class CiscoDistributeTask(BaseTask):
    ...
```

This single line registers your class into the global `TaskRegistry` at import time. When the orchestrator needs to run the `distribute` stage for a `cisco` device, it looks up `("distribute", "cisco")` and instantiates your class.

### The `BaseTask` Contract

Every stage implementation must:

1. **Extend `BaseTask`**
2. **Define `name` property** — returning the stage name string
3. **Implement `run(**kwargs) → StageResult`** — the core execution logic
4. **Use `self._success()` / `self._fail()`** — to return structured results
5. **Access context via `self.ctx`** — device info, golden image, file server, stage results

```python
class BaseTask(ABC):
    ctx: ExecutionContext         # The global backpack
    scrapli                      # Shortcut: self.ctx.cm.get_connection('scrapli')
    unicon                       # Shortcut: self.ctx.cm.get_connection('unicon')

    def run(self, **kwargs) -> StageResult:     # ← You implement this
        ...

    def _success(msg, data=None, command=None) -> StageResult
    def _fail(msg, errors=None, command=None) -> StageResult
```

### The `ExecutionContext` Backpack

All stages share this context object:

| Attribute | Type | Description |
|-----------|------|-------------|
| `ctx.cm` | `ConnectionManager` | SSH connection manager |
| `ctx.golden_image` | `GoldenImage` | Target firmware details |
| `ctx.file_server` | `FileServer` | File server configuration |
| `ctx.device_info` | `DeviceInfo` | Discovered device information |
| `ctx.device_info.extra['device_profile']` | `dict` | Resolved JSON profile (after sync) |
| `ctx.connection_mode` | `str` | `normal`, `mock`, or `dry_run` |
| `ctx.stage_results` | `dict` | Results from completed stages |
| `ctx.errors` | `list[str]` | Accumulated error messages |
| `ctx.failed_stage` | `str \| None` | First stage that failed |
| `ctx.data` | `dict` | Arbitrary data shared between stages |

### File Structure After Adding Arista

```
src/simple_upgrade/
├── base.py
├── registry.py
├── upgrade_package.py
├── connection_manager.py
├── config_validator.py
├── logger.py
├── device_profiles/
│   ├── cisco/
│   │   ├── groups/
│   │   │   ├── install_mode.json
│   │   │   └── lab_vios.json
│   │   ├── catalyst_9300x.json
│   │   └── catalyst_VIOS.json
│   └── arista/                        ← NEW
│       ├── groups/
│       │   └── eos_standard.json      ← NEW
│       └── 7050x.json                 ← NEW
├── manufacturers/
│   ├── __init__.py                    ← MODIFIED (add 'from . import arista')
│   ├── cisco/
│   │   ├── __init__.py
│   │   ├── sync.py
│   │   ├── readiness.py
│   │   ├── distribution.py
│   │   ├── activation.py
│   │   ├── checks.py
│   │   ├── verification.py
│   │   └── diff.py
│   └── arista/                        ← NEW
│       ├── __init__.py                ← NEW
│       ├── sync.py                    ← NEW
│       ├── readiness.py               ← NEW
│       ├── distribution.py            ← NEW
│       ├── activation.py              ← NEW
│       ├── checks.py                  ← NEW
│       ├── verification.py            ← NEW
│       └── diff.py                    ← NEW
```

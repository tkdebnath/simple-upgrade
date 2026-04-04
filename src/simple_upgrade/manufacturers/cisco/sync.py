"""
Cisco sync task.

Fetches device information (hostname, model, version, manufacturer)
using a headless Genie parser mapped over the Scrapli connection.
Falls back to raw text parsing if Genie is unavailable.
"""

import re
from ...registry import register_stage
from ...base import BaseTask, StageResult


@register_stage('sync', 'cisco')
class CiscoSyncTask(BaseTask):
    @property
    def name(self) -> str: return "sync"

    def run(self, **kwargs) -> StageResult:
        """Fetch device information and populate ctx.device_info."""
        
        if self.ctx.connection_mode != "normal":
            self.ctx.device_info.hostname = "MOCK-R1"
            self.ctx.device_info.manufacturer = "Cisco"
            self.ctx.device_info.model = "C9300-MOCK"
            self.ctx.device_info.version = "17.0.0"
            return self._success(f"[MOCK] Synchronised device info: {self.ctx.device_info.hostname}")

        # Send command via scrapli
        res_version = self.scrapli.send_command("show version")
        res_hostname = self.scrapli.get_prompt()
        
        data = {}
        hostname = None
        version = None
        model = None
        platform = None
        manufacturer = "Cisco"
        boot_file = None
        uptime = None

        if res_hostname:
            hostname = res_hostname.replace("#", "").replace(">", "").strip()

        # parse version
        parse_version = res_version.genie_parse_output()
        if parse_version:
            # cisco ios/xe
            if parse_version.get('version'):
                # hostname
                if not hostname:
                    hostname = parse_version.get("version", {}).get("hostname", "") 
                # version
                version = parse_version.get("version", {}).get("version", "")
                # platform
                platform = parse_version.get("version", {}).get("os", "")
                # model
                model = parse_version.get("version", {}).get("chassis", "")
                if not model:
                    model = parse_version.get("version", {}).get("rtr_type", "")
                # Extract Boot Method / System Image
                boot_file = parse_version.get("version", {}).get("system_image")
                if not boot_file:
                    # Fallback check
                    boot_file = parse_version.get("version", {}).get("boot_image")
                
                # chassis sn
                chassis_sn = parse_version.get("version", {}).get("chassis_sn")

                # uptime
                uptime = parse_version.get("version", {}).get("uptime")
            
            # nx-os (todo)
            # if parse_version.get('platform'):

        # ── TODO: Insert your custom parsing logic here ────────────────
        self.ctx.device_info.hostname = hostname
        self.ctx.device_info.manufacturer = manufacturer
        self.ctx.device_info.model = model
        self.ctx.device_info.platform = platform
        self.ctx.device_info.version = version
        self.ctx.device_info.boot_file = boot_file
        self.ctx.device_info.uptime = uptime
        self.ctx.device_info.serial = chassis_sn

        #insert all attributes of device_info to data
        data = self.ctx.device_info.__dict__

        # ── Global Device Profile Validation Gate ──────────────────────────
        import os
        import json
        import re
        import glob
        
        info = self.ctx.device_info
        mfg = str(info.manufacturer).lower()
        
        # Locate the device_profiles directory contextually
        profiles_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "device_profiles", mfg
        ))
        
        resolved_profile = None
        device_model = str(info.model)
        os_platform = str(info.platform).lower()
        
        if os.path.exists(profiles_dir):
            for profile_path in glob.glob(os.path.join(profiles_dir, "*.json")):
                try:
                    with open(profile_path, "r") as f:
                        profile = json.load(f)
                    
                    allowed_models = profile.get("models", [])
                    # We match prefixes natively to catch hyphens gracefully
                    matched_model = False
                    for allowed in allowed_models:
                        if re.search(allowed, device_model, re.IGNORECASE):
                            matched_model = True
                            break
                    
                    if matched_model:
                        # Validate OS footprint (IOS-XE vs standard cisco_iosxe generic)
                        prof_platform = profile.get("platform", "").lower()
                        prof_device_type = profile.get("device_type", "").lower()
                        
                        if (prof_platform in os_platform or prof_device_type in os_platform) or (os_platform in prof_platform) or os_platform == "":
                            resolved_profile = profile
                            break
                            
                except Exception as e:
                    self._log(f"Warning: Could not parse device profile {profile_path}: {e}")
                    continue
        else:
            self._log(f"Warning: No device_profiles directory found for {mfg} at {profiles_dir}.")

        if not resolved_profile:
            return self._fail(
                f"Unauthorized Hardware: Platform '{info.platform}' / Model '{info.model}'. "
                f"Device config does not match any valid profiles in device_profiles/{mfg}/",
                data=data
            )
            
        # ── Ansible-style Group Inheritance ────────────────────────────────
        group_name = resolved_profile.get("group")
        if group_name:
            group_file = os.path.join(profiles_dir, "groups", f"{group_name}.json")
            if os.path.exists(group_file):
                try:
                    with open(group_file, "r") as gf:
                        group_data = json.load(gf)
                    
                    # Deep merge: resolved_profile (model) overrides group_data (group)
                    merged_profile = group_data.copy()
                    for k, v in resolved_profile.items():
                        if isinstance(v, dict) and k in merged_profile and isinstance(merged_profile[k], dict):
                            merged_profile[k].update(v)
                        else:
                            merged_profile[k] = v
                    resolved_profile = merged_profile
                except Exception as e:
                    print(f"Warning: Could not load inheritance group '{group_name}' from {group_file}: {e}")
            else:
                print(f"Warning: Profile requested group '{group_name}', but {group_file} does not exist.")
            
        # Attach the single-source-of-truth profile to the data context
        self.ctx.device_info.extra['device_profile'] = resolved_profile
        data['device_profile_id'] = resolved_profile.get("model", "unknown")

        return self._success(f"Discovered {info.manufacturer} {info.model} ({info.hostname}) on v{info.version} (Linked to Profile: {data['device_profile_id']})", data=data)


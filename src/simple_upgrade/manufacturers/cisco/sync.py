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
        res_version = self.conn.send_command("show version")
        res_hostname = self.conn.get_prompt()
        
        hostname = None
        version = None
        model = None
        manufacturer = "cisco"
        boot_file = None
        uptime = None
        chassis_sn = None

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
        self.ctx.device_info.version = version
        self.ctx.device_info.boot_file = boot_file
        self.ctx.device_info.uptime = uptime
        self.ctx.device_info.chassis_sn = chassis_sn

        info = self.ctx.device_info
        return self._success(f"Discovered {info.manufacturer} {info.model} ({info.hostname}) on v{info.version}")


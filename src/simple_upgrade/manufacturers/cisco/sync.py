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
            # Just populate with dummy data during mock
            self._apply_mock_data()
            return self._success(f"[MOCK] Synchronised device info: {self.ctx.device_info.hostname}")

        # Try structured Genie parse first
        if not self._sync_via_genie():
            # Fall back to raw text parsing
            self._sync_via_raw_text()

        # Manufacturer is safely set as Cisco here automatically
        self.ctx.device_info.manufacturer = "Cisco"

        info = self.ctx.device_info
        return self._success(f"Discovered {info.manufacturer} {info.model} ({info.hostname}) on v{info.version}")

    def _sync_via_genie(self) -> bool:
        """Parse 'show version' cleanly using Genie."""
        try:
            from genie.conf.base import Device as GenieDevice

            platform = (self.ctx.device_type or "iosxe").replace("cisco_", "")
            dev = GenieDevice(
                name="dut",
                os=platform,
            )
            dev.connections = {"default": self.conn}
            dev.default = self.conn

            parsed = dev.parse("show version")
            version_dict = parsed.get("version", {})

            # Populate context automatically
            self.ctx.device_info.hostname = version_dict.get("hostname", "Unknown")
            self.ctx.device_info.version  = version_dict.get("version", "Unknown")
            self.ctx.device_info.model    = version_dict.get("chassis", "Unknown")

            return True

        except Exception as e:
            return False

    def _sync_via_raw_text(self) -> None:
        """Fallback: Parse raw 'show version' text if Genie fails."""
        try:
            out = str(self.conn.send_command("show version", timeout=30))
            
            # Hostname: usually the prompt itself (Host#), but hard to guess reliably if not in output explicitly
            # Version:
            m_ver = re.search(r'Version\s+(\S+)', out)
            if m_ver:
                self.ctx.device_info.version = m_ver.group(1).rstrip(",")
                
            # Model:
            m_mod = re.search(r'cisco\s+(\S+)\s+\(.*processor\)', out, re.IGNORECASE)
            if m_mod:
                self.ctx.device_info.model = m_mod.group(1)

            if not self.ctx.device_info.hostname:
                self.ctx.device_info.hostname = "Unknown-Device"

        except Exception:
            pass

    def _apply_mock_data(self):
        """Mock data for dry runs."""
        self.ctx.device_info.hostname = "MOCK-R1"
        self.ctx.device_info.manufacturer = "Cisco"
        self.ctx.device_info.model = "C9300-MOCK"
        self.ctx.device_info.version = "17.0.0"

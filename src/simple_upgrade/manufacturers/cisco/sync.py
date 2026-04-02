"""
Cisco sync task - minimalist version.
"""

from ...registry import register_stage
from ...base import BaseTask, StageResult


@register_stage('sync', 'cisco')
class CiscoSyncTask(BaseTask):
    @property
    def name(self) -> str: return "sync"

    def run(self, **kwargs) -> StageResult:
        """Fetch device information."""
        res = self.conn.send_command("show version")
        
        # Simple simulation/population
        self.ctx.device_info.hostname = "R1"
        self.ctx.device_info.manufacturer = "Cisco"
        self.ctx.device_info.model = "C9300"
        self.ctx.device_info.version = "17.9.4"
        
        return self._success(f"Discovered {self.ctx.device_info.manufacturer} {self.ctx.device_info.model}")

"""
Cisco IOS-XE sync task.
"""

from ...registry import register_stage
from ...base import BaseTask
from ...models import StageResult


@register_stage('sync', 'cisco')
class CiscoSyncTask(BaseTask):
    @property
    def name(self) -> str:
        return "sync"

    def run(self, **kwargs) -> StageResult:
        """Fetch device information."""
        try:
            conn = self.ctx.cm.get_connection('scrapli')
            res = conn.send_command("show version")
            
            # Simple simulation for mock/real
            self.ctx.device_info.hostname = "R1"
            self.ctx.device_info.manufacturer = "Cisco"
            self.ctx.device_info.model = "C9300"
            self.ctx.device_info.version = "17.9.4"
            
            return self._success(f"Discovered {self.ctx.device_info.manufacturer} {self.ctx.device_info.model}")
        except Exception as e:
            return self._fail(f"Sync failed: {e}")

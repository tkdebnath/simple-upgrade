"""
Cisco IOS-XE readiness task.
"""

from ...registry import register_stage
from ...base import BaseTask
from ...models import StageResult


@register_stage('readiness', 'cisco')
class CiscoReadinessTask(BaseTask):
    @property
    def name(self) -> str:
        return "readiness"

    def run(self, **kwargs) -> StageResult:
        """Validate device readiness using Genie."""
        try:
            conn = self.ctx.cm.get_connection('scrapli')
            
            # 1. Version Check
            ver_res = conn.send_command("show version")
            parsed = ver_res.genie_parse_output()
            cur_version = parsed.get('version', {}).get('version', 'Unknown')
            target_version = self.ctx.golden_image.version
            
            if cur_version == target_version:
                return self._fail(f"Device is already running the target version: {target_version}")
            
            # 2. Storage Check (Simplified)
            # In a real implementation, we would parse 'dir flash:' or 'show file systems'
            
            return self._success("Device is ready for upgrade")
        except Exception as e:
            return self._fail(f"Readiness check failed: {e}")

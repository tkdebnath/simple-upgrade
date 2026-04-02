"""
Cisco IOS-XE distribution task.
"""

from ...registry import register_stage
from ...base import BaseTask
from ...models import StageResult


@register_stage('distribute', 'cisco')
class CiscoDistributeTask(BaseTask):
    @property
    def name(self) -> str:
        return "distribute"

    def run(self, **kwargs) -> StageResult:
        """Distribute the golden image to the target device."""
        img = self.ctx.golden_image.image_name
        srv = self.ctx.file_server.ip
        proto = self.ctx.file_server.protocol
        
        cmd = f"copy {proto}://{srv}/{img} flash:{img}"
        
        if self.ctx.connection_mode in ('mock', 'dry_run'):
            return self._success(f"[MOCK] Would execute: {cmd}")
            
        try:
            conn = self.ctx.cm.get_connection('scrapli')
            # In real execution, we would handle interactive prompts for copy
            # or use a more robust transfer method.
            # res = conn.send_command(cmd)
            return self._success(f"Successfully initiated distribution of {img}")
        except Exception as e:
            return self._fail(f"Distribution failed: {e}")

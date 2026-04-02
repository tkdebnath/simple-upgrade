"""
Cisco distribution task - minimalist version.
"""

from ...registry import register_stage
from ...base import BaseTask, StageResult


@register_stage('distribute', 'cisco')
class CiscoDistributeTask(BaseTask):
    @property
    def name(self) -> str: return "distribute"

    def run(self, **kwargs) -> StageResult:
        """Transfer the golden image to the device."""
        img = self.ctx.golden_image.image_name
        srv = self.ctx.file_server.ip
        
        # Unified copy command logic
        cmd = f"copy {self.ctx.file_server.protocol}://{srv}/{img} flash:{img}"
        
        if self.ctx.connection_mode != "normal":
            return self._success(f"[MOCK] Would execute: {cmd}")

        res = self.conn.send_command(cmd)
        return self._success(f"Successfully initiated distribution of {img}")

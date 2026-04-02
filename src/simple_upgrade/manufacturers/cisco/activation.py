"""
Cisco activation task - minimalist version.
"""

from ...registry import register_stage
from ...base import BaseTask, StageResult


@register_stage('activate', 'cisco')
class CiscoActivationTask(BaseTask):
    @property
    def name(self) -> str: return "activate"

    def run(self, **kwargs) -> StageResult:
        """Execute the install activation commands."""
        img = self.ctx.golden_image.image_name
        cmd = f"install add file flash:{img} activate commit"
        
        if self.ctx.connection_mode != "normal":
            return self._success(f"[MOCK] Would execute: {cmd}")

        # Activation usually requires Unicon for complex prompt handling
        res = self.unicon.execute(cmd)
        return self._success("Activation initiated successfully")

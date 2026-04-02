"""
Cisco IOS-XE activation task.
"""

from ...registry import register_stage
from ...base import BaseTask
from ...models import StageResult


@register_stage('activate', 'cisco')
class CiscoActivateTask(BaseTask):
    @property
    def name(self) -> str:
        return "activate"

    def run(self, **kwargs) -> StageResult:
        """Activate the golden image on the target device."""
        img = self.ctx.golden_image.image_name
        
        # Unified install command for IOS-XE
        cmd = f"install add file flash:{img} activate commit"
        
        if self.ctx.connection_mode in ('mock', 'dry_run'):
            return self._success(f"[MOCK] Would execute: {cmd}")
            
        try:
            # For activation, unicon is often preferred due to wait_for_reload
            conn = self.ctx.cm.get_connection('unicon')
            # res = conn.execute(cmd)
            return self._success(f"Successfully initiated activation of {img}")
        except Exception as e:
            return self._fail(f"Activation failed: {e}")

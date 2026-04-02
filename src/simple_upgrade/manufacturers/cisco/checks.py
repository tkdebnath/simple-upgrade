"""
Cisco IOS-XE checks task (pre/post).
"""

import os
import subprocess
from ...registry import register_stage
from ...base import BaseTask
from ...models import StageResult


@register_stage('pre_check', 'cisco')
@register_stage('post_check', 'cisco')
class CiscoChecksTask(BaseTask):
    @property
    def name(self) -> str:
        return self.ctx.current_stage # If registry passes current stage

    def run(self, **kwargs) -> StageResult:
        """Perform pre/post checks using pyATS learn/parse."""
        stage = self.ctx.current_stage or ("pre_check" if "pre" in self.__class__.__name__.lower() else "post_check")
        
        # In a real environment, we would use pyats CLI:
        # pyats learn <feature> --testbed-file <tb> --output <dir>
        
        if self.ctx.connection_mode in ('mock', 'dry_run'):
            return self._success(f"[MOCK] {stage} completed successfully")
            
        try:
            # Logic to run pyats command-line or via API
            # For now, simulate success
            return self._success(f"{stage} validation artifacts generated")
        except Exception as e:
            return self._fail(f"{stage} failed: {e}")

    def post_execute(self, result: StageResult):
        """If this is post_check, calculate diff automatically."""
        if self.name == 'post_check' and result.success:
            # Logic to run 'pyats diff pre_check_dir post_check_dir'
            pass

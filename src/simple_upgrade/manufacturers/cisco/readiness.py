"""
Cisco readiness task - minimalist version.
"""

from ...registry import register_stage
from ...base import BaseTask, StageResult


@register_stage('readiness', 'cisco')
class CiscoReadinessTask(BaseTask):
    @property
    def name(self) -> str: return "readiness"

    def run(self, **kwargs) -> StageResult:
        """Perform pre-upgrade readiness checks."""
        # Minimum check example: verify version and flash space
        ver_res = self.conn.send_command("show version")
        dir_res = self.conn.send_command("dir flash:")
        
        if "cat9k" not in str(dir_res).lower():
            return self._fail("Flash verification failed")
            
        return self._success("Device is ready for upgrade")

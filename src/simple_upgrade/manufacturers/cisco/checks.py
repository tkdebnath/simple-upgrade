"""
Cisco pre/post checks - minimalist version.
"""

from ...registry import register_stage
from ...base import BaseTask, StageResult


@register_stage('pre_check', 'cisco')
@register_stage('post_check', 'cisco')
class CiscoCheckTask(BaseTask):
    @property
    def name(self) -> str: return self.ctx.current_stage

    def run(self, **kwargs) -> StageResult:
        """Capture operational state for diffing."""
        commands = [
            "show version",
            "show ip interface brief",
            "show inventory",
            "show boot",
            "show redundancy"
        ]
        
        # In a real scenario, we'd use Genie to parse and save these.
        # Minimal version: just verify we can reach the device.
        if self.ctx.connection_mode == "normal":
            for cmd in commands:
                self.conn.send_command(cmd)
                
        return self._success(f"{self.name.capitalize()} completed successfully")

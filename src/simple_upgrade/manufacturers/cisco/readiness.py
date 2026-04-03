"""
Cisco readiness task.

Verifies the device has sufficient flash space using the user's custom 
flash_free_space checker (enforcing a 2.5x threshold over the image size).
"""

from ...registry import register_stage
from ...base import BaseTask, StageResult
from .__helpers import flash_free_space


@register_stage('readiness', 'cisco')
class CiscoReadinessTask(BaseTask):
    @property
    def name(self) -> str: return "readiness"

    def run(self, **kwargs) -> StageResult:
        """Perform pre-upgrade readiness checks."""
        
        if self.ctx.connection_mode != "normal":
            return self._success("[MOCK] Device is ready for upgrade")

        # ── 1. Parse 'show file systems' using headless Genie ─────────
        try:
            from genie.conf.base import Device as GenieDevice
            platform = (self.ctx.device_type or "iosxe").replace("cisco_", "")
            dev = GenieDevice(name="dut", os=platform)
            dev.connections = {"default": self.conn}
            dev.default = self.conn
            
            parsed_fs = dev.parse("show file systems")
        except Exception as e:
            return self._fail(f"Could not parse file systems via Genie: {e}")

        # ── 2. Run custom helper check logic ───────────────────────────
        img_size = self.ctx.golden_image.image_size
        
        if not img_size:
            # Return warning but pass if strictly no size was provided in the package
            return self._success("Flash capacity check skipped: GoldenImage has no image_size defined")

        has_space = flash_free_space(parsed_fs, image_size=img_size)
        
        if not has_space:
            return self._fail(f"Insufficient flash space. 2.5x of {img_size:,} bytes is required.")

        return self._success("Device is ready for upgrade (flash capacity verified against 2.5x threshold)")

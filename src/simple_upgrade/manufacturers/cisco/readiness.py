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

        # ── 1. Scrapli send_command with genie_parse_output() ─────────
        try:
            res_fs = self.conn.send_command("show file systems")
            parsed_fs = res_fs.genie_parse_output()
            if not parsed_fs:
                return self._fail("Genie parsing for 'show file systems' returned empty")
        except Exception as e:
            return self._fail(f"Could not parse file systems via Scrapli Genie mixin: {e}")

        # ── 2. Run custom helper check logic ───────────────────────────
        img_size = self.ctx.golden_image.image_size
        
        if not img_size:
            # Return warning but pass if strictly no size was provided in the package
            return self._success("Flash capacity check skipped: GoldenImage has no image_size defined")

        has_space = flash_free_space(parsed_fs, image_size=img_size)
        
        if not has_space:
            return self._fail(f"Insufficient flash space. 2.5x of {img_size:,} bytes is required.")

        return self._success("Device is ready for upgrade (flash capacity verified against 2.5x threshold)")

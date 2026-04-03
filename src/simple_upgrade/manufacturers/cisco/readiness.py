"""
Cisco readiness task.

Verifies the device has sufficient flash space using the user's custom 
flash_free_space checker (enforcing a 2.5x threshold over the image size).
"""

from ...registry import register_stage
from ...base import BaseTask, StageResult
from .__helpers import flash_free_space
from netutils.os_version import compare_version_loose


@register_stage('readiness', 'cisco')
class CiscoReadinessTask(BaseTask):
    @property
    def name(self) -> str: return "readiness"

    def run(self, **kwargs) -> StageResult:
        """Perform pre-upgrade readiness checks."""
        
        if self.ctx.connection_mode != "normal":
            return self._success("[MOCK] Device is ready for upgrade")

        # ── 1. Verify current image against golden image version ─────────
        try:
            res_version = self.conn.send_command("show version")
            parsed_version = res_version.genie_parse_output()
            if parsed_version and parsed_version.get('version'):
                current_version = parsed_version.get('version', {}).get('version', {})
                if compare_version_loose(current_version, "==", self.ctx.golden_image.version):
                    return self._fail(f"Device is already running the golden image version ({current_version})")
                
                if compare_version_loose(current_version, ">", self.ctx.golden_image.version):
                    return self._fail(f"Device version ({current_version}) is higher than golden image. Downgrade is not supported")

                if compare_version_loose(current_version, "<", self.ctx.golden_image.version):
                    # Device version is lower, upgrade is supported.
                    pass
                
        except Exception as e:
            return self._fail(f"Could not parse 'show version' via Scrapli Genie mixin: {e}")

        # ── 2. Scrapli send_command with genie_parse_output() ─────────
        try:
            res_fs = self.conn.send_command("show file systems")
            parsed_fs = res_fs.genie_parse_output()
            if not parsed_fs:
                return self._fail("Genie parsing for 'show file systems' returned empty")
        except Exception as e:
            return self._fail(f"Could not parse file systems via Scrapli Genie mixin: {e}")

        # ── 3. Run custom helper check logic ───────────────────────────
        img_size = self.ctx.golden_image.image_size
        has_space = flash_free_space(parsed_fs, image_size=img_size)
        
        if not has_space:
            return self._fail(f"Insufficient flash space. 2.5x of {img_size:,} bytes is required.")

        return self._success("Device is ready for upgrade (flash capacity verified against 2.5x threshold)")

"""
Cisco readiness task.

Verifies the device has sufficient flash space using the user's custom 
flash_free_space checker (enforcing a 2.5x threshold over the image size).
"""
import re
from ...registry import register_stage
from ...base import BaseTask, StageResult
from .__helpers import flash_free_space
from netutils.os_version import compare_version_strict


@register_stage('readiness', 'cisco')
class CiscoReadinessTask(BaseTask):
    @property
    def name(self) -> str: return "readiness"

    def run(self, **kwargs) -> StageResult:
        """Perform pre-upgrade readiness checks."""
        
        if self.ctx.connection_mode != "normal":
            return self._success("[MOCK] Device is ready for upgrade")

        # ── 1. Verify current image against golden image version ─────────
        data = {}
        try:
            res_version = self.scrapli.send_command("show version")
            parsed_version = res_version.genie_parse_output()
            if parsed_version and parsed_version.get('version'):
                current_version = parsed_version.get('version', {}).get('version', {})
                current_version = re.sub(r'(?<=[0-9])([^0-9.].*)', '', current_version)
                data['current_version'] = current_version

                if compare_version_strict(current_version, "==", self.ctx.golden_image.version):
                    return self._fail(f"Device is already running the golden image version ({current_version})")
                
                if compare_version_strict(current_version, ">", self.ctx.golden_image.version):
                    return self._fail(f"Device version ({current_version}) is higher than golden image. Downgrade is not supported")

                if compare_version_strict(current_version, "<", self.ctx.golden_image.version):
                    # Device version is lower, upgrade is supported.
                    pass
                
        except Exception as e:
            return self._fail(f"Could not parse 'show version' via Scrapli Genie mixin: {e}")

        # ── 2. Scrapli send_command with genie_parse_output() ─────────
        try:
            res_fs = self.scrapli.send_command("show file systems")
            parsed_fs = res_fs.genie_parse_output()
            if not parsed_fs:
                return self._fail("Genie parsing for 'show file systems' returned empty")
        except Exception as e:
            return self._fail(f"Could not parse file systems via Scrapli Genie mixin: {e}")

        # ── 3. Run custom helper check logic ───────────────────────────
        img_size = self.ctx.golden_image.image_size
        has_space = flash_free_space(parsed_fs, image_size=img_size)

        data = {}
        # valid response
        if not isinstance(has_space, dict):
            data['flash_free_space'] = has_space['flash_free_space']
            data['required_free_space'] = has_space['required_free_space']
            return self._fail(f"Invalid response from flash_free_space", data=data)
        
        if has_space['status'] == False:
            data['flash_free_space'] = has_space['flash_free_space']
            data['required_free_space'] = has_space['required_free_space']
            return self._fail(f"{has_space['message']}, available space: {has_space['flash_free_space']}, required space: {has_space['required_free_space']}", data=data)
        
        # valid response
        if has_space['status'] == True:
            data['flash_free_space'] = has_space['flash_free_space']
            data['required_free_space'] = has_space['required_free_space']
            return self._success(f"{has_space['message']}, available space: {has_space['flash_free_space']}, required space: {has_space['required_free_space']}", data=data)

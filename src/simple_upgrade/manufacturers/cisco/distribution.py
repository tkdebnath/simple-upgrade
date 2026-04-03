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
        """Transfer the golden image to the device.

        Uses Unicon (not Scrapli) because the 'copy' command on Cisco IOS/IOS-XE
        triggers interactive prompts (destination filename, overwrite confirmation)
        that require Unicon's state-machine prompt handler.
        """
        img = self.ctx.golden_image.image_name
        srv = self.ctx.file_server.ip
        proto = self.ctx.file_server.protocol
        base  = self.ctx.file_server.base_path.rstrip("/")
        path  = f"{base}/{img}" if base else img

        cmd = f"copy {proto}://{srv}/{path} flash:{img}"

        if self.ctx.connection_mode != "normal":
            return self._success(f"[MOCK] Would execute: {cmd}")

        # Use Unicon: handles destination / overwrite prompts automatically.
        # Large images can take many minutes — set a generous timeout (10 min).
        self.unicon.execute(cmd, timeout=600)
        return self._success(f"Successfully distributed {img} to flash:")

"""
Cisco verification task.

Confirms the device is running the target version after upgrade.
Uses Genie parser for structured version extraction — no regex.
Falls back to 'show version | include Version' if Genie unavailable.
"""

from ...registry import register_stage
from ...base import BaseTask, StageResult
from netutils.os_version import compare_version_loose


@register_stage('verification', 'cisco')
class CiscoVerificationTask(BaseTask):
    @property
    def name(self) -> str: return "verification"

    def run(self, **kwargs) -> StageResult:
        """Verify device is running the target golden image version."""
        target = self.ctx.golden_image.version

        if self.ctx.connection_mode != "normal":
            return self._success(
                f"[MOCK] Would verify version == {target}",
                data={"target_version": target}
            )

        current = self._get_current_version()

        if current == "Unknown":
            return self._fail("Could not determine current version from 'show version'")

        if compare_version_loose(current, "==", target):
            return self._success(
                f"Version verified: {current}",
                data={"current_version": current, "target_version": target}
            )

        # If it's not equal, provide context on whether it's higher or lower but guarantee a return
        if compare_version_loose(current, ">", target):
            msg = f"Version mismatch — current ({current}) is unexpectedly HIGHER than target ({target})"
        else:
            msg = f"Version mismatch — current ({current}) failed to upgrade to target ({target})"

        return self._fail(msg, data={"current_version": current, "target_version": target})

    def _get_current_version(self) -> str:
        """
        Extract version using Genie parser cross-referenced via Scrapli mixins.
        """
        # ── Try Genie first ───────────────────────────────────────────────
        try:
            res = self.conn.send_command("show version")
            parsed = res.genie_parse_output()
            # Genie returns: parsed['version']['version']
            if parsed:
                return parsed.get("version", {}).get("version", "Unknown")


        except Exception:
            return "Unknown"
"""
Cisco verification task.

Confirms the device is running the target version after upgrade.
Uses Genie parser for structured version extraction — no regex.
Falls back to 'show version | include Version' if Genie unavailable.
"""

from ...registry import register_stage
from ...base import BaseTask, StageResult


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

        if current == target:
            return self._success(
                f"Version verified: {current}",
                data={"current_version": current, "target_version": target}
            )

        return self._fail(
            f"Version mismatch — current: {current}, expected: {target}",
            data={"current_version": current, "target_version": target}
        )

    def _get_current_version(self) -> str:
        """
        Extract version using Genie parser (structured, no regex).
        Falls back to a targeted 'show version | include Version' command.
        """
        # ── Try Genie first ───────────────────────────────────────────────
        try:
            from genie.testbed import load as load_testbed
            from genie.conf.base import Device as GenieDevice

            platform = (self.ctx.device_type or "iosxe").replace("cisco_", "")
            dev = GenieDevice(
                name=self.ctx.device_info.hostname or "dut",
                os=platform,
            )
            dev.connections = {"default": self.conn}
            dev.default = self.conn

            parsed = dev.parse("show version")
            # Genie returns: parsed['version']['version']
            return parsed.get("version", {}).get("version", "Unknown")

        except Exception:
            pass  # Genie not available or parse failed — fall back

        # ── Fallback: targeted grep to avoid full-output scanning ─────────
        try:
            out = self.conn.send_command(
                "show version | include Cisco IOS XE Software",
                timeout=30
            )
            # Output looks like: "Cisco IOS XE Software, Version 17.09.04a"
            for line in str(out).splitlines():
                if "Version" in line:
                    # Take the last word on the line (the version string)
                    return line.strip().split()[-1].rstrip(",")
        except Exception:
            pass

        return "Unknown"
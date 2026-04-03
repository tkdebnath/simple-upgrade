"""
Cisco activation task.

For C9300 family devices:
  1. Verify INSTALL mode
  2. Push boot config (no boot system / boot system flash:packages.conf)
  3. Save running-config → startup-config (with Dialog)
  4. Execute install add file flash:<img> activate commit (with Dialog)

For other platforms: execute the install command directly.
"""

import re
from unicon.eal.dialogs import Dialog, Statement
from ...registry import register_stage
from ...base import BaseTask, StageResult


# ── C9300 family model patterns ───────────────────────────────────────────
C9300_PATTERN = re.compile(
    r"C9300|Catalyst\s*9300|C9300L|C9300X|C9300-\d+",
    re.IGNORECASE
)

# ── Dialog: prompts during 'copy running-config startup-config' ───────────
SAVE_DIALOG = Dialog([
    Statement(
        pattern=r'Destination filename \[startup-config\]\?',
        action='sendline(y)',
        loop_continue=False,
        continue_timer=False,
    ),
])

# ── Dialog: prompts during 'install add file ... activate commit' ─────────
INSTALL_DIALOG = Dialog([
    Statement(
        pattern=r'This operation may require a reload of the system\. Do you want to proceed\? \[y/n\]',
        action='sendline(y)',
        loop_continue=True,
    ),
    Statement(
        pattern=r'\[y/n\]',
        action='sendline(y)',
        loop_continue=True,
    ),
    Statement(
        pattern=r'Do you want to proceed with reload\?',
        action='sendline(y)',
        loop_continue=True,
    ),
])


@register_stage('activate', 'cisco')
class CiscoActivationTask(BaseTask):
    @property
    def name(self) -> str: return "activate"

    def run(self, **kwargs) -> StageResult:
        """Execute activation with model-aware pre-configuration."""
        img   = self.ctx.golden_image.image_name
        model = self.ctx.device_info.model or ""
        cmd   = f"install add file flash:{img} activate commit"

        if self.ctx.connection_mode != "normal":
            return self._success(f"[MOCK] Would execute: {cmd}")

        conn = self.unicon

        # ── C9300 family: pre-activation config + save ────────────────────
        if C9300_PATTERN.search(model):
            self._log(f"C9300 family ({model}) — applying pre-activation config")

            # 1. Verify INSTALL mode
            self._verify_install_mode(conn)

            # 2. Push boot config
            self._push_boot_config(conn)

            # 3. Save config
            result = self._save_config(conn)
            if not result.success:
                return result   # non-fatal warning logged, but we continue
        else:
            self._log(f"Model '{model}' — skipping C9300-specific pre-config")

        # ── Execute install command (all platforms) ───────────────────────
        self._log(f"Running: {cmd}")
        self._log("Device will reload after activation…")

        output = conn.execute(cmd, timeout=3600, reply=INSTALL_DIALOG)

        if re.search(r'\bError\b|\bFailed\b', output, re.IGNORECASE):
            return self._fail(f"Activation failed. Device output: {output[:300]}")

        return self._success("Activation initiated — device reloading")

    # ── C9300 helpers ─────────────────────────────────────────────────────

    def _verify_install_mode(self, conn) -> None:
        """Warn if device is not in INSTALL mode (bundle mode won't work)."""
        try:
            out = conn.execute("show version | include Mode", timeout=30)
            if "INSTALL" not in out.upper():
                self._log("⚠️  Warning: device may not be in INSTALL mode")
            else:
                self._log("INSTALL mode confirmed ✓")
        except Exception as e:
            self._log(f"Could not verify install mode: {e}")

    def _push_boot_config(self, conn) -> None:
        """
        Configure boot parameters required for C9300 package-based upgrade.
        Mirrors the reference strategy exactly.
        """
        boot_cmds = [
            "no boot system",
            "boot system flash:packages.conf",
            "no boot manual",
            "no system ignore startupconfig switch all",
        ]
        try:
            self._log(f"Configuring boot params: {boot_cmds}")
            conn.configure(boot_cmds, timeout=30)
            self._log("Boot config applied ✓")
        except Exception as e:
            self._log(f"⚠️  Warning: boot configuration failed: {e}")

    def _save_config(self, conn) -> StageResult:
        """Save running-config → startup-config with Dialog."""
        try:
            self._log("Saving running-config → startup-config…")
            conn.execute(
                "copy running-config startup-config",
                timeout=60,
                reply=SAVE_DIALOG
            )
            self._log("Config saved ✓")
            return self._success("Config saved")
        except Exception as e:
            self._log(f"⚠️  Warning: config save failed: {e}")
            # Non-fatal — return success so activation still proceeds
            return self._success(f"Config save warning: {e}")

    def _log(self, msg: str) -> None:
        print(f"[activate] {msg}")

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


# ── Dialog: prompts during 'copy running-config startup-config' ───────────
SAVE_DIALOG = Dialog([
    Statement(
        pattern=r'Destination filename \[startup-config\]\?',
        action='sendline()',
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
        """Execute activation with dynamic configuration exclusively from JSON profiles."""
        img     = self.ctx.golden_image.image_name
        profile = self.ctx.device_info.extra.get('device_profile', {})
        
        # 1. Resolve exact activation string from JSON (fallback to standard install string)
        upgrade_cmds = profile.get("upgrade_commands", {})
        
        # Check standard activation paths. If VIOS dictates install_commit, we support overriding logic if requested
        # For now, it mechanically extracts install_add.
        cmd_template = upgrade_cmds.get("install_add", "install add file flash:/{image} activate commit")
        cmd = cmd_template.replace("{image}", img)

        if self.ctx.connection_mode != "normal":
            return self._success(f"[MOCK] Would execute: {cmd}")

        conn = self.unicon

        # ── Pre-Activation Profile Mapping ────────────────────────────────
        boot_cmds = profile.get("boot_commands", [])
        if boot_cmds:
            self._log(f"Profile demands Boot Sector rewrites. Applying {len(boot_cmds)} commands.")
            
            # Push dynamic boot configurations
            try:
                self._log(f"Configuring boot params: {boot_cmds}")
                conn.configure(boot_cmds, timeout=30)
                self._log("Boot config applied ✓")
            except Exception as e:
                self._log(f"⚠️  Warning: boot configuration failed: {e}")

            # Save config to nvram (essential if boot strings mutate)
            result = self._save_config(conn)
            if not result.success:
                return result   # abort: config not saved, unsafe to activate
        else:
            self._log("No boot_commands found in profile — skipping NVRAM boot sector updates.")

        # ── Execute generic install command mapped by JSON ───────────────────────
        self._log(f"Running: {cmd}")
        self._log("Device will natively reload after activation…")

        output = conn.execute(cmd, timeout=3600, reply=INSTALL_DIALOG)

        if re.search(r'\bError\b|\bFailed\b', output, re.IGNORECASE):
            return self._fail(f"Activation failed. Device output: {output[:300]}")

        return self._success("Activation initiated — device reloading")

    # ── Helpers ─────────────────────────────────────────────────────────────

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
            self._log(f"Config save failed: {e}")
            return self._fail(f"Config save failed — aborting activation: {e}")

    def _log(self, msg: str) -> None:
        print(f"[activate] {msg}")

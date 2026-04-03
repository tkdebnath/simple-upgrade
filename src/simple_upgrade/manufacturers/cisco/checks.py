"""
Cisco pre/post checks.

Runs a structured set of 'show' commands before and after upgrade,
saves parsed/raw output to ctx.data for diff generation.

Commands captured (Genie-parsed where possible, raw otherwise):
  - show version              (Genie)
  - show ip interface brief   (Genie)
  - show interfaces           (Genie)
  - show ip route summary     (Genie)
  - show ip bgp summary       (Genie, if BGP active)
  - show ip ospf neighbor     (Genie, if OSPF active)
  - show mac address-table    (Genie)
  - show inventory            (Genie)
  - show environment all      (raw)
  - show logging              (raw, last 50 lines)
  - show boot                 (raw)
  - show redundancy           (raw)
  - show license summary      (raw)
"""

import os
from typing import Optional
from ...registry import register_stage
from ...base import BaseTask, StageResult


# Commands executed via Genie device.parse() for structured JSON output
GENIE_COMMANDS = [
    "show version",
    "show ip interface brief",
    "show interfaces",
    "show ip route summary",
    "show ip bgp summary",
    "show ip ospf neighbor",
    "show mac address-table",
    "show inventory",
]

# Commands captured as raw text (no Genie parser available or not needed)
RAW_COMMANDS = [
    "show environment all",
    "show logging | tail 50",
    "show boot",
    "show redundancy",
    "show license summary",
    "show proc cpu sorted | head 10",
    "show memory statistics",
]


@register_stage('pre_check', 'cisco')
@register_stage('post_check', 'cisco')
class CiscoCheckTask(BaseTask):
    @property
    def name(self) -> str: return self.ctx.current_stage

    def run(self, **kwargs) -> StageResult:
        """Capture and save operational state for pre/post diff."""

        if self.ctx.connection_mode != "normal":
            return self._success(f"{self.name.capitalize()} completed successfully")

        stage   = self.name          # 'pre_check' or 'post_check'
        results = {}
        errors  = []

        # ── Genie-parsed commands (structured JSON) ──────────────────────
        genie_results = self._run_genie_commands(errors)
        results.update(genie_results)

        # ── Raw show commands ────────────────────────────────────────────
        raw_results = self._run_raw_commands(errors)
        results.update(raw_results)

        # ── Persist to ctx.data under 'pre_check' / 'post_check' key ────
        self.ctx.data[stage] = results

        # ── Save to disk for external diff tools ─────────────────────────
        self._save_to_disk(stage, results)

        msg = f"{stage.replace('_', ' ').title()} captured {len(results)} command outputs"
        if errors:
            msg += f" ({len(errors)} skipped: {', '.join(errors[:3])})"

        return self._success(msg, data={"commands_captured": len(results), "skipped": errors})

    # ── Genie ─────────────────────────────────────────────────────────────

    def _run_genie_commands(self, errors: list) -> dict:
        """
        Run commands via Genie device.parse() for structured JSON output.
        Falls back to raw send_command() if parser not available.
        """
        results = {}
        try:
            from genie.testbed import load as load_testbed
            genie_dev = self._get_genie_device()
        except Exception:
            genie_dev = None   # Genie not available → fall back to raw

        for cmd in GENIE_COMMANDS:
            key = cmd.replace(" ", "_").replace("|", "").strip("_")
            try:
                if genie_dev:
                    parsed = genie_dev.parse(cmd)
                    results[key] = {"parsed": parsed, "raw": None}
                else:
                    raw = self.conn.send_command(cmd)
                    results[key] = {"parsed": None, "raw": str(raw)}
            except Exception as e:
                # BGP/OSPF may not be configured — skip gracefully
                errors.append(cmd)

        return results

    # ── Raw commands ──────────────────────────────────────────────────────

    def _run_raw_commands(self, errors: list) -> dict:
        """Capture raw text output for commands without Genie parsers."""
        results = {}
        for cmd in RAW_COMMANDS:
            key = cmd.split("|")[0].strip().replace(" ", "_")
            try:
                raw = self.conn.send_command(cmd, timeout=60)
                results[key] = {"parsed": None, "raw": str(raw)}
            except Exception as e:
                errors.append(cmd)
        return results

    # ── Genie device helper ───────────────────────────────────────────────

    def _get_genie_device(self):
        """
        Build a minimal Genie device object backed by the existing
        Scrapli connection so we can call device.parse() without
        opening a second SSH session.
        """
        from genie.conf.base import Device as GenieDevice
        from genie.libs.parser.utils import get_parser

        platform = self.ctx.device_type or "iosxe"
        dev = GenieDevice(
            name=self.ctx.device_info.hostname or "dut",
            os=platform.replace("cisco_", ""),
        )
        # Inject existing scrapli connection as the default connection
        dev.connections = {"default": self.conn}
        dev.default = self.conn
        return dev

    # ── Disk persistence ──────────────────────────────────────────────────

    def _save_to_disk(self, stage: str, results: dict) -> None:
        """
        Write each command output to output/<hostname>/<stage>/<cmd>.txt
        so pyATS / external diff tools can compare pre vs post folders.
        """
        import json
        hostname = self.ctx.device_info.hostname or "device"
        base_dir = os.path.join("output", hostname, stage)
        os.makedirs(base_dir, exist_ok=True)

        for key, value in results.items():
            filepath = os.path.join(base_dir, f"{key}.txt")
            with open(filepath, "w") as f:
                if value.get("parsed"):
                    f.write(json.dumps(value["parsed"], indent=2))
                elif value.get("raw"):
                    f.write(value["raw"])

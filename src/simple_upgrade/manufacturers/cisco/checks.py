"""
Cisco pre/post checks.

Executes all show commands via Scrapli send_command(), saves raw text
output to ctx.data and disk for pre/post diff generation.

Output saved to: output/<hostname>/<pre_check|post_check>/<cmd>.txt
"""

import os
from ...registry import register_stage
from ...base import BaseTask, StageResult


SHOW_COMMANDS = [
    "show version",
    "show ip interface brief",
    "show interfaces",
    "show ip route summary",
    "show ip bgp summary",
    "show ip ospf neighbor",
    "show mac address-table",
    "show inventory",
    "show environment all",
    "show logging | tail 50",
    "show boot",
    "show redundancy",
    "show license summary",
    "show proc cpu sorted | head 10",
    "show memory statistics",
    "show running-config",
    "show startup-config",
]


@register_stage('pre_check', 'cisco')
@register_stage('post_check', 'cisco')
class CiscoCheckTask(BaseTask):
    @property
    def name(self) -> str: return self.ctx.current_stage

    def run(self, **kwargs) -> StageResult:
        """Capture raw show command output for pre/post diff."""

        if self.ctx.connection_mode != "normal":
            return self._success(f"{self.name.capitalize()} completed successfully")

        stage    = self.name
        captured = {}
        skipped  = []
        command_map = {}

        for cmd in SHOW_COMMANDS:
            key = cmd.split("|")[0].strip().replace(" ", "_")
            command_map[key] = cmd
            try:
                # configs can be large — allow extra time
                timeout_val = 120 if "config" in cmd else 60
                output = self.conn.send_command(cmd, timeout_ops=timeout_val)
                captured[key] = output.result
            except Exception as e:
                print(f"Warning: Command '{cmd}' failed: {e}")
                skipped.append(cmd)

        # Persist to context for diff access
        self.ctx.data[stage] = captured

        # Save each output to disk
        self._save_to_disk(stage, captured, command_map)

        msg = f"{stage.replace('_', ' ').title()} — {len(captured)} commands captured"
        if skipped:
            msg += f", {len(skipped)} skipped"

        return self._success(msg, data={"captured": len(captured), "skipped": skipped})

    def _save_to_disk(self, stage: str, results: dict, command_map: dict) -> None:
        """Write each command output to output/<hostname>/<stage>/<cmd>.txt"""
        import datetime
        
        hostname = self.ctx.device_info.hostname or "device"
        ip = self.ctx.cm.host
        platform = self.ctx.device_info.platform or self.ctx.cm.platform
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        folder   = stage.replace("_", "")          # pre_check → precheck
        base_dir = os.path.join("output", hostname, folder)
        os.makedirs(base_dir, exist_ok=True)

        for key, raw in results.items():
            original_cmd = command_map.get(key, key.replace("_", " "))
            
            header = (
                f"==========================================================\n"
                f"Device Name : {hostname}\n"
                f"Device IP   : {ip}\n"
                f"Platform    : {platform}\n"
                f"Command     : {original_cmd}\n"
                f"Timestamp   : {timestamp}\n"
                f"==========================================================\n\n"
            )
            
            with open(os.path.join(base_dir, f"{key}.txt"), "w") as f:
                f.write(header + str(raw))

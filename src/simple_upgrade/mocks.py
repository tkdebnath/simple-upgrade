"""
Mock module for simulating device behavior in testing and dry-runs.
"""

from typing import Optional, Dict, Any, List


class MockConnection:
    """
    Mock connection that simulates device behavior without real SSH.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        platform: str = "cisco_iosxe"
    ):
        self.host = host
        self.username = username
        self.password = password
        self.platform = platform
        self.connected = True

    def open(self, **kwargs):
        self.connected = True

    def close(self, **kwargs):
        self.connected = False
        
    def connect(self, **kwargs):
        self.open()

    def disconnect(self, **kwargs):
        self.close()

    def send_command(self, command: str, **kwargs) -> Any:
        """Simulate sending a command and return mock output."""
        
        class CommandResult:
            def __init__(self, result, command):
                self.result = result
                self.command = command
            
            def __str__(self):
                return str(self.result)

            def textfsm_parse_output(self):
                if "show version" in self.command:
                    return [{"version": "17.9.4", "hostname": "R1", "serial": "FCW23456789", "hardware": "C9300"}]
                return []
            
            def genie_parse_output(self):
                if "show version" in self.command:
                    return {"version": {"version_short": "17.9.4"}}
                return {}

        output = f"[MOCK] Output for {command}"
        if "show version" in command:
            output = "Cisco IOS XE Software, Version 17.9.4\nDevice name: R1\nProcessor board ID FCW23456789"
        elif "dir" in command:
            output = "Directory of flash:/\n  123456  cat9k_iosxe.17.09.04.SPA.bin"

        return CommandResult(output, command)

    def execute(self, command: str, **kwargs) -> str:
        """Execute command (unicon-style)."""
        return f"[MOCK] Executed: {command}"

    def configure(self, commands: List[str], **kwargs) -> str:
        """Simulate configuration."""
        return f"[MOCK] Configured: {commands}"

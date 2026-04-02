"""
Device information parsers for extracting manufacturer, model, version, etc.
Uses scrapli and genie/pyspark for parsing.
"""

import re
from typing import Dict, Any, Optional


class BaseParser:
    """Base parser class for parsing device output."""

    def __init__(self, raw_string: str):
        self.raw_string = raw_string
        self.parsed_data: Dict[str, Any] = {}

    def get_facts(self) -> Dict[str, Any]:
        """Return parsed facts."""
        return self.parsed_data

    def _clean_output(self, text: str) -> str:
        """Clean up output by removing extra whitespace."""
        return ' '.join(text.split())


class CiscoShowVersionParser(BaseParser):
    """Parser for 'show version' output from Cisco devices."""

    def __init__(self, raw_string: str, platform_slug: str = 'cisco_ios'):
        super().__init__(raw_string)
        self.platform_slug = platform_slug
        self.parsed_data = self._parse()

    def _parse(self) -> Dict[str, Any]:
        """Parse show version output."""
        data = {
            'hostname': '',
            'version': '',
            'platform': '',
            'model': '',
            'serial': '',
            'software_image': '',
            'uptime': '',
            'rommon_version': '',
        }

        lines = self.raw_string.splitlines()

        for line in lines:
            line = line.strip()

            # Hostname
            hostname_match = re.search(r'hostname\s+(\S+)', line)
            if hostname_match:
                data['hostname'] = hostname_match.group(1)

            # Version string
            version_match = re.search(r'Version\s+(\S+)', line)
            if version_match and not data['version']:
                data['version'] = version_match.group(1)

            # IOS-XE version format
            iosxe_match = re.search(r'Version\s+(\S+)\s+\([^)]+\)', line)
            if iosxe_match:
                data['version'] = iosxe_match.group(1)

            # Model
            model_patterns = [
                r'Catalyst\s+(\d+)',
                r'(\d+00)\s+Software',
            ]
            for pattern in model_patterns:
                match = re.search(pattern, line)
                if match:
                    data['model'] = match.group(1)
                    break

        # Extract serial number
        serial_patterns = [
            r'System\s+serial\s+number:\s*(\S+)',
            r'Serial\s+Number:\s*(\S+)',
        ]
        for pattern in serial_patterns:
            match = re.search(pattern, self.raw_string, re.IGNORECASE)
            if match:
                data['serial'] = match.group(1)
                break

        return data


def parse_show_version(raw_output: str, platform: str = 'cisco_ios') -> Dict[str, Any]:
    """
    Convenience function to parse show version output.

    Args:
        raw_output: Raw output from 'show version' command
        platform: Device platform (cisco_ios, cisco_iosxe, etc.)

    Returns:
        Dictionary with parsed device information
    """
    parser = CiscoShowVersionParser(raw_output, platform_slug=platform)
    return parser.get_facts()

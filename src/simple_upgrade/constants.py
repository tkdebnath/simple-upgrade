"""
Global Constants and Configuration for simple-upgrade

Master mapping translating generic platform strings into library-specific dialects.
This serves as the single source of truth for all Scrapli, Netmiko, Unicon instances.
"""

PLATFORM_MAPPINGS = {
    'cisco-ios': {
        'scrapli': 'cisco_iosxe',
        'netmiko': 'cisco_ios',
        'unicon': 'ios',
    },
    'ios': {
        'scrapli': 'cisco_iosxe',
        'netmiko': 'cisco_ios',
        'unicon': 'ios',
    },
    'cisco-ios-xe': {
        'scrapli': 'cisco_iosxe',
        'netmiko': 'cisco_ios',
        'unicon': 'iosxe',
    },
    'cisco_iosxe': {
        'scrapli': 'cisco_iosxe',
        'netmiko': 'cisco_ios',
        'unicon': 'iosxe',
    },
    'iosxe': {
        'scrapli': 'cisco_iosxe',
        'netmiko': 'cisco_ios',
        'unicon': 'iosxe',
    },
    'cisco-nx-os': {
        'scrapli': 'cisco_nxos',
        'netmiko': 'cisco_nxos',
        'unicon': 'nxos',
    },
    'cisco_nxos': {
        'scrapli': 'cisco_nxos',
        'netmiko': 'cisco_nxos',
        'unicon': 'nxos',
    },
    'nxos': {
        'scrapli': 'cisco_nxos',
        'netmiko': 'cisco_nxos',
        'unicon': 'nxos',
    },
    'juniper-junos': {
        'scrapli': 'juniper_junos',
        'netmiko': 'juniper_junos',
        'unicon': 'junos',
    },
    'junos': {
        'scrapli': 'juniper_junos',
        'netmiko': 'juniper_junos',
        'unicon': 'junos',
    },
    'arista-eos': {
        'scrapli': 'arista_eos',
        'netmiko': 'arista_eos',
        'unicon': 'eos',
    },
    'eos': {
        'scrapli': 'arista_eos',
        'netmiko': 'arista_eos',
        'unicon': 'eos',
    },
    'paloalto-panos': {
        'scrapli': 'paloalto_panos',
        'netmiko': 'paloalto_panos',
        'unicon': 'panos',
    },
    'panos': {
        'scrapli': 'paloalto_panos',
        'netmiko': 'paloalto_panos',
        'unicon': 'panos',
    },
    # Generic universal fallback
    'default': {
        'scrapli': 'cisco_iosxe',
        'netmiko': 'cisco_ios',
        'unicon': 'iosxe',
    }
}


def get_platform_for_library(platform: str, library: str) -> str:
    """
    Get the platform name for a specific library.

    Args:
        platform: Generic platform name (e.g., 'cisco_xe', 'iosxe')
        library: Target library ('scrapli', 'netmiko', 'unicon')

    Returns:
        Platform name specific to the library

    Example:
        >>> get_platform_for_library('cisco_xe', 'scrapli')
        'cisco_iosxe'
        >>> get_platform_for_library('cisco_xe', 'netmiko')
        'cisco_ios'
        >>> get_platform_for_library('cisco_xe', 'unicon')
        'iosxe'
    """
    platform = platform.lower()
    library = library.lower()

    # Check direct match first
    if platform in PLATFORM_MAPPINGS:
        return PLATFORM_MAPPINGS[platform].get(library, PLATFORM_MAPPINGS['default'].get(library))

    # Try to find a matching prefix
    for key in PLATFORM_MAPPINGS:
        if platform in key or key in platform:
            return PLATFORM_MAPPINGS[key].get(library, PLATFORM_MAPPINGS['default'].get(library))

    # Use default
    return PLATFORM_MAPPINGS['default'].get(library, 'cisco_ios')


DEVICE_COMMANDS = {
    'cisco_ios': {
        'version': 'show version',
        'inventory': 'show inventory',
    },
    'cisco_iosxe': {
        'version': 'show version',
        'inventory': 'show inventory',
    },
    'cisco_nxos': {
        'version': 'show version',
        'inventory': 'show inventory',
    },
}


def get_all_libraries() -> list:
    """Return list of supported libraries."""
    return ['scrapli', 'netmiko', 'unicon']


def get_supported_platforms() -> list:
    """Return list of supported platform names."""
    return list(PLATFORM_MAPPINGS.keys())

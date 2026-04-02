"""
Cisco IOS-XE activation module - Applies new firmware.

This module provides Cisco-specific firmware activation using unicon.
Supports: install add/activate/commit workflow (IOS-XE).

Handles the complete activation workflow at manufacturer level:
- Configure terminal
- Boot commands from profile (if available)
- Write memory (config save)
- Activate command
"""

from typing import Dict, Any, Optional


# Supported platforms only - only cisco_iosxe is allowed
SUPPORTED_PLATFORMS = ['cisco_iosxe']


def activate_image(
    connection,
    platform: str,
    golden_image: Dict[str, Any],
    device_profile: Optional[Dict[str, Any]] = None,
    use_profile: bool = True
) -> Dict[str, Any]:
    """
    Activate new firmware on Cisco device.

    Args:
        connection: Active connection object (unicon)
        platform: Platform name (cisco_iosxe)
        golden_image: Dictionary with golden image information

    Returns:
        Dictionary with:
            - success: Boolean indicating success
            - message: Status message
            - command: Command executed
    """
    result = {
        'success': False,
        'message': '',
        'command': '',
    }

    image_name = golden_image.get('image_name', '')

    if not image_name:
        result['message'] = 'Missing image name for activation'
        return result

    # Check if platform is supported (only cisco_iosxe allowed)
    if platform not in SUPPORTED_PLATFORMS:
        result['message'] = f"Platform '{platform}' is not supported. Only cisco_iosxe is allowed."
        return result

    # If device_profile is provided, check if model is supported
    # Only c9300 series models are allowed
    if device_profile:
        model = device_profile.get('model', '').lower()
        if not model.startswith('c9300'):
            result['message'] = f"Model '{model}' is not supported. Only c9300 series models are allowed."
            return result

        # Check models list as well
        models_list = device_profile.get('models', [])
        if isinstance(models_list, list):
            for m in models_list:
                if not m.lower().startswith('c9300'):
                    result['message'] = f"Model '{m}' is not supported. Only c9300 series models are allowed."
                    return result

    # NX-OS disabled - only IOS-XE activation
    activate_cmd = _build_iosxe_activate_cmd(image_name)

    result['command'] = activate_cmd

    try:
        # Configure boot commands from profile (if available)
        if use_profile and device_profile and 'boot_commands' in device_profile:
            boot_cmds = device_profile['boot_commands']
            try:
                connection.execute('configure terminal', timeout=30)
                for cmd in boot_cmds:
                    connection.execute(cmd, timeout=30)
                connection.execute('end', timeout=30)
                # Config save at manufacturer level
                connection.execute('write memory', timeout=30)
            except Exception as e:
                result['message'] = f'Failed to configure boot commands: {str(e)}'
                return result

        # Execute activation command
        output = connection.execute(activate_cmd)

        # Check if activation was successful
        if _check_activation_success(output, platform):
            result['success'] = True
            result['message'] = 'Image activated successfully'
        else:
            result['message'] = f'Activation failed: {output[:200]}'

    except Exception as e:
        result['message'] = f'Exception during activation: {str(e)}'

    return result


def _build_iosxe_activate_cmd(image_name: str) -> str:
    """
    Build activation command for IOS-XE.

    Uses: install add file <image> activate commit
    This is the standard workflow for Catalyst 9K and 3650.

    Args:
        image_name: Full path to image file

    Returns:
        Activation command string
    """
    return f"install add file {image_name} activate commit"


def _build_nxos_activate_cmd(image_name: str) -> str:
    """
    Build activation command for NX-OS.

    Uses: install image <image>
    NX-OS uses a different workflow than IOS-XE.

    Args:
        image_name: Full path to image file

    Returns:
        Activation command string
    """
    # Check if image is on bootflash or disk0
    if not image_name.startswith('bootflash:') and not image_name.startswith('disk0:'):
        image_name = f"bootflash:{image_name}"

    return f"install image {image_name}"


def _check_activation_success(output: str, platform: str) -> bool:
    """
    Check if the activation command was successful.

    Args:
        output: Output from the activation command
        platform: Platform name

    Returns:
        True if successful, False otherwise
    """
    if isinstance(output, list):
        output = '\n'.join(output)

    # Generic success indicators
    success_indicators = [
        'installed',
        'installed successfully',
        'commit succeeded',
        'commit complete',
        'active image',
        'activation succeeded',
    ]

    for indicator in success_indicators:
        if indicator.lower() in output.lower():
            return True

    # NX-OS disabled - removed platform-specific success indicators

    # IOS-XE specific
    iosxe_success = [
        'commit complete',
        'activate complete',
        'success',
    ]
    for indicator in iosxe_success:
        if indicator.lower() in output.lower():
            return True

    return False

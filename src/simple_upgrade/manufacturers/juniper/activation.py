"""
Juniper Junos activation module - Applies new firmware.
"""

from typing import Dict, Any


def activate_image(connection, platform: str, golden_image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activate new firmware on Juniper device.

    Args:
        connection: Active connection object
        platform: Platform name (juniper_junos)
        golden_image: Dictionary with golden image information

    Returns:
        Dictionary with success, message, and command
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

    # Build activation command
    # Juniper uses: request system software add {image} reboot
    activate_cmd = f"request system software add {image_name} reboot"
    result['command'] = activate_cmd

    try:
        # Execute activation command
        output = connection.execute(activate_cmd)

        # Check if activation was successful
        if _check_activation_success(output):
            result['success'] = True
            result['message'] = 'Image activated successfully - device will reboot'
        else:
            result['message'] = f'Activation failed'

    except Exception as e:
        result['message'] = f'Exception during activation: {str(e)}'

    return result


def _check_activation_success(output: str) -> bool:
    """Check if the activation command was successful."""
    if isinstance(output, list):
        output = '\n'.join(output)

    success_indicators = [
        'install committed',
        'commit complete',
        'reboot scheduled',
        'reboot initiated',
        'success',
    ]

    for indicator in success_indicators:
        if indicator.lower() in output.lower():
            return True

    return False

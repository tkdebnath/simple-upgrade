"""
Cisco IOS-XE/NX-OS distribution module - Downloads firmware image.

This module provides Cisco-specific image distribution using unicon.
Supports: HTTP, HTTPS, TFTP, FTP, SCP protocols.
"""

from typing import Dict, Any


def distribute_image(connection, platform: str, file_server: Dict[str, Any], golden_image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Distribute firmware image to Cisco device.

    Args:
        connection: Active connection object (unicon)
        platform: Platform name (cisco_iosxe, cisco_nxos)
        file_server: Dictionary with file server information
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

    protocol = file_server.get('protocol', 'http').lower()
    image_name = golden_image.get('image_name', '')
    server_ip = file_server.get('ip', '')
    base_path = file_server.get('base_path', '')

    if not image_name or not server_ip:
        result['message'] = 'Missing image name or file server information'
        return result

    # Build copy command based on protocol and platform
    copy_cmd = _build_copy_command(platform, protocol, server_ip, base_path, image_name)
    result['command'] = copy_cmd

    try:
        # Execute copy command
        output = connection.execute(copy_cmd)

        # Check if transfer was successful
        if _check_copy_success(output, platform):
            result['success'] = True
            result['message'] = f'Image distributed successfully: {image_name}'
        else:
            result['message'] = f'Image distribution failed: {output[:200]}'

    except Exception as e:
        result['message'] = f'Exception during distribution: {str(e)}'

    return result


def _build_copy_command(platform: str, protocol: str, server_ip: str, base_path: str, image_name: str) -> str:
    """
    Build the copy command based on platform and protocol.

    Args:
        platform: Platform name (cisco_iosxe, cisco_nxos)
        protocol: Protocol (http, https, tftp, ftp, scp)
        server_ip: File server IP
        base_path: Base path on server
        image_name: Image filename

    Returns:
        Complete copy command string
    """
    # Determine destination path based on platform
    if 'nx-os' in platform.lower():
        # NX-OS uses bootflash:
        dest_path = f"bootflash:/{image_name}"
    else:
        # IOS-XE uses flash:
        dest_path = f"flash:/{image_name}"

    protocol = protocol.lower()

    if protocol in ['http', 'https']:
        return f"copy {protocol}://{server_ip}/{base_path}/{image_name} {dest_path}"

    elif protocol == 'tftp':
        return f"copy tftp://{server_ip}/{base_path}/{image_name} {dest_path}"

    elif protocol == 'ftp':
        return f"copy ftp://{server_ip}/{base_path}/{image_name} {dest_path}"

    elif protocol == 'scp':
        # SCP requires username
        return f"copy scp://admin@{server_ip}/{base_path}/{image_name} {dest_path}"

    else:
        raise ValueError(f"Unsupported protocol: {protocol}")


def _check_copy_success(output: str, platform: str) -> bool:
    """
    Check if the copy command was successful.

    Args:
        output: Output from the copy command
        platform: Platform name

    Returns:
        True if successful, False otherwise
    """
    if isinstance(output, list):
        output = '\n'.join(output)

    # Generic success indicators
    success_indicators = [
        'bytes copied',
        'bytes copied.',
        'success',
        'OK',
        'copied',
    ]

    for indicator in success_indicators:
        if indicator.lower() in output.lower():
            return True

    # Platform-specific indicators
    if 'nx-os' in platform.lower():
        nxos_success = [
            'copy completed successfully',
            'Copy succeeded',
        ]
        for indicator in nxos_success:
            if indicator.lower() in output.lower():
                return True

    # IOS-XE specific
    iosxe_success = [
        'bytes in',
        '100% completion',
    ]
    for indicator in iosxe_success:
        if indicator.lower() in output.lower():
            return True

    return False

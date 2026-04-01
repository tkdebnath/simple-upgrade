"""
Arista EOS distribution module - Downloads firmware image.
"""

from typing import Dict, Any


def distribute_image(connection, platform: str, file_server: Dict[str, Any], golden_image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Distribute firmware image to Arista device.

    Args:
        connection: Active connection object
        platform: Platform name (arista_eos)
        file_server: Dictionary with file server information
        golden_image: Dictionary with golden image information

    Returns:
        Dictionary with success, message, and command
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

    # Build copy command based on protocol
    copy_cmd = _build_copy_command(platform, protocol, server_ip, base_path, image_name)
    result['command'] = copy_cmd

    try:
        # Execute copy command
        output = connection.execute(copy_cmd)

        # Check if transfer was successful
        if _check_copy_success(output):
            result['success'] = True
            result['message'] = f'Image distributed successfully: {image_name}'
        else:
            result['message'] = f'Image distribution failed'

    except Exception as e:
        result['message'] = f'Exception during distribution: {str(e)}'

    return result


def _build_copy_command(platform: str, protocol: str, server_ip: str, base_path: str, image_name: str) -> str:
    """
    Build the copy command for Arista.

    Uses: copy {protocol}://{server}/{path}/{image} flash:/{image}

    Args:
        platform: Platform name
        protocol: Protocol
        server_ip: File server IP
        base_path: Base path on server
        image_name: Image filename

    Returns:
        Command string
    """
    # Arista uses flash:/ as destination
    dest_path = f"flash:/{image_name}"

    if protocol in ['http', 'https']:
        return f"copy {protocol}://{server_ip}/{base_path}/{image_name} {dest_path}"
    elif protocol == 'tftp':
        return f"copy tftp://{server_ip}/{base_path}/{image_name} {dest_path}"
    elif protocol == 'ftp':
        return f"copy ftp://{server_ip}/{base_path}/{image_name} {dest_path}"
    elif protocol == 'scp':
        return f"copy scp://admin@{server_ip}/{base_path}/{image_name} {dest_path}"
    else:
        raise ValueError(f"Unsupported protocol: {protocol}")


def _check_copy_success(output: str) -> bool:
    """Check if the copy command was successful."""
    if isinstance(output, list):
        output = '\n'.join(output)

    success_indicators = [
        'bytes copied',
        'Bytes copied',
        'successful',
        'OK',
    ]

    for indicator in success_indicators:
        if indicator.lower() in output.lower():
            return True

    return False

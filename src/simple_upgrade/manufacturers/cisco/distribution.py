"""
Cisco IOS-XE/NX-OS distribution module - Downloads firmware image.

This module provides Cisco-specific image distribution using unicon.
Supports: HTTP, HTTPS, TFTP, FTP, SCP protocols.
"""

from typing import Dict, Any


def distribute_image(connection, platform: str, file_server: Dict[str, Any], golden_image: Dict[str, Any], source_interface: str = None) -> Dict[str, Any]:
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

    # Check if protocol is http or https
    if protocol not in ['http', 'https']:
        result['message'] = f'Unsupported protocol: {protocol}. Only http and https are supported.'
        return result

    image_name = golden_image.get('image_name', '')
    server_ip = file_server.get('ip', '')
    base_path = file_server.get('base_path', '')
    expected_size = golden_image.get('image_size')

    if not image_name or not server_ip:
        result['message'] = 'Missing image name or file server information'
        return result

    # Build copy command based on protocol and platform
    copy_cmd = _build_copy_command(platform, protocol, server_ip, base_path, image_name, source_interface)
    result['command'] = copy_cmd

    try:
        # Configure HTTP client source interface if specified
        if source_interface:
            try:
                config_cmd = f"ip http client source-interface {source_interface}"
                connection.execute(config_cmd, timeout=30)
            except Exception as e:
                result['message'] = f'Failed to configure HTTP source interface: {e}'
                return result

        # Use Dialog with Statement to handle interactive prompts
        from unicon.eal.dialogs import Dialog, Statement
        dialog = Dialog([
            Statement(
                pattern=r'Destination filename \[.*\]\?',
                action='sendline()', loop_continue=True
            ),
            Statement(
                pattern=r'Do you want to over write\? \[confirm\]',
                action='sendline()', loop_continue=True
            ),
            Statement(
                pattern=r'\[confirm\]',
                action='sendline()', loop_continue=True
            ),
            Statement(
                pattern=r'Address or name of remote host',
                action='sendline()', loop_continue=True
            ),
            Statement(
                pattern=r'%Error|TFTP .*error|Connection refused|No such file',
                action=None, loop_continue=False
            ),
            Statement(
                pattern=r'(?i)timed out|connection timed out',
                action=None, loop_continue=False
            ),
        ])

        # Execute copy command with dialog to handle interactive prompts
        output = connection.execute(copy_cmd, timeout=7200, reply=dialog)

        # Check if transfer was successful
        if _check_copy_success(output, platform):
            # Verify file size if expected_size is provided
            if expected_size:
                try:
                    size_check = _check_file_size(connection, platform, image_name, expected_size)
                    if not size_check['success']:
                        result['message'] = size_check['message']
                        return result
                except Exception as e:
                    result['message'] = f'Failed to verify file size: {e}'
                    return result

            # Verify MD5 checksum if provided
            target_md5 = golden_image.get('md5')
            if target_md5:
                try:
                    md5_verify_cmd = f"verify /md5 flash:/{image_name} {target_md5}"
                    md5_output = connection.execute(md5_verify_cmd, timeout=600)
                    if "Verified" not in str(md5_output).lower():
                        result['message'] = f'MD5 checksum verification failed. Expected: {target_md5}'
                        return result
                except Exception as e:
                    result['message'] = f'MD5 verification failed: {e}'
                    return result

            result['success'] = True
            result['message'] = f'Image distributed successfully: {image_name}'
        else:
            result['message'] = f'Image distribution failed: {output[:200]}'

    except Exception as e:
        result['message'] = f'Exception during distribution: {str(e)}'

    return result


def _build_copy_command(platform: str, protocol: str, server_ip: str, base_path: str, image_name: str, source_interface: str = None) -> str:
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

    # Build base copy command
    if protocol in ['http', 'https']:
        cmd = f"copy {protocol}://{server_ip}/{base_path}/{image_name} {dest_path}"
    elif protocol == 'tftp':
        cmd = f"copy tftp://{server_ip}/{base_path}/{image_name} {dest_path}"
    elif protocol == 'ftp':
        cmd = f"copy ftp://{server_ip}/{base_path}/{image_name} {dest_path}"
    elif protocol == 'scp':
        # SCP requires username
        cmd = f"copy scp://admin@{server_ip}/{base_path}/{image_name} {dest_path}"
    else:
        raise ValueError(f"Unsupported protocol: {protocol}")

    # Add source interface if specified
    if source_interface:
        cmd = f"{cmd} source interface {source_interface}"

    return cmd


def _check_file_size(connection, platform: str, image_name: str, expected_size: int) -> Dict[str, Any]:
    """
    Check if the downloaded file has the expected size.

    Args:
        connection: Active connection object (unicon)
        platform: Platform name (cisco_iosxe, cisco_nxos)
        image_name: Image filename
        expected_size: Expected file size in bytes

    Returns:
        Dictionary with 'success' and 'message' keys
    """
    if 'nx-os' in platform.lower():
        dest_path = f"bootflash:/{image_name}"
    else:
        dest_path = f"flash:/{image_name}"

    try:
        output = connection.execute(f"dir {dest_path}", timeout=30)
        # Parse file size from dir output
        import re
        match = re.search(r'\s+(\d+)\s+\w{3}\s+\d+', output)
        if match:
            actual_size = int(match.group(1))
            if actual_size == expected_size:
                return {'success': True}
            else:
                return {'success': False, 'message': f'File size mismatch. Expected: {expected_size} bytes, Got: {actual_size} bytes'}
        return {'success': False, 'message': 'Could not parse file size from dir output'}
    except Exception as e:
        return {'success': False, 'message': f'Failed to check file size: {e}'}


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

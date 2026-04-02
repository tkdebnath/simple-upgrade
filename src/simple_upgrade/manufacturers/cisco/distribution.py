"""
Cisco IOS-XE distribution module - Downloads firmware image to device.

This module provides Cisco-specific image distribution using unicon.
Supports: HTTP, HTTPS protocols.

Workflow:
    1. Push pre-download config (source interface, HTTP settings)
    2. Smart download check (skip if file exists with matching size/MD5)
    3. Execute copy command with dialog for interactive prompts
    4. Post-download verification (size check + MD5 check)
"""

import re
from typing import Dict, Any, Optional


def distribute_image(
    connection,
    platform: str,
    file_server: Dict[str, Any],
    golden_image: Dict[str, Any],
    source_interface: Optional[str] = None
) -> Dict[str, Any]:
    """
    Distribute firmware image to Cisco device.

    Args:
        connection: Active connection object (unicon)
        platform: Platform name (cisco_iosxe)
        file_server: Dictionary with file server information
            - ip: File server IP address
            - protocol: Transfer protocol (http, https)
            - base_path: Base path on server
            - port: Optional port number
        golden_image: Dictionary with golden image information
            - image_name: Image filename
            - image_size: Expected file size in bytes
            - md5: Expected MD5 checksum
        source_interface: Optional source interface for HTTP client

    Returns:
        Dictionary with:
            - success: Boolean indicating success
            - message: Status message
            - command: Command executed
            - skipped: Boolean if download was skipped (file already exists)
    """
    result = {
        'success': False,
        'message': '',
        'command': '',
        'skipped': False,
    }

    protocol = file_server.get('protocol', 'http').lower()

    # Check if protocol is http or https (tftp/ftp/scp are disabled)
    if protocol not in ['http', 'https']:
        result['message'] = f'Unsupported protocol: {protocol}. Only http and https are supported.'
        return result

    image_name = golden_image.get('image_name', '')
    # Strip flash: prefix if present (avoids flash:flash: doubling)
    image_name = image_name.replace('flash:/', '').replace('flash:', '')

    server_ip = file_server.get('ip', '')
    base_path = file_server.get('base_path', '').strip('/')
    expected_size = golden_image.get('image_size')
    expected_md5 = golden_image.get('md5')

    if not image_name or not server_ip:
        result['message'] = 'Missing image name or file server information'
        return result

    # ── Step 1: Push pre-download configuration ──────────────────────────
    try:
        _push_pre_download_config(connection, source_interface)
    except Exception as e:
        result['message'] = f'Failed to push pre-download config: {e}'
        return result

    # ── Step 2: Smart download check ─────────────────────────────────────
    # Check if file already exists on flash with matching size and MD5
    try:
        existing_size = _get_file_size(connection, image_name)

        if existing_size is not None and expected_size and existing_size == expected_size:
            # Size matches — verify MD5 if available
            if expected_md5:
                if _verify_file_md5(connection, image_name, expected_md5):
                    result['success'] = True
                    result['skipped'] = True
                    result['message'] = (
                        f'File {image_name} already exists on flash with '
                        f'matching size ({expected_size:,} bytes) and MD5. Skipping download.'
                    )
                    return result
                # MD5 mismatch — re-download
            else:
                # No MD5 to verify but size matches — skip download
                result['success'] = True
                result['skipped'] = True
                result['message'] = (
                    f'File {image_name} already exists on flash with '
                    f'matching size ({expected_size:,} bytes). Skipping download.'
                )
                return result
    except Exception:
        # Could not check — proceed with download
        pass

    # ── Step 3: Build and execute copy command ───────────────────────────
    path_part = f"{base_path}/{image_name}" if base_path else image_name
    copy_url = f"{protocol}://{server_ip}/{path_part}"
    copy_cmd = f"copy {copy_url} flash:{image_name}"
    result['command'] = copy_cmd

    try:
        from unicon.eal.dialogs import Dialog, Statement

        dialog = Dialog([
            Statement(
                pattern=r'Destination filename \[.*\]\?',
                action='sendline()',
                loop_continue=True
            ),
            Statement(
                pattern=r'Do you want to over write\? \[confirm\]',
                action='sendline()',
                loop_continue=True
            ),
            Statement(
                pattern=r'\[confirm\]',
                action='sendline()',
                loop_continue=True
            ),
            Statement(
                pattern=r'Address or name of remote host',
                action='sendline()',
                loop_continue=True
            ),
            Statement(
                pattern=r'%Error|TFTP .*error|Connection refused|No such file',
                action=None,
                loop_continue=False
            ),
            Statement(
                pattern=r'(?i)timed out|connection timed out',
                action=None,
                loop_continue=False
            ),
        ])

        output = connection.execute(
            copy_cmd,
            timeout=3600,       # 1 hour timeout for large files
            reply=dialog
        )

    except Exception as e:
        result['message'] = f'Exception during copy command: {str(e)}'
        return result

    # ── Step 4: Post-download verification ───────────────────────────────
    # 4a: Check copy output for success indicators
    if not _check_copy_success(output):
        result['message'] = f'Copy command did not indicate success: {str(output)[:200]}'
        return result

    # 4b: Verify file size
    if expected_size:
        actual_size = _get_file_size(connection, image_name)
        if actual_size is None:
            result['message'] = f'File {image_name} not found on flash after copy'
            return result
        if actual_size != expected_size:
            result['message'] = (
                f'Size mismatch: expected {expected_size:,} bytes, '
                f'got {actual_size:,} bytes'
            )
            return result

    # 4c: Verify MD5 checksum
    if expected_md5:
        if not _verify_file_md5(connection, image_name, expected_md5):
            result['message'] = f'MD5 verification failed. Expected: {expected_md5}'
            return result

    result['success'] = True
    result['message'] = f'Image distributed successfully: {image_name}'
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Private helpers
# ═══════════════════════════════════════════════════════════════════════════

def _push_pre_download_config(connection, source_interface: Optional[str] = None) -> None:
    """
    Push configuration required before starting the download.

    Configures HTTP client source interface if specified.

    Args:
        connection: Active unicon connection
        source_interface: Interface name (e.g., 'Loopback0', 'Vlan100')

    Raises:
        Exception: If configuration fails
    """
    if not source_interface:
        return

    connection.execute('configure terminal', timeout=30)
    connection.execute(
        f'ip http client source-interface {source_interface}',
        timeout=30
    )
    connection.execute('end', timeout=30)


def _get_file_size(connection, filename: str, destination: str = 'flash:') -> Optional[int]:
    """
    Get file size in bytes from device storage.

    Args:
        connection: Active unicon connection
        filename: Image filename
        destination: Storage destination (default: flash:)

    Returns:
        File size in bytes, or None if file not found
    """
    try:
        output = connection.execute(f'dir {destination}{filename}', timeout=30)

        if 'No such file' in output or 'Error opening' in output:
            return None

        # Standard IOS/XE dir output: "... 123456  MMM dd yyyy ..."
        match = re.search(r'\s+(\d+)\s+\w{3}\s+\d+', output)
        if match:
            return int(match.group(1))

        return None
    except Exception:
        return None


def _verify_file_md5(
    connection,
    filename: str,
    expected_md5: str,
    destination: str = 'flash:'
) -> bool:
    """
    Verify file MD5 checksum on device.

    Args:
        connection: Active unicon connection
        filename: Image filename
        expected_md5: Expected MD5 hash string
        destination: Storage destination (default: flash:)

    Returns:
        True if MD5 matches, False otherwise
    """
    if not expected_md5:
        return True

    try:
        cmd = f'verify /md5 {destination}{filename} {expected_md5}'
        output = connection.execute(cmd, timeout=600)  # 10 min for large images

        # Cisco outputs "Verified" when checksum matches
        return 'Verified' in output

    except Exception:
        return False


def _check_copy_success(output: str) -> bool:
    """
    Check if the copy command output indicates success.

    Args:
        output: Output string from the copy command

    Returns:
        True if successful, False otherwise
    """
    if isinstance(output, list):
        output = '\n'.join(output)

    output_lower = str(output).lower()

    success_indicators = [
        'bytes copied',
        'ok',
        '100% completion',
        'bytes in',
    ]

    return any(indicator in output_lower for indicator in success_indicators)

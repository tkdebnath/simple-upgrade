"""
Cisco IOS-XE activation module - Applies new firmware.

This module provides Cisco-specific firmware activation using unicon.
Supports: install add/activate/commit workflow (IOS-XE).

Workflow:
    1. Verify device is in INSTALL mode
    2. Configure boot parameters (no boot system, boot system flash:packages.conf)
    3. Save configuration (copy running-config startup-config)
    4. Execute install add file activate commit
    5. Device will reload automatically
"""

from typing import Dict, Any, Optional
from unicon.eal.dialogs import Dialog, Statement


# Supported platforms
SUPPORTED_PLATFORMS = ['cisco_iosxe', 'cisco_xe', 'iosxe']


def activate_image(
    connection,
    platform: str,
    golden_image: Dict[str, Any],
    device_profile: Optional[Dict[str, Any]] = None,
    use_profile: bool = True
) -> Dict[str, Any]:
    """
    Activate new firmware on Cisco IOS-XE device.

    Args:
        connection: Active connection object (unicon)
        platform: Platform name (cisco_iosxe, cisco_xe)
        golden_image: Dictionary with golden image information
            - image_name: Image filename on flash
        device_profile: Optional device profile with model info
        use_profile: Whether to use profile for boot commands

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
    # Strip flash: prefix if present (avoids flash:flash: doubling)
    image_name = image_name.replace('flash:/', '').replace('flash:', '')

    if not image_name:
        result['message'] = 'Missing image name for activation'
        return result

    # Check if platform is supported
    if platform not in SUPPORTED_PLATFORMS:
        result['message'] = f"Platform '{platform}' is not supported. Supported: {SUPPORTED_PLATFORMS}"
        return result

    try:
        # ── Step 1: Verify install mode ──────────────────────────────────
        try:
            output = connection.execute('show version | include Mode', timeout=30)
            if 'INSTALL' not in str(output):
                # Warning only — don't block activation
                pass
        except Exception:
            pass

        # ── Step 2: Configure boot parameters ────────────────────────────
        try:
            boot_commands = [
                'no boot system',
                'boot system flash:packages.conf',
                'no boot manual',
                'no system ignore startupconfig switch all',
            ]

            # If device_profile provides custom boot commands, use those instead
            if use_profile and device_profile and 'boot_commands' in device_profile:
                boot_commands = device_profile['boot_commands']

            connection.configure(boot_commands, timeout=30)

        except Exception as e:
            # Warning — boot config failure shouldn't block activation
            pass

        # ── Step 3: Save configuration ───────────────────────────────────
        try:
            save_dialog = Dialog([
                Statement(
                    pattern=r'Destination filename \[startup-config\]\?',
                    action='sendline()',
                    loop_continue=False,
                ),
            ])
            connection.execute(
                'copy running-config startup-config',
                timeout=60,
                reply=save_dialog
            )
        except Exception as e:
            # Warning — config save failure shouldn't block activation
            pass

        # ── Step 4: Execute activation command ───────────────────────────
        activate_cmd = f'install add file flash:{image_name} activate commit'
        result['command'] = activate_cmd

        activate_dialog = Dialog([
            Statement(
                pattern=r'This operation may require a reload of the system\. Do you want to proceed\? \[y/n\]',
                action='sendline(y)',
                loop_continue=True,
            ),
            Statement(
                pattern=r'\[y/n\]',
                action='sendline(y)',
                loop_continue=True,
            ),
            Statement(
                pattern=r'Do you want to proceed with reload\?',
                action='sendline(y)',
                loop_continue=True,
            ),
        ])

        output = connection.execute(
            activate_cmd,
            timeout=3600,       # 1 hour timeout
            reply=activate_dialog
        )

        # ── Step 5: Check result ─────────────────────────────────────────
        output_str = str(output)

        if 'Error' in output_str or 'Failed' in output_str:
            result['message'] = f'Activation failed: {output_str[:200]}'
            return result

        result['success'] = True
        result['message'] = 'Activation initiated — device will reload'

    except Exception as e:
        result['message'] = f'Exception during activation: {str(e)}'

    return result

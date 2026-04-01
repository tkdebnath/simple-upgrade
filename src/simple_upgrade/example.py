"""
Example usage of simple-upgrade package
"""

from simple_upgrade import UpgradeManager, DeviceConnectionError

# Example 1: Basic upgrade
def basic_upgrade():
    """Basic firmware upgrade example."""
    manager = UpgradeManager(
        host="192.168.1.1",
        username="admin",
        password="password123",
        port=22,
        golden_image={
            "version": "17.9.4",
            "image_name": "flash:c9300-universalk9.17.9.4.SPA.bin",
            "file_size": 512000000
        },
        file_server={
            "ip": "10.0.0.10",
            "protocol": "http",
            "base_path": "/tftpboot"
        },
        auto_update=True,
        wait_time=300
    )

    try:
        # Connect to device
        if not manager.connect():
            print("Failed to connect to device")
            return

        # Perform upgrade
        result = manager.upgrade()

        # Check results
        if result['success']:
            print("Upgrade completed successfully!")
            for stage_name, stage_result in result['stages'].items():
                print(f"  {stage_name}: {'SUCCESS' if stage_result['success'] else 'FAILED'}")
        else:
            print("Upgrade failed!")
            print("Errors:", result['errors'])

    except DeviceConnectionError as e:
        print(f"Connection error: {e}")
    finally:
        manager.disconnect()


# Example 2: Upgrade with custom parameters
def upgrade_with_custom_params():
    """Upgrade with custom timeout and retry settings."""
    manager = UpgradeManager(
        host="192.168.1.1",
        username="admin",
        password="password123",
        port=22,
        timeout=60,
        max_retries=5,
        golden_image={
            "version": "17.9.4",
            "image_name": "flash:c9300-universalk9.17.9.4.SPA.bin"
        },
        file_server={
            "ip": "10.0.0.10",
            "protocol": "scp",
            "username": "tftpuser",
            "password": "tfptpass",
            "base_path": "/images"
        },
        auto_update=True
    )

    result = manager.upgrade()
    print(result)

    manager.disconnect()


# Example 3: Check device info before upgrade
def check_device_info():
    """Check device information before upgrading."""
    manager = UpgradeManager(
        host="192.168.1.1",
        username="admin",
        password="password123"
    )

    manager.connect()

    # Get current device info
    device_info = manager.device.gather_info()
    print(f"Current device info: {device_info}")

    manager.disconnect()


if __name__ == "__main__":
    # Run example
    basic_upgrade()

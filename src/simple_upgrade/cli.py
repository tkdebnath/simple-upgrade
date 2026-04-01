"""
Command-line interface for simple-upgrade
"""

import argparse
import sys
import json
from simple_upgrade import UpgradeManager, DeviceConnectionError


def main():
    parser = argparse.ArgumentParser(
        description="Network device firmware upgrade tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic upgrade
  simple-upgrade --host 192.168.1.1 --user admin --pass password \\
    --version 17.9.4 --image flash:c9300-universalk9.17.9.4.SPA.bin \\
    --server 10.0.0.10

  # Upgrade with file server protocol
  simple-upgrade --host 192.168.1.1 --user admin --pass password \\
    --version 17.9.4 --image flash:image.bin \\
    --server 10.0.0.10 --protocol scp --base-path /images
        """
    )

    parser.add_argument('--host', '-H', required=True,
                        help='Device IP address or hostname')
    parser.add_argument('--user', '-u', required=True,
                        help='SSH username')
    parser.add_argument('--pass', '-p', dest='password', required=True,
                        help='SSH password')
    parser.add_argument('--port', type=int, default=22,
                        help='SSH port (default: 22)')
    parser.add_argument('--version', '-v', required=True,
                        help='Target firmware version')
    parser.add_argument('--image', '-i', required=True,
                        help='Firmware image path (e.g., flash:image.bin)')
    parser.add_argument('--server', '-s', required=True,
                        help='File server IP or hostname')
    parser.add_argument('--protocol', default='http',
                        choices=['http', 'https', 'ftp', 'scp', 'tftp'],
                        help='File transfer protocol (default: http)')
    parser.add_argument('--base-path', default='',
                        help='Base path on file server')
    parser.add_argument('--output', '-o',
                        help='Output file for JSON results')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')

    args = parser.parse_args()

    # Create upgrade manager
    manager = UpgradeManager(
        host=args.host,
        username=args.user,
        password=args.password,
        port=args.port,
        golden_image={
            'version': args.version,
            'image_name': args.image
        },
        file_server={
            'ip': args.server,
            'protocol': args.protocol,
            'base_path': args.base_path
        }
    )

    try:
        # Connect to device
        if not manager.connect():
            result = {'success': False, 'error': 'Failed to connect to device'}
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("Failed to connect to device")
            sys.exit(1)

        # Perform upgrade
        result = manager.upgrade()

        # Output results
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result['success']:
                print("\nUpgrade completed successfully!\n")
            else:
                print("\nUpgrade failed!\n")

            print("Stage Results:")
            print("-" * 40)
            for stage_name, stage_result in result['stages'].items():
                status = "OK" if stage_result['success'] else "FAIL"
                print(f"  {status} {stage_name}: {stage_result['message']}")

            if result['errors']:
                print("\nErrors:")
                for error in result['errors']:
                    print(f"  - {error}")

            # Save to file if specified
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                print(f"\nResults saved to {args.output}")

        # Disconnect
        manager.disconnect()

        # Exit with appropriate code
        sys.exit(0 if result['success'] else 1)

    except DeviceConnectionError as e:
        result = {'success': False, 'error': str(e)}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Connection error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nUpgrade cancelled by user")
        manager.disconnect()
        sys.exit(130)


if __name__ == '__main__':
    main()

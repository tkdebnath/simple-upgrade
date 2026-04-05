import sys
import json
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from simple_upgrade import UpgradePackage

def main():
    print("Initializing UpgradePackage with live network configuration...")
    pkg = UpgradePackage(
        host="172.20.20.11",
        username="admin",
        password="admin",
        enable_password="admin",
        platform="cisco_iosxe",
        manufacturer="cisco",
        connection_mode="normal",
        source_interface="GigabitEthernet0/0",
        source_vrf="Mgmt-vrf",
        # activation stage
        post_wait_delay=10,
        post_wait_retries=60,
        post_wait_convergence=30,
        # golden image
        golden_image={
            "version": "17.13.1",
            "image_name": "test_file_30M.bin",
            "image_size": 31457280,
            "md5": "281ed1d5ae50e8419f9b978aab16de83",
            "sha256": "abcdef1234567890",
        },
        file_server={
            "protocol": "http",
            "ip": "192.168.29.73",
            "port": 5000,
            "base_path": "/",
            "username": "ftpuser",
            "password": "ftppassword",
        }
    )

    print("\nExecuting actual Live pipeline interactively...")
    
    for stage in pkg.STAGES:
        if pkg.ctx.failed_stage and stage != 'diff':
            print(f"[-] Skipping stage '{stage}' (Pipeline halted due to error in '{pkg.ctx.failed_stage}')")
            continue  # Skip steps automatically if pipeline is in a failed state
            
        print("-" * 50)
        action = input(f"\n[?] Ready to execute stage: '{stage}'. Press Enter to proceed (or 'q' to quit): ").strip().lower()
        
        if action == 'q':
            print("\nAborting manual test execution.")
            break
            
        print(f"[*] Running stage '{stage}'...")
        res = pkg.run_stage(stage)
        print(f"\n[+] '{stage}' RESULT:")
        print(json.dumps(res.model_dump(), indent=2))
        
    print("\n--- FINAL CONTEXT ERRORS ---")
    if pkg.errors:
        for err in pkg.errors:
            print(f"  - {err}")
    else:
        print("  No Pipeline Errors.")

if __name__ == "__main__":
    main()

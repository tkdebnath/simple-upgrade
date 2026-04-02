from simple_upgrade import UpgradePackage, GoldenImage, FileServer

def test_mock_upgrade():
    # Configure the orchestrator
    orchestrator = UpgradePackage(
        host="10.10.10.1",
        username="admin",
        password="password",
        manufacturer="cisco"
    )
    
    # Setup context
    orchestrator.golden_image = GoldenImage(
        version="17.9.4",
        image_name="cat9k_iosxe.17.09.04.SPA.bin"
    )
    orchestrator.file_server = FileServer(
        ip="10.10.10.5",
        protocol="http"
    )
    
    # Set connection mode to mock
    orchestrator.connection_mode = "mock"
    
    # Run upgrade stages
    print("\n" + "="*60)
    print("  Running Mock Upgrade Pipeline (V3 Architecture)")
    print("="*60)
    
    stages = ["sync", "readiness", "pre_check", "distribute", "activate"]
    for stage in stages:
        print(f"\n[STAGING] Running: {stage}...")
        result = orchestrator.run_stage(stage)
        status = "PASS" if result.success else "FAIL"
        print(f"[{status}] {stage}: {result.message}")
        if result.data:
            print(f"       Data: {result.data}")
            
    # Print overall result
    print("\n" + "="*60)
    print("  Final Device Information")
    print("="*60)
    info = orchestrator.context.device_info
    print(f"  Manufacturer : {info.manufacturer}")
    print(f"  Model        : {info.model}")
    print(f"  Version      : {info.version}")
    print(f"  Hostname     : {info.hostname}")
    print(f"  Serial       : {info.serial}")

if __name__ == "__main__":
    test_mock_upgrade()

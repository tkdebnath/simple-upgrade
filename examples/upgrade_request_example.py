"""
upgrade_request_example.py
==========================
Demonstrates how a firmware upgrade request is initiated using the
simple-upgrade framework. Covers all supported input patterns.

Run in mock mode (no real device needed):
    python3 examples/upgrade_request_example.py

Run against a real device:
    UPGRADE_MODE=normal python3 examples/upgrade_request_example.py
"""

import os
import json
from simple_upgrade import UpgradePackage, GoldenImage, FileServer

# ─────────────────────────────────────────────────────────────────────────────
# Connection mode: "mock" (default) | "normal" | "dry_run"
# Override via env var for CI/real device runs.
# ─────────────────────────────────────────────────────────────────────────────
CONNECTION_MODE = os.environ.get("UPGRADE_MODE", "mock")


# ═════════════════════════════════════════════════════════════════════════════
# 1. FULL GOLDEN IMAGE SPECIFICATION
#    Every field that GoldenImage supports.
# ═════════════════════════════════════════════════════════════════════════════
golden_image = GoldenImage(
    # Target software version (used for verification post-upgrade)
    version="17.09.04a",

    # Exact filename as it exists on the file server
    image_name="cat9k_iosxe.17.09.04a.SPA.bin",

    # Optional: expected file size in bytes (integrity guard)
    image_size=897_286_144,   # ~856 MB

    # Optional: MD5 checksum for transfer validation
    md5="a3f1e2d4c5b6789012345678abcdef01",

    # Optional: SHA-256 checksum (preferred over MD5)
    sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
)


# ═════════════════════════════════════════════════════════════════════════════
# 2. FULL FILE SERVER SPECIFICATION
#    Every field that FileServer supports.
# ═════════════════════════════════════════════════════════════════════════════
file_server = FileServer(
    # IP address of the TFTP / HTTP / FTP / SCP server
    ip="10.10.10.5",

    # Transfer protocol: "http" | "tftp" | "ftp" | "scp"
    protocol="http",

    # Optional: sub-directory on the server where the image lives
    base_path="/images/cisco/cat9k",

    # Optional: non-standard port (default 80 for http, 69 for tftp, etc.)
    port=8080,

    # Optional: authentication (required for FTP / SCP)
    username="imageuser",
    password="Sup3rS3cur3!",

    # Optional: source interface on the device used for the transfer
    source_interface="GigabitEthernet0/0",
)


# ═════════════════════════════════════════════════════════════════════════════
# 3. PATTERN A — Pass all config at construction time (recommended)
# ═════════════════════════════════════════════════════════════════════════════
def example_inline_config():
    """All inputs provided in the constructor — cleanest pattern."""
    print("\n" + "=" * 65)
    print("  PATTERN A: Inline constructor config")
    print("=" * 65)

    upgrade = UpgradePackage(
        # ── Device connection ────────────────────────────────────────
        host="192.168.1.10",
        username="admin",
        password="C!sc0Admin",
        port=22,

        # ── Enable / privilege-exec password (optional) ───────────────
        # Required when the device needs "enable" after SSH login.
        # Maps to auth_secondary in Scrapli and credentials[enable]
        # in Unicon. Leave as None if not needed.
        enable_password="Enabl3S3cret!",

        # ── Manufacturer & platform ──────────────────────────────────
        manufacturer="cisco",
        platform="cisco_iosxe",

        # ── Golden image dict (converted to GoldenImage internally) ──
        golden_image={
            "version": "17.09.04a",
            "image_name": "cat9k_iosxe.17.09.04a.SPA.bin",
            "image_size": 897_286_144,
            "md5": "a3f1e2d4c5b6789012345678abcdef01",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },

        # ── File server dict (converted to FileServer internally) ─────
        file_server={
            "ip": "10.10.10.5",
            "protocol": "http",
            "base_path": "/images/cisco/cat9k",
            "port": 8080,
            "username": "imageuser",
            "password": "Sup3rS3cur3!",
            "source_interface": "GigabitEthernet0/0",
        },

        # ── Execution mode ────────────────────────────────────────────
        connection_mode=CONNECTION_MODE,
    )

    _run_and_print(upgrade, "Pattern A")


# ═════════════════════════════════════════════════════════════════════════════
# 4. PATTERN B — Use model objects directly (explicit & type-safe)
# ═════════════════════════════════════════════════════════════════════════════
def example_model_objects():
    """GoldenImage and FileServer built as Pydantic objects before passing."""
    print("\n" + "=" * 65)
    print("  PATTERN B: Explicit Pydantic model objects")
    print("=" * 65)

    upgrade = UpgradePackage(
        host="192.168.1.10",
        username="admin",
        password="C!sc0Admin",
        enable_password="Enabl3S3cret!",   # optional — needed for 'enable' mode
        manufacturer="cisco",
        platform="cisco_iosxe",
        connection_mode=CONNECTION_MODE,
        golden_image=golden_image.model_dump() if hasattr(golden_image, 'model_dump') else golden_image,
        file_server=file_server.model_dump() if hasattr(file_server, 'model_dump') else file_server,
    )

    _run_and_print(upgrade, "Pattern B")


# ═════════════════════════════════════════════════════════════════════════════
# 5. PATTERN C — Stage-by-stage execution (granular control)
#    Useful when you want to gate each stage on external approval,
#    custom logging, or integration with a workflow engine.
# ═════════════════════════════════════════════════════════════════════════════
def example_stage_by_stage():
    """Run each stage individually with full result inspection."""
    print("\n" + "=" * 65)
    print("  PATTERN C: Stage-by-stage execution")
    print("=" * 65)

    upgrade = UpgradePackage(
        host="192.168.1.10",
        username="admin",
        password="C!sc0Admin",
        enable_password="Enabl3S3cret!",   # optional
        manufacturer="cisco",
        platform="cisco_iosxe",
        connection_mode=CONNECTION_MODE,
        golden_image=golden_image.model_dump() if hasattr(golden_image, 'model_dump') else golden_image,
        file_server=file_server.model_dump() if hasattr(file_server, 'model_dump') else file_server,
    )

    stages = [
        "sync",
        "readiness",
        "pre_check",
        "distribute",
        "activate",
        "post_activation_wait",
        "post_check",
    ]

    for stage in stages:
        print(f"\n  ▶  Running stage: {stage}")
        result = upgrade.run_stage(stage)

        status_icon = "✅" if result.success else "❌"
        print(f"     {status_icon}  {result.message}")
        print(f"     Duration : {result.duration:.2f}s")

        if result.data:
            print(f"     Data     : {json.dumps(result.data, indent=6)}")

        if result.errors:
            print(f"     Errors   : {result.errors}")

        # Gate: stop on first failure (same as execute() behaviour)
        if not result.success:
            print(f"\n  ⛔  Pipeline halted at stage '{stage}'.")
            break

    # Print final device info discovered during sync
    _print_device_info(upgrade)


# ═════════════════════════════════════════════════════════════════════════════
# 6. PATTERN D — Full execute() bulk run (fire-and-get-summary)
# ═════════════════════════════════════════════════════════════════════════════
def example_full_execute():
    """Run the entire pipeline in one call and receive a results dict."""
    print("\n" + "=" * 65)
    print("  PATTERN D: Full execute() — complete pipeline")
    print("=" * 65)

    upgrade = UpgradePackage(
        host="192.168.1.10",
        username="admin",
        password="C!sc0Admin",
        enable_password="Enabl3S3cret!",   # optional
        manufacturer="cisco",
        platform="cisco_iosxe",
        golden_image={
            "version": "17.09.04a",
            "image_name": "cat9k_iosxe.17.09.04a.SPA.bin",
            "image_size": 897_286_144,
            "md5": "a3f1e2d4c5b6789012345678abcdef01",
        },
        file_server={
            "ip": "10.10.10.5",
            "protocol": "http",
            "base_path": "/images/cisco/cat9k",
        },
        connection_mode=CONNECTION_MODE,
    )

    results = upgrade.execute()

    print("\n  Stage Summary:")
    print(f"  {'Stage':<25} {'Status':<8} {'Message'}")
    print(f"  {'-'*25} {'-'*7} {'-'*35}")
    for stage, res in results.items():
        status = "PASS" if res["success"] else "FAIL"
        print(f"  {stage:<25} {status:<8} {res['message']}")

    _print_device_info(upgrade)


# ═════════════════════════════════════════════════════════════════════════════
# 7. PATTERN E — Multi-device upgrade (batch loop)
# ═════════════════════════════════════════════════════════════════════════════
def example_multi_device():
    """Upgrade a list of devices with shared golden image and file server."""
    print("\n" + "=" * 65)
    print("  PATTERN E: Multi-device batch upgrade")
    print("=" * 65)

    devices = [
        {"host": "192.168.1.10", "username": "admin",   "password": "C!sc0Admin",  "enable_password": "Enabl3S3cret!", "manufacturer": "cisco"},
        {"host": "192.168.1.11", "username": "netops",  "password": "N3t0ps2024!", "enable_password": None,             "manufacturer": "cisco"},
        {"host": "192.168.1.12", "username": "svcacct", "password": "Svc@99!xK",   "enable_password": "Svc@Enable99!", "manufacturer": "cisco"},
    ]

    shared_image = {
        "version": "17.09.04a",
        "image_name": "cat9k_iosxe.17.09.04a.SPA.bin",
        "image_size": 897_286_144,
        "md5": "a3f1e2d4c5b6789012345678abcdef01",
    }

    shared_server = {
        "ip": "10.10.10.5",
        "protocol": "http",
        "base_path": "/images/cisco/cat9k",
    }

    summary = []

    for device in devices:
        upgrade = UpgradePackage(
            **device,
            platform="cisco_iosxe",
            golden_image=shared_image,
            file_server=shared_server,
            connection_mode=CONNECTION_MODE,
        )

        # Run only the critical stages for this demo
        for stage in ["sync", "readiness", "pre_check", "distribute", "activate"]:
            result = upgrade.run_stage(stage)
            if not result.success:
                break

        summary.append({
            "host":    device["host"],
            "success": upgrade.success,
            "device":  upgrade.ctx.device_info.model_dump(),
        })

    print("\n  Batch Results:")
    print(f"  {'Host':<16} {'Status':<8} {'Model':<12} {'Version'}")
    print(f"  {'-'*16} {'-'*7} {'-'*12} {'-'*15}")
    for s in summary:
        status = "PASS" if s["success"] else "FAIL"
        model   = s["device"].get("model")   or "—"
        version = s["device"].get("version") or "—"
        print(f"  {s['host']:<16} {status:<8} {model:<12} {version}")


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

def _run_and_print(upgrade: UpgradePackage, label: str):
    stages = ["sync", "readiness", "pre_check", "distribute", "activate"]
    results = []
    for stage in stages:
        result = upgrade.run_stage(stage)
        results.append((stage, result))
        if not result.success:
            break

    print(f"\n  Results ({label}):")
    for stage, r in results:
        icon = "✅" if r.success else "❌"
        print(f"    {icon}  [{stage:<25}] {r.message}")

    _print_device_info(upgrade)


def _print_device_info(upgrade: UpgradePackage):
    info = upgrade.ctx.device_info
    print("\n  Device Discovered:")
    print(f"    Hostname     : {info.hostname or '—'}")
    print(f"    Manufacturer : {info.manufacturer}")
    print(f"    Model        : {info.model or '—'}")
    print(f"    Version      : {info.version or '—'}")
    print(f"    Serial       : {info.serial or '—'}")
    print(f"    Platform     : {info.platform or '—'}")


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n  🔧  Running in [{CONNECTION_MODE.upper()}] mode")
    print("  Set UPGRADE_MODE=normal to run against a real device.\n")

    example_inline_config()
    example_model_objects()
    example_stage_by_stage()
    example_full_execute()
    example_multi_device()

    print("\n" + "=" * 65)
    print("  ✅  All examples completed.")
    print("=" * 65 + "\n")

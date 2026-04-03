"""
Cisco distribution task.

Handles interactive copy-command prompts via unicon.eal.dialogs,
smart-skip if the image already exists with matching size/MD5,
and post-download MD5 verification.
"""

import re
from unicon.eal.dialogs import Dialog, Statement
from ...registry import register_stage
from ...base import BaseTask, StageResult


# ── Dialog: handles all interactive prompts during 'copy' ─────────────────
COPY_DIALOG = Dialog([
    Statement(
        pattern=r'Destination filename \[.*\]\?',
        action='sendline()',        # accept default filename
        loop_continue=True
    ),
    Statement(
        pattern=r'Do you want to over write\? \[confirm\]',
        action='sendline()',        # confirm overwrite
        loop_continue=True
    ),
    Statement(
        pattern=r'\[confirm\]',
        action='sendline()',        # any generic confirm prompt
        loop_continue=True
    ),
    Statement(
        pattern=r'Address or name of remote host',
        action='sendline()',        # accept default (shouldn't appear for URL copy)
        loop_continue=True
    ),
])


@register_stage('distribute', 'cisco')
class CiscoDistributeTask(BaseTask):
    @property
    def name(self) -> str: return "distribute"

    def run(self, **kwargs) -> StageResult:
        """Transfer the golden image to device flash using Unicon + Dialog."""
        img    = self.ctx.golden_image.image_name
        fs     = self.ctx.file_server
        base   = fs.base_path.strip("/")
        path   = f"{base}/{img}" if base else img
        port   = f":{fs.port}" if fs.port else ""
        url    = f"{fs.protocol}://{fs.ip}{port}/{path}"
        dest   = "flash:"
        cmd    = f"copy {url} {dest}"

        if self.ctx.connection_mode != "normal":
            return self._success(f"[MOCK] Would execute: {cmd}")

        conn = self.unicon   # Unicon required for interactive prompt handling

        # ── Smart-skip: check if file already exists and is valid ──────────
        if self._file_valid(conn, img, dest):
            return self._success(f"{img} already present and verified — skipping download")

        # ── Execute copy with Dialog-based prompt handler ──────────────────
        self._log(f"Starting transfer: {url} → {dest}")
        result = conn.execute(cmd, timeout=3600, reply=COPY_DIALOG)

        # ── Verify transfer succeeded (bytes copied in output) ─────────────
        if not self._transfer_ok(result, img, dest, conn):
            return self._fail(f"Transfer failed or file not found on {dest} after copy")

        # ── Post-download MD5 verification ─────────────────────────────────
        if self.ctx.golden_image.md5:
            if not self._verify_md5(conn, img, self.ctx.golden_image.md5, dest):
                return self._fail("Post-download MD5 verification failed")

        return self._success(f"Successfully distributed {img} to {dest}")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _file_valid(self, conn, filename: str, dest: str) -> bool:
        """Return True if file exists on device with matching size (and MD5 if provided)."""
        size_on_device = self._get_file_size(conn, filename, dest)
        if size_on_device is None:
            return False

        expected = self.ctx.golden_image.image_size
        if expected and size_on_device != expected:
            self._log(f"Size mismatch: expected {expected:,} got {size_on_device:,} — re-downloading")
            return False

        if self.ctx.golden_image.md5:
            return self._verify_md5(conn, filename, self.ctx.golden_image.md5, dest)

        self._log(f"File found ({size_on_device:,} bytes) but no MD5 provided — re-downloading to ensure integrity")
        return False

    def _get_file_size(self, conn, filename: str, dest: str):
        """Return file size in bytes from 'dir' output, or None if not found."""
        try:
            out = conn.execute(f"dir {dest}{filename}", timeout=30)
            if "No such file" in out or "Error opening" in out:
                return None
            m = re.search(r'\s+(\d+)\s+\w{3}\s+\d+', out)
            return int(m.group(1)) if m else None
        except Exception:
            return None

    def _verify_md5(self, conn, filename: str, expected: str, dest: str) -> bool:
        """Run 'verify /md5' on device and compare checksum."""
        self._log(f"Verifying MD5 for {filename}…")
        try:
            out = conn.execute(
                f"verify /md5 {dest}{filename} {expected}",
                timeout=600   # 10 min — large images on slow flash
            )
            if "Verified" in out:
                self._log("MD5 verified ✓")
                return True
            self._log(f"MD5 mismatch. Output: {out}")
            return False
        except Exception as e:
            self._log(f"MD5 verification error: {e}")
            return False

    def _transfer_ok(self, output: str, filename: str, dest: str, conn) -> bool:
        """Check 'bytes copied' in output, or fall back to checking flash."""
        if re.search(r'\d+\s+bytes copied', output, re.IGNORECASE):
            return True
        if "OK" in output:
            return True
        # Fallback: confirm file appears in flash dir
        return self._get_file_size(conn, filename, dest) is not None

    def _log(self, msg: str):
        print(f"[distribute] {msg}")

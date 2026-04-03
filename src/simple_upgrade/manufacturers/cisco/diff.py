"""
Cisco diff and reporting task.

Compares pre_check and post_check outputs, generates diff patches, 
dumps the execution log, and packages everything into an audit zip.
"""

import os
import json
import shutil
import difflib
from datetime import datetime
from ...registry import register_stage
from ...base import BaseTask, StageResult


@register_stage('diff', 'cisco')
class CiscoDiffTask(BaseTask):
    @property
    def name(self) -> str: return "diff"

    def run(self, **kwargs) -> StageResult:
        """Generate final operational diffs and compress the artifact bundle."""
        hostname = self.ctx.device_info.hostname or "device"
        base_dir = os.path.join("output", hostname)
        
        pre_dir = os.path.join(base_dir, "precheck")
        post_dir = os.path.join(base_dir, "postcheck")
        diff_dir = os.path.join(base_dir, "diff")

        if self.ctx.connection_mode != "normal":
            return self._success(
                "[MOCK] Simulated diff generation and log packaging",
                data={"zip_path": f"output/{hostname}_upgrade_report.zip"}
            )

        # 1. Condition requirement: pre and post check folders must both exist
        if not os.path.exists(pre_dir) or not os.path.exists(post_dir):
            return self._success("Diff generation skipped: Pre-check or Post-check directories are missing.")

        # 2. Generate Diffs
        os.makedirs(diff_dir, exist_ok=True)
        diff_count = 0
        
        for filename in os.listdir(post_dir):
            if not filename.endswith(".txt"): continue
            
            pre_file = os.path.join(pre_dir, filename)
            post_file = os.path.join(post_dir, filename)
            diff_file = os.path.join(diff_dir, filename.replace(".txt", ".diff"))
            
            if os.path.exists(pre_file):
                with open(pre_file, "r") as f_pre, open(post_file, "r") as f_post:
                    pre_lines = f_pre.readlines()
                    post_lines = f_post.readlines()
                    
                diff = list(difflib.unified_diff(
                    pre_lines, post_lines, 
                    fromfile=f"precheck/{filename}", 
                    tofile=f"postcheck/{filename}",
                    n=3 # Lines of context
                ))
                
                if diff:  # Only write out diff files if there are actual deviations
                    with open(diff_file, "w") as f_diff:
                        f_diff.writelines(diff)
                    diff_count += 1

        # 3. Dump complete execution log
        log_path = os.path.join(base_dir, "execution_log.json")
        execution_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_device": self.ctx.device_info.model_dump(),
            "golden_image": self.ctx.golden_image.model_dump(),
            "file_server": self.ctx.file_server.model_dump(),
            "errors": self.ctx.errors,
            "overall_success": self.ctx.failed_stage is None,
            "stages": {name: res.model_dump() for name, res in self.ctx.stage_results.items()}
        }
        with open(log_path, "w") as f:
            json.dump(execution_report, f, indent=4)

        # 4. Zip the entire output directory
        zip_base_name = os.path.join("output", f"{hostname}_upgrade_report")
        try:
            shutil.make_archive(zip_base_name, 'zip', base_dir)
            zip_path = f"{zip_base_name}.zip"
        except Exception as e:
            return self._fail(f"Failed to create artifact bundle: {e}")

        return self._success(
            f"Diff generated ({diff_count} changes detected) and artifact bundled to {zip_path}",
            data={"diff_count": diff_count, "zip_path": zip_path}
        )

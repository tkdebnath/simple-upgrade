"""
Global Profile Configuration Validator.

Scans the JSON device profiles before execution to ensure strict data integrity.
Detects overlapping model regexes (race conditions) and missing schema requirements.
"""

import os
import glob
import json
import re
from typing import Dict, List, Any


class ProfileValidationError(Exception):
    """Raised when JSON device profiles fail integrity checks."""
    pass


class ProfileValidator:
    """Recursively lints and guarantees the integrity of all JSON device templates."""

    def __init__(self, profiles_dir: str):
        self.profiles_dir = profiles_dir
        self.loaded_profiles: Dict[str, Dict[str, Any]] = {}
        
    def validate_all(self):
        """Execute full suite of integrity checks across the configuration tree."""
        self._load_profiles()
        self._check_required_keys()
        self._check_for_overlapping_models()

    def _load_profiles(self):
        """Load all JSON files excluding the groups directory."""
        pattern = os.path.join(self.profiles_dir, "**", "*.json")
        for filepath in glob.glob(pattern, recursive=True):
            if "groups" in filepath:
                continue  # Skip group templates, only root templates dictate paths

            filename = os.path.basename(filepath)
            try:
                with open(filepath, 'r') as f:
                    self.loaded_profiles[filename] = json.load(f)
            except json.JSONDecodeError as e:
                raise ProfileValidationError(f"File {filename} contains invalid JSON syntax: {e}")

    def _check_required_keys(self):
        """Ensure all templates possess the minimum strict routing requirements."""
        required = {"manufacturer", "models"}
        for filename, data in self.loaded_profiles.items():
            missing = required - set(data.keys())
            if missing:
                raise ProfileValidationError(
                    f"Profile '{filename}' is structurally invalid. Missing required keys: {missing}"
                )

    def _check_for_overlapping_models(self):
        """
        Prevent race conditions by ensuring no two JSON files map the same 
        model string across the same OS footprint.
        """
        # Map: "RegexPattern" -> "Filename"
        global_regex_map: Dict[str, str] = {}

        for filename, data in self.loaded_profiles.items():
            models = data.get("models", [])
            if isinstance(models, str):
                models = [models]

            for pattern_str in (models or []):
                # We enforce that the exact same exact regex string shouldn't exist in two files
                # Note: A true regex intersection test is highly complex. This strictly prevents 
                # developers from literally pasting "C9300.*" into two separate JSON blobs.
                key = pattern_str.strip().lower()
                
                if key in global_regex_map:
                    conflicting_file = global_regex_map[key]
                    raise ProfileValidationError(
                        f"CRITICAL OVERLAP DETECTED: The model pattern '{pattern_str}' exists inside "
                        f"both '{filename}' and '{conflicting_file}'. This creates a severe pipeline "
                        f"race condition. You must ensure models are mutually exclusive across device profiles!"
                    )
                global_regex_map[key] = filename


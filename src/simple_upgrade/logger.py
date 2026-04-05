"""
Global Execution Logger for Simple-Upgrade.

Transparently captures both application standard output (print statements) 
and native Network Engine logging (Unicon/Scrapli) into a persistent formatted 
text file with timestamps, while continuing to stream natively to the terminal.
"""

import sys
import os
import re
import logging
from datetime import datetime


class TeeStreamLogger:
    """
    Transparent proxy that intersects sys.stdout and sys.stderr.
    Streams to the original terminal while cleanly writing timestamped
    clones into the execution text log.
    """
    def __init__(self, filename: str, stream):
        self.terminal = stream
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.log_file = open(filename, 'a', encoding='utf-8')

        # Regex to detect if an output string (like Unicon) already natively contains a timestamp
        self.has_timestamp = re.compile(r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}')

    def write(self, message: str):
        # 1. Output normally to the terminal
        self.terminal.write(message)
        
        # 2. Reformat and save to the text log
        if message.strip():
            # If the engine (e.g. Unicon) already stamped it, save as-is
            if self.has_timestamp.match(message.strip()):
                self.log_file.write(message)
            else:
                # If it's a raw print() statement, natively inject the timestamp
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                # we don't prepend basic newlines, we strictly format text boundaries
                formatted_lines = [f"{ts}: [framework] {line}" if line else "" for line in message.split("\n")]
                self.log_file.write("\n".join(formatted_lines))
        else:
            self.log_file.write(message)
            
        self.log_file.flush()

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()
        
    def close(self):
        self.log_file.close()


def enable_global_logging(host: str) -> str:
    """
    Initialize the absolute logging tracker for a specific host deployment.
    Returns the absolute path to the generated log file.
    """
    log_dir = os.path.abspath(os.path.join(os.getcwd(), "output", host))
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "execution_cli.log")

    # 1. Start with a clean separation block in the log
    with open(log_file, "a") as f:
        f.write("\n" + "="*80 + "\n")
        f.write(f"=== DEPLOYMENT STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        f.write("="*80 + "\n\n")

    # 2. Hijack terminal streams to passively catch all raw generic prints
    if not isinstance(sys.stdout, TeeStreamLogger):
        sys.stdout = TeeStreamLogger(log_file, sys.stdout)
    if not isinstance(sys.stderr, TeeStreamLogger):
        sys.stderr = TeeStreamLogger(log_file, sys.stderr)

    # 3. Synchronise the Python standard logging module (To natively catch Unicon/Scrapli internals)
    logger = logging.getLogger()
    
    # Avoid attaching multiple duplicate handlers if run in a loop
    has_file_handler = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    if not has_file_handler:
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s: %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
    return log_file

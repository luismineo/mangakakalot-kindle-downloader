import os
import sys
import logging
from pathlib import Path

# Paths
BASE_DIR = Path.cwd() / "downloads"
PROFILE_PATH = Path.cwd() / "browser_profile_uc"

# Ensure external tools are in PATH
os.environ["PATH"] = r"C:\Program Files\7-Zip" + os.pathsep + os.environ["PATH"]

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler("pipeline.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

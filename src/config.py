import os
import sys
import logging
from pathlib import Path

# Paths
BASE_DIR = Path.cwd() / "downloads"
PROFILE_PATH = Path.cwd() / "browser_profile_uc"

# Downloads concorrentes. Manter entre 5 e 8: acima disso o site passa a
# responder 429 / banir o IP.
DEFAULT_WORKERS = 6

# Ensure external tools are in PATH
os.environ["PATH"] = r"C:\Program Files\7-Zip" + os.pathsep + os.environ["PATH"]

def setup_logging(verbose: bool = False):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler("pipeline.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

import sys
import subprocess
import logging
from pathlib import Path
from src.config import BASE_DIR

class KCCConverter:
    def __init__(self, profile="KPW6"):
        self.profile = profile

    def run(self, manga_title: str):
        manga_path = BASE_DIR / manga_title
        if not manga_path.exists() or not any(manga_path.iterdir()):
            logging.warning(f"No downloaded chapters found for '{manga_title}'. Skipping KCC.")
            return

        project_root = Path(__file__).parent.parent.parent
        kcc_script_path = project_root / "src" / "vendor" / "kcc" / "kcc-c2e.py"

        if not kcc_script_path.exists():
            logging.error(f"KCC script not found! Please check your folder structure.")
            logging.error(f"Attempted path: {kcc_script_path}")
            return

        logging.info(f"Starting KCC conversion: {manga_title}")
        kcc_command = [
            sys.executable,
            str(kcc_script_path),
            "-p",
            self.profile,
            "-m",
            "-f",
            "MOBI",
            "-b",
            "1",
            "-d",
            str(manga_path),
        ]

        try:
            subprocess.run(
                kcc_command,
                check=True,
                cwd=str(kcc_script_path.parent),
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"Error executing KCC: {e}")

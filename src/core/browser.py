import platform
import subprocess
import re
import logging
# pyrefly: ignore [missing-import]
import undetected_chromedriver as uc
from src.config import PROFILE_PATH

class BrowserManager:
    def __init__(self):
        self.driver = self._init_driver()

    def get_chrome_major_version(self):
        system = platform.system()
        try:
            if system == 'Windows':
                import winreg
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Google\Chrome\BLBeacon')
                    version, _ = winreg.QueryValueEx(key, 'version')
                    return int(version.split('.')[0])
                except FileNotFoundError:
                    cmd = r'wmic datafile where name="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" get Version /value'
                    output = subprocess.check_output(cmd, shell=True).decode('utf-8')
                    match = re.search(r'Version=(\d+)', output)
                    if match:
                        return int(match.group(1))
                        
            elif system == 'Darwin':
                output = subprocess.check_output(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version']).decode('utf-8')
                match = re.search(r'Chrome (\d+)', output)
                if match:
                    return int(match.group(1))
                    
            elif system == 'Linux':
                output = subprocess.check_output(['google-chrome', '--version']).decode('utf-8')
                match = re.search(r'Chrome (\d+)', output)
                if match:
                    return int(match.group(1))
                    
        except Exception as e:
            logging.warning(f"Could not detect Chrome Version: {e}")
            
        return None

    def _init_driver(self):
        options = uc.ChromeOptions()
        options.user_data_dir = str(PROFILE_PATH)
        options.add_argument("--no-first-run")
        options.add_argument("--password-store=basic")
        options.add_argument("--window-size=1280,720")
        options.add_argument("--test-type")

        chrome_version = self.get_chrome_major_version()

        if chrome_version:
            return uc.Chrome(options=options, user_data_dir=str(PROFILE_PATH), use_subprocess=True, version_main=chrome_version)
        else:
            logging.info("Starting ChromeDriver with self-detection version.")
            return uc.Chrome(options=options, user_data_dir=str(PROFILE_PATH), use_subprocess=True)

    def close(self):
        try:
            self.driver.close()
            self.driver.quit()
        except:
            pass

import argparse
import subprocess
import sys
import logging
import time
import re
import os
import json
import requests
import io
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

os.environ["PATH"] = r"C:\Program Files\7-Zip" + os.pathsep + os.environ["PATH"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def sanitize_name(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


class MangaPipeline:
    def __init__(self, args):
        self.args = args
        self.base_dir = Path.cwd() / "downloads"
        self.base_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.driver = self._init_driver()

    def _init_driver(self):
        profile_path = os.path.join(os.getcwd(), "browser_profile_uc")
        options = uc.ChromeOptions()
        options.user_data_dir = profile_path
        options.add_argument("--no-first-run")
        options.add_argument("--password-store=basic")
        options.add_argument("--window-size=1280,720")
        options.add_argument("--test-type")
        return uc.Chrome(options=options, use_subprocess=True)

    def fetch_metadata(self):
        logging.info(f"Accessing: {self.args.url}")
        self.driver.get(self.args.url)

        manga_slug = self.args.url.split("/")[-1]
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".manga-info-content h1"))
        )

        soup = BeautifulSoup(self.driver.page_source, "lxml")
        title = soup.select_one(".manga-info-content h1").text.strip()
        safe_title = sanitize_name(title)

        api_url = f"https://www.mangakakalot.gg/api/manga/{manga_slug}/chapters?limit=50&offset=0"
        chapters = self._fetch_all_chapters(api_url, manga_slug)

        return safe_title, chapters

    def _fetch_all_chapters(self, initial_url, manga_slug):
        chapters = []
        offset = 0
        limit = 50
        has_more = True

        while has_more:
            url = f"https://www.mangakakalot.gg/api/manga/{manga_slug}/chapters?limit={limit}&offset={offset}"
            self.driver.get(url)
            json_data = self.driver.find_element(By.TAG_NAME, "pre").text
            res = json.loads(json_data)

            if res.get("success") and "data" in res:
                for item in res["data"].get("chapters", []):
                    chapters.append(
                        {
                            "title": sanitize_name(item.get("chapter_name")),
                            "url": f"https://www.mangakakalot.gg/manga/{manga_slug}/{item.get('chapter_slug')}",
                            "number": float(item.get("chapter_num", 0)),
                        }
                    )

                pagination = res["data"].get("pagination", {})
                has_more = pagination.get("has_more", False)
                offset += limit
            else:
                has_more = False

        chapters.sort(key=lambda x: x["number"])
        return chapters

    def download_chapters(self, manga_title, chapters):
        manga_path = self.base_dir / manga_title
        manga_path.mkdir(exist_ok=True)

        self.session.headers.update(
            {"User-Agent": self.driver.execute_script("return navigator.userAgent;")}
        )
        for c in self.driver.get_cookies():
            self.session.cookies.set(c["name"], c["value"])

        for chap in chapters:
            chap_path = manga_path / chap["title"]
            chap_path.mkdir(exist_ok=True)

            logging.info(f"Processing: {chap['title']}")
            self.driver.get(chap["url"])
            time.sleep(2)

            img_urls = self._extract_img_urls()
            images = self._download_images(img_urls, chap["url"])
            self._merge_and_save(images, chap_path)

    def _extract_img_urls(self):
        soup = BeautifulSoup(self.driver.page_source, "lxml")
        urls = []
        tags = soup.select(
            ".chapter-image-container img, .container-chapter-reader img, #vungdoc img"
        )
        for t in tags:
            src = t.get("data-src") or t.get("src")
            if src and "data:" not in src and "logo" not in src.lower():
                if src not in urls:
                    urls.append(src)
        return urls

    def _download_images(self, urls, referer):
        imgs = []
        for url in urls:
            self.session.headers.update({"Referer": "https://mangakakalot.com/"})
            res = self.session.get(url)
            if res.status_code == 403:
                self.session.headers.update({"Referer": referer})
                res = self.session.get(url)

            if res.status_code == 200:
                try:
                    imgs.append(Image.open(io.BytesIO(res.content)).convert("RGB"))
                except:
                    continue
        return imgs

    def _merge_and_save(self, imgs, path):
        final = []
        i = 0
        while i < len(imgs):
            curr = imgs[i]
            if i + 1 < len(imgs) and imgs[i + 1].size[1] < 250:
                nxt = imgs[i + 1]
                w, h = max(curr.size[0], nxt.size[0]), curr.size[1] + nxt.size[1]
                comb = Image.new("RGB", (w, h), (255, 255, 255))
                comb.paste(curr, (0, 0))
                comb.paste(nxt, (0, curr.size[1]))
                final.append(comb)
                i += 2
            else:
                final.append(curr)
                i += 1

        for idx, page in enumerate(final):
            page.save(path / f"{idx:03d}.jpg", "JPEG", quality=85)

    def run_kcc(self, manga_title):
        manga_path = self.base_dir / manga_title
        if not any(manga_path.iterdir()):
            return

        project_root = Path(__file__).parent.parent
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
            self.args.profile,
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

    def close(self):
        try:
            self.driver.close()
            self.driver.quit()
        except:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", required=True)
    parser.add_argument("-p", "--profile", default="KPW6")
    parser.add_argument("-cr", "--chapter_range", default=None)
    args = parser.parse_args()

    pipeline = MangaPipeline(args)
    try:
        title, chapters = pipeline.fetch_metadata()

        if args.chapter_range:
            start, end = map(float, args.chapter_range.split("-"))
            chapters = [c for c in chapters if start <= c["number"] <= end]

        pipeline.download_chapters(title, chapters)
        pipeline.run_kcc(title)
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()

import io
import time
import requests
import logging
# pyrefly: ignore [missing-import]
from PIL import Image
from pathlib import Path
from src.config import BASE_DIR

class ImageDownloader:
    def __init__(self, browser_manager):
        self.session = requests.Session()
        self.driver = browser_manager.driver
        
        # Base dir setup
        BASE_DIR.mkdir(exist_ok=True)

    def _sync_cookies_and_headers(self):
        self.session.headers.update(
            {"User-Agent": self.driver.execute_script("return navigator.userAgent;")}
        )
        for c in self.driver.get_cookies():
            self.session.cookies.set(c["name"], c["value"])

    def download_chapters(self, manga, scraper, chapter_range_filter=None):
        manga_path = BASE_DIR / manga.title
        manga_path.mkdir(exist_ok=True)

        self._sync_cookies_and_headers()

        chapters = manga.chapters
        if chapter_range_filter:
            chapters = [c for c in chapters if chapter_range_filter(c)]

        for chap in chapters:
            chap_path = manga_path / chap.title
            chap_path.mkdir(exist_ok=True)

            logging.info(f"Processing: {chap.title}")
            self.driver.get(chap.url)
            time.sleep(2)

            img_urls = scraper.extract_img_urls()
            images = self._download_images(img_urls, chap.url)
            self._merge_and_save(images, chap_path)

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

    def _merge_and_save(self, imgs, path: Path):
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

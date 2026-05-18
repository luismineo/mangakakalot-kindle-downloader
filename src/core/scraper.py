import json
import logging
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
# pyrefly: ignore [missing-import]
from selenium.webdriver.common.by import By
# pyrefly: ignore [missing-import]
from selenium.webdriver.support.ui import WebDriverWait
# pyrefly: ignore [missing-import]
from selenium.webdriver.support import expected_conditions as EC

from src.core.models import Manga, Chapter
from src.utils import sanitize_name

class MangakakalotScraper:
    def __init__(self, browser_manager):
        self.browser = browser_manager.driver

    def fetch_metadata(self, url: str) -> Manga:
        logging.info(f"Accessing: {url}")
        self.browser.get(url)

        manga_slug = url.rstrip("/").split("/")[-1]
        WebDriverWait(self.browser, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".manga-info-content h1"))
        )

        soup = BeautifulSoup(self.browser.page_source, "lxml")
        title = soup.select_one(".manga-info-content h1").text.strip()
        safe_title = sanitize_name(title)

        chapters = self._fetch_all_chapters(manga_slug)

        return Manga(title=safe_title, slug=manga_slug, chapters=chapters)

    def _fetch_all_chapters(self, manga_slug: str):
        chapters = []
        offset = 0
        limit = 50
        has_more = True

        while has_more:
            url = f"https://www.mangakakalot.gg/api/manga/{manga_slug}/chapters?limit={limit}&offset={offset}"
            self.browser.get(url)
            
            try:
                # Wait up to 15 seconds for <pre> tag (Cloudflare validation)
                pre_element = WebDriverWait(self.browser, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "pre"))
                )
                json_data = pre_element.text
                res = json.loads(json_data)
            except Exception as e:
                logging.error(f"Failed to load or read API JSON (Possible persistent Cloudflare block). URL: {url}")
                has_more = False
                break

            if res.get("success") and "data" in res:
                for item in res["data"].get("chapters", []):
                    chapters.append(
                        Chapter(
                            title=sanitize_name(item.get("chapter_name")),
                            url=f"https://www.mangakakalot.gg/manga/{manga_slug}/{item.get('chapter_slug')}",
                            number=float(item.get("chapter_num", 0)),
                        )
                    )

                pagination = res["data"].get("pagination", {})
                has_more = pagination.get("has_more", False)
                offset += limit
            else:
                has_more = False

        chapters.sort(key=lambda x: x.number)
        return chapters

    def extract_img_urls(self) -> list:
        soup = BeautifulSoup(self.browser.page_source, "lxml")
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

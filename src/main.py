import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from src.config import setup_logging
from src.core.browser import BrowserManager
from src.core.scraper import MangakakalotScraper
from src.core.downloader import ImageDownloader
from src.core.converter import KCCConverter

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", required=True)
    parser.add_argument("-p", "--profile", default="KPW6")
    parser.add_argument("-cr", "--chapter_range", default=None)
    args = parser.parse_args()

    browser = BrowserManager()
    try:
        scraper = MangakakalotScraper(browser)
        downloader = ImageDownloader(browser)
        converter = KCCConverter(profile=args.profile)
        
        manga = scraper.fetch_metadata(args.url)

        chapter_range_filter = None
        if args.chapter_range:
            start, end = map(float, args.chapter_range.split("-"))
            # Filter chapters based on their number
            manga.chapters = [c for c in manga.chapters if start <= c.number <= end]

        downloader.download_chapters(manga, scraper)
        converter.run(manga.title)
    finally:
        browser.close()

if __name__ == "__main__":
    main()

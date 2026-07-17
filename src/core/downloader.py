import io
import time
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Protocol

# pyrefly: ignore [missing-import]
from PIL import Image, UnidentifiedImageError
# pyrefly: ignore [missing-import]
from requests.adapters import HTTPAdapter

from src.config import BASE_DIR, DEFAULT_WORKERS
from src.core.models import Chapter, Manga
from src.core.progress import ProgressReporter

REFERER_FALLBACK = "https://mangakakalot.com/"
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 30

# Quantas fatias, no máximo, uma única página pode ter. O site observado usa 2;
# o limite generoso serve só para detectar que a remontagem se enganou.
MAX_SLICES_PER_PAGE = 5


class PageUrlSource(Protocol):
    """Capacidade mínima que o downloader exige de um scraper (Interface Segregation).

    Evita acoplar o downloader à implementação concreta do MangakakalotScraper.
    """

    def extract_img_urls(self) -> list[str]: ...


class ImageDownloader:
    """Baixa as páginas de um capítulo e as grava já processadas em disco.

    O navegador (bypass Cloudflare) é instância única e permanece serial: só ele
    navega até o capítulo. Os downloads em si saem por uma `requests.Session`
    que herda seus cookies.
    """

    def __init__(self, browser_manager, workers: int = DEFAULT_WORKERS) -> None:
        self.session = requests.Session()
        self.driver = browser_manager.driver
        self.workers = max(1, workers)

        # O pool de conexões precisa comportar todos os workers; caso contrário a
        # urllib3 descarta conexões e reabre sockets a cada página (mais lento e
        # mais suspeito para o anti-bot).
        adapter = HTTPAdapter(pool_connections=self.workers, pool_maxsize=self.workers)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        BASE_DIR.mkdir(parents=True, exist_ok=True)

    def prepare(self, manga: Manga) -> Path:
        """Cria a pasta do mangá e sincroniza cookies/headers do Selenium uma única vez."""
        manga_path = BASE_DIR / manga.title
        manga_path.mkdir(parents=True, exist_ok=True)
        self._sync_cookies_and_headers()
        return manga_path

    def download_chapter(
        self,
        manga: Manga,
        chapter: Chapter,
        scraper: PageUrlSource,
        reporter: ProgressReporter,
    ) -> int:
        """Baixa e processa um capítulo inteiro. Retorna o número de páginas salvas."""
        chap_path = BASE_DIR / manga.title / chapter.title
        chap_path.mkdir(parents=True, exist_ok=True)

        started = time.perf_counter()
        self.driver.get(chapter.url)
        # Sem sleep fixo: o scraper espera o leitor renderizar (WebDriverWait).
        img_urls = scraper.extract_img_urls()
        navigated = time.perf_counter()

        images = self._download_images(img_urls, chapter.url, reporter)
        fetched = time.perf_counter()

        pages = self._merge_and_save(images, chap_path)
        finished = time.perf_counter()

        logging.debug(
            f"{chapter.title}: nav={navigated - started:.1f}s "
            f"download={fetched - navigated:.1f}s ({len(images)} fatias) "
            f"merge+save={finished - fetched:.1f}s ({pages} páginas)"
        )
        return pages

    def _sync_cookies_and_headers(self) -> None:
        self.session.headers.update(
            {"User-Agent": self.driver.execute_script("return navigator.userAgent;")}
        )
        for c in self.driver.get_cookies():
            self.session.cookies.set(c["name"], c["value"])

    def _download_images(
        self, urls: list[str], referer: str, reporter: ProgressReporter
    ) -> list[Image.Image]:
        """Baixa as páginas em paralelo, devolvendo-as na ordem original do site.

        Só o I/O é paralelo — o navegador continua serial. As páginas concluem fora
        de ordem, por isso cada resultado carrega seu índice: a remontagem das
        fatias depende estritamente da sequência publicada pelo site.
        """
        total = len(urls)
        if not total:
            return []

        results: list[tuple[int, Image.Image | None]] = []
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = [
                pool.submit(self._fetch_one, index, url, referer)
                for index, url in enumerate(urls)
            ]
            for future in as_completed(futures):
                results.append(future.result())
                reporter.on_page_progress(len(results), total)

        results.sort(key=lambda pair: pair[0])
        return [img for _, img in results if img is not None]

    def _fetch_one(
        self, index: int, url: str, referer: str
    ) -> tuple[int, Image.Image | None]:
        """Baixa uma página com retry e backoff exponencial.

        Roda em várias threads: o Referer vai por chamada e nada muda o estado da
        sessão, que só é lido concorrentemente (cookies são sincronizados antes).
        """
        for attempt in range(MAX_RETRIES):
            try:
                res = self.session.get(
                    url,
                    headers={"Referer": REFERER_FALLBACK},
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                if res.status_code == 403:
                    res = self.session.get(
                        url, headers={"Referer": referer}, timeout=REQUEST_TIMEOUT_SECONDS
                    )

                if res.status_code == 429:
                    # Rate limit: recuar mais que num erro comum antes de insistir.
                    self._backoff(attempt, extra=1.0)
                    continue

                if res.status_code != 200:
                    logging.warning(f"HTTP {res.status_code} for {url}")
                    return index, None

                return index, Image.open(io.BytesIO(res.content)).convert("RGB")

            except requests.RequestException as exc:
                if attempt == MAX_RETRIES - 1:
                    logging.warning(f"Network error on {url} after {MAX_RETRIES} tries: {exc}")
                    return index, None
                self._backoff(attempt)
            except (UnidentifiedImageError, OSError) as exc:
                logging.warning(f"Corrupt or unreadable image at {url}: {exc}")
                return index, None

        logging.warning(f"Giving up on {url} after {MAX_RETRIES} tries (rate limited).")
        return index, None

    @staticmethod
    def _backoff(attempt: int, extra: float = 0.0) -> None:
        time.sleep(BACKOFF_BASE_SECONDS * (2**attempt) + extra)

    def _merge_and_save(self, imgs: list[Image.Image], path: Path) -> int:
        """Remonta as fatias do site em páginas inteiras e grava como JPEG numerado."""
        pages = self._reassemble(imgs)
        for idx, page in enumerate(pages):
            page.save(path / f"{idx:03d}.jpg", "JPEG", quality=85)
        return len(pages)

    @staticmethod
    def _reassemble(imgs: list[Image.Image]) -> list[Image.Image]:
        """Reagrupa as fatias verticais do site em páginas completas.

        O site corta cada página numa altura fixa (ex.: 1500px) e emite o restante
        como uma fatia seguinte, mais curta. Logo: uma fatia com a altura cheia
        significa "continua"; a primeira fatia mais curta fecha a página.

        Isto substitui o antigo limiar fixo `altura < 250`, que nunca disparava em
        tiras de 500px. Um limiar fixo é insuficiente por natureza: os restos
        observados variam de 500px a 1492px, praticamente colando na fatia cheia
        de 1500px — não há constante capaz de separá-los de uma página nova.
        """
        if not imgs:
            return []

        heights = [im.size[1] for im in imgs]
        slice_height = max(heights)

        # Só há fatiamento se a altura cheia se repete E existe alguma fatia menor.
        if not (heights.count(slice_height) > 1 and any(h < slice_height for h in heights)):
            return list(imgs)

        groups: list[list[Image.Image]] = []
        group: list[Image.Image] = []
        for img in imgs:
            group.append(img)
            if img.size[1] < slice_height:
                groups.append(group)
                group = []
        if group:
            groups.append(group)

        # Uma página real é cortada em poucas fatias (o site usa 2). Um grupo enorme
        # significa que confundimos páginas inteiras de altura uniforme com fatias —
        # abortar, senão o capítulo inteiro viraria uma única imagem gigante. Isto
        # também torna a remontagem idempotente: reprocessar páginas já unidas não
        # as empilha de novo.
        if any(len(g) > MAX_SLICES_PER_PAGE for g in groups):
            logging.debug("Uniform page heights detected; skipping slice reassembly.")
            return list(imgs)

        return [ImageDownloader._stack(g) for g in groups]

    @staticmethod
    def _stack(group: list[Image.Image]) -> Image.Image:
        """Empilha verticalmente as fatias de uma mesma página."""
        if len(group) == 1:
            return group[0]

        width = max(im.size[0] for im in group)
        canvas = Image.new("RGB", (width, sum(im.size[1] for im in group)), (255, 255, 255))
        offset = 0
        for img in group:
            canvas.paste(img, (0, offset))
            offset += img.size[1]
        return canvas

"""Orquestração do fluxo completo: scraping -> download -> conversão.

Ponto de entrada único usado tanto pela CLI (`src/main.py`) quanto, futuramente,
pela GUI PySide6. Toda a fiação de colaboradores vive aqui, não na camada de UI.
"""

import threading
from dataclasses import dataclass

# pyrefly: ignore [missing-import]
import requests
# pyrefly: ignore [missing-import]
from selenium.common.exceptions import WebDriverException

from src.config import DEFAULT_WORKERS
from src.core.browser import BrowserManager
from src.core.converter import KCCConverter
from src.core.downloader import ImageDownloader
from src.core.models import Chapter, Manga
from src.core.progress import LoggingReporter, ProgressReporter
from src.core.scraper import MangakakalotScraper
from src.core.state import StateManager

# Falhas esperadas de um capítulo: rede, navegador ou disco. Um capítulo ruim é
# registrado e pulado; erros inesperados continuam subindo (são bugs, não ruído).
CHAPTER_ERRORS = (requests.RequestException, WebDriverException, OSError)


def parse_chapter_range(raw: str) -> tuple[float, float]:
    """Converte "1-10" ou "15.5" em (início, fim) inclusivos.

    Raises:
        ValueError: se o formato for inválido.
    """
    error = ValueError(f"Invalid chapter range '{raw}'. Use e.g. '1-10' or '15.5'.")
    parts = [p.strip() for p in raw.split("-") if p.strip()]
    try:
        if len(parts) == 1:
            single = float(parts[0])
            return single, single
        if len(parts) == 2:
            return float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise error from exc
    raise error


@dataclass
class PipelineConfig:
    """Parâmetros de uma execução, independentes da origem (CLI ou GUI)."""

    url: str
    profile: str = "KPW6"
    chapter_range: str | None = None
    workers: int = DEFAULT_WORKERS
    output_format: str = "MOBI"

    def __post_init__(self) -> None:
        # Valida já na construção: subir o Chrome e passar pelo Cloudflare leva
        # ~15s, e é desperdício descobrir só depois que a faixa era inválida.
        if self.chapter_range:
            parse_chapter_range(self.chapter_range)


class MangaPipeline:
    """Coordena scraper, downloader e converter para uma execução completa.

    Os colaboradores são injetados (Dependency Inversion) para permitir testes
    com dublês; use `MangaPipeline.create()` para a montagem padrão.
    """

    def __init__(
        self,
        config: PipelineConfig,
        scraper: MangakakalotScraper,
        downloader: ImageDownloader,
        converter: KCCConverter,
        reporter: ProgressReporter | None = None,
        state: StateManager | None = None,
    ) -> None:
        self.config = config
        self.scraper = scraper
        self.downloader = downloader
        self.converter = converter
        self.reporter: ProgressReporter = reporter or LoggingReporter()
        self.state = state or StateManager()
        self._cancel = threading.Event()

    @classmethod
    def create(
        cls,
        config: PipelineConfig,
        browser: BrowserManager,
        reporter: ProgressReporter | None = None,
    ) -> "MangaPipeline":
        """Monta o pipeline com os colaboradores concretos padrão."""
        return cls(
            config=config,
            scraper=MangakakalotScraper(browser),
            downloader=ImageDownloader(browser, workers=config.workers),
            converter=KCCConverter(profile=config.profile, output_format=config.output_format),
            reporter=reporter,
            state=StateManager(),
        )

    def cancel(self) -> None:
        """Solicita o cancelamento cooperativo (checado entre capítulos)."""
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> Manga:
        """Executa o fluxo completo e retorna o mangá com os capítulos selecionados.

        Raises:
            ValueError: se `config.chapter_range` estiver malformado.
        """
        manga = self.scraper.fetch_metadata(self.config.url)
        manga.chapters = self._select_chapters(manga.chapters)
        self.reporter.on_manga_ready(manga.title, len(manga.chapters))

        if not manga.chapters:
            self.reporter.on_log("warning", "No chapters matched the requested range.")
            return manga

        failed = self._download_all(manga)

        if self.cancelled:
            self.reporter.on_log("warning", "Cancelled before conversion.")
            return manga

        if failed:
            self.reporter.on_log(
                "warning",
                f"{failed} of {len(manga.chapters)} chapter(s) failed and will be "
                "retried on the next run.",
            )

        if self.state.completed_count() == 0:
            self.reporter.on_log("error", "No chapter completed; skipping conversion.")
            return manga

        self.reporter.on_stage("converting")
        if not self.converter.run(manga.title, self.reporter):
            self.reporter.on_log("error", "KCC conversion failed; images kept on disk.")
        return manga

    def _download_all(self, manga: Manga) -> int:
        """Baixa os capítulos pendentes. Retorna quantos falharam."""
        self.reporter.on_stage("downloading")
        self.downloader.prepare(manga)
        self.state.load(manga, self.config.url)

        failed = 0
        total = len(manga.chapters)
        for index, chapter in enumerate(manga.chapters, start=1):
            if self.cancelled:
                self.reporter.on_log("warning", "Cancelled by user.")
                return failed

            if self.state.is_completed(chapter):
                self.reporter.on_chapter_done(chapter.title, skipped=True)
                continue

            self.reporter.on_chapter_start(chapter.title, index, total)
            self.state.mark_downloading(chapter)
            try:
                pages = self.downloader.download_chapter(
                    manga, chapter, self.scraper, self.reporter
                )
            except CHAPTER_ERRORS as exc:
                failed += 1
                self.state.mark_failed(chapter)
                self.reporter.on_log("error", f"Chapter '{chapter.title}' failed: {exc}")
                continue

            self.state.mark_completed(chapter, pages)
            self.reporter.on_chapter_done(chapter.title)

        return failed

    def _select_chapters(self, chapters: list[Chapter]) -> list[Chapter]:
        if not self.config.chapter_range:
            return chapters
        start, end = parse_chapter_range(self.config.chapter_range)
        return [c for c in chapters if start <= c.number <= end]

"""Execução do pipeline fora da thread de UI, com progresso via sinais Qt."""

import logging

# pyrefly: ignore [missing-import]
from PySide6.QtCore import QObject, Signal

from src.core.browser import BrowserManager
from src.core.pipeline import MangaPipeline, PipelineConfig


class QtReporter(QObject):
    """Adapta o `ProgressReporter` do núcleo para sinais Qt.

    É esta classe que mantém o núcleo livre de Qt: ela implementa o Protocol e
    reemite tudo como sinal. Emitir de outra thread é seguro — o Qt enfileira a
    entrega na thread do receptor.
    """

    manga_ready = Signal(str, int)
    chapter_started = Signal(str, int, int)
    page_progress = Signal(int, int)
    chapter_done = Signal(str, bool)
    convert_progress = Signal(int, int, str)
    stage_changed = Signal(str)
    message = Signal(str, str)

    def on_manga_ready(self, title: str, total_chapters: int) -> None:
        self.manga_ready.emit(title, total_chapters)

    def on_chapter_start(self, title: str, index: int, total: int) -> None:
        self.chapter_started.emit(title, index, total)

    def on_page_progress(self, done: int, total: int) -> None:
        self.page_progress.emit(done, total)

    def on_chapter_done(self, title: str, skipped: bool = False) -> None:
        self.chapter_done.emit(title, skipped)

    def on_convert_progress(self, step: int, total: int, label: str) -> None:
        self.convert_progress.emit(step, total, label)

    def on_stage(self, stage: str) -> None:
        self.stage_changed.emit(stage)

    def on_log(self, level: str, message: str) -> None:
        self.message.emit(level, message)


class PipelineWorker(QObject):
    """Roda um `MangaPipeline` completo numa QThread."""

    finished = Signal(bool, str)

    def __init__(self, config: PipelineConfig, reporter: QtReporter) -> None:
        super().__init__()
        self.config = config
        self.reporter = reporter
        self._pipeline: MangaPipeline | None = None

    def run(self) -> None:
        browser = None
        try:
            self.reporter.on_log("info", "Starting browser (Cloudflare bypass)...")
            browser = BrowserManager()
            self._pipeline = MangaPipeline.create(self.config, browser, self.reporter)
            self._pipeline.run()

            if self._pipeline.cancelled:
                self.finished.emit(False, "Cancelled. Progress was saved.")
            else:
                self.finished.emit(True, "Done.")

        # Fronteira de thread: uma exceção não capturada aqui morreria em silêncio
        # e a interface ficaria travada "em progresso" para sempre.
        except Exception as exc:  # noqa: BLE001
            logging.exception("Pipeline failed")
            self.finished.emit(False, str(exc))
        finally:
            if browser is not None:
                browser.close()

    def cancel(self) -> None:
        """Cancelamento cooperativo: o capítulo em curso termina, e para aí."""
        if self._pipeline is not None:
            self._pipeline.cancel()

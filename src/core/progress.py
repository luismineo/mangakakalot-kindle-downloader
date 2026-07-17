"""Canal de reporte de progresso desacoplado da interface (CLI ou GUI)."""

import logging
from typing import Protocol

_LEVELS: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


class ProgressReporter(Protocol):
    """Interface de progresso consumida pelo pipeline.

    O núcleo depende apenas deste Protocol (Dependency Inversion): a CLI usa
    `LoggingReporter` e a GUI usará um QObject que reemite os callbacks como
    sinais Qt. Nenhum módulo de `core` deve importar Qt.
    """

    def on_manga_ready(self, title: str, total_chapters: int) -> None:
        """Metadados resolvidos. `total_chapters` já reflete o filtro de range."""
        ...

    def on_chapter_start(self, title: str, index: int, total: int) -> None:
        """Início de um capítulo. `index` é 1-based."""
        ...

    def on_page_progress(self, done: int, total: int) -> None:
        """Páginas concluídas dentro do capítulo corrente."""
        ...

    def on_chapter_done(self, title: str, skipped: bool = False) -> None:
        """Capítulo finalizado. `skipped=True` quando reaproveitado do checkpoint."""
        ...

    def on_convert_progress(self, step: int, total: int, label: str) -> None:
        """Etapa da conversão do KCC (a fase mais longa de uma execução)."""
        ...

    def on_stage(self, stage: str) -> None:
        """Mudança de etapa macro do pipeline (ex.: "downloading", "converting")."""
        ...

    def on_log(self, level: str, message: str) -> None:
        """Mensagem livre destinada ao usuário."""
        ...


class LoggingReporter:
    """Implementação para a CLI: encaminha os eventos para o `logging` estruturado."""

    def on_manga_ready(self, title: str, total_chapters: int) -> None:
        logging.info(f"Manga: {title} | {total_chapters} chapter(s) selected")

    def on_chapter_start(self, title: str, index: int, total: int) -> None:
        logging.info(f"[{index}/{total}] Processing: {title}")

    def on_page_progress(self, done: int, total: int) -> None:
        logging.debug(f"Pages: {done}/{total}")

    def on_chapter_done(self, title: str, skipped: bool = False) -> None:
        if skipped:
            logging.info(f"Skipping (already completed): {title}")
        else:
            logging.info(f"Finished: {title}")

    def on_convert_progress(self, step: int, total: int, label: str) -> None:
        logging.info(f"KCC [{step}/{total}] {label}")

    def on_stage(self, stage: str) -> None:
        logging.info(f"Stage: {stage}")

    def on_log(self, level: str, message: str) -> None:
        logging.log(_LEVELS.get(level.lower(), logging.INFO), message)


class NullReporter:
    """No-op. Útil em testes e quando o progresso não interessa."""

    def on_manga_ready(self, title: str, total_chapters: int) -> None: ...

    def on_chapter_start(self, title: str, index: int, total: int) -> None: ...

    def on_page_progress(self, done: int, total: int) -> None: ...

    def on_chapter_done(self, title: str, skipped: bool = False) -> None: ...

    def on_convert_progress(self, step: int, total: int, label: str) -> None: ...

    def on_stage(self, stage: str) -> None: ...

    def on_log(self, level: str, message: str) -> None: ...

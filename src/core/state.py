"""Persistência do progresso de download (checkpoint) por mangá.

Grava `downloads/<manga_title>/state.json` para que uma execução interrompida
(erro de rede, Ctrl+C, queda de energia) possa ser retomada exatamente de onde
parou, pulando os capítulos já concluídos.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from src.config import BASE_DIR
from src.core.models import Chapter, Manga

ChapterStatus = Literal["pending", "downloading", "completed", "failed"]

PENDING: ChapterStatus = "pending"
DOWNLOADING: ChapterStatus = "downloading"
COMPLETED: ChapterStatus = "completed"
FAILED: ChapterStatus = "failed"

STATE_FILENAME = "state.json"


class StateManager:
    """Lê e grava o checkpoint de um mangá.

    A unidade de checkpoint é o **capítulo**: ele só vira `completed` depois que
    todas as páginas foram baixadas, unidas e gravadas em disco. Qualquer estado
    diferente de `completed` é re-baixado na execução seguinte (idempotente, os
    arquivos `NNN.jpg` são sobrescritos).
    """

    def __init__(self, base_dir: Path = BASE_DIR) -> None:
        self._base_dir = base_dir
        self._path: Path | None = None
        self._data: dict = {}

    @property
    def path(self) -> Path | None:
        """Caminho do state.json corrente (None antes do `load`)."""
        return self._path

    def load(self, manga: Manga, url: str) -> None:
        """Carrega (ou inicializa) o checkpoint e semeia os capítulos selecionados.

        `manga.chapters` já deve estar filtrado pelo range: só os capítulos desta
        execução são semeados, e entradas de execuções anteriores são preservadas.
        """
        self._path = self._base_dir / manga.title / STATE_FILENAME
        self._data = self._read() or {}

        self._data["manga_title"] = manga.title
        self._data["url"] = url
        chapters = self._data.setdefault("chapters", {})

        for chapter in manga.chapters:
            chapters.setdefault(chapter.title, {"status": PENDING, "pages_downloaded": 0})

        self._save()

    def is_completed(self, chapter: Chapter) -> bool:
        entry = self._data.get("chapters", {}).get(chapter.title)
        return isinstance(entry, dict) and entry.get("status") == COMPLETED

    def mark_downloading(self, chapter: Chapter) -> None:
        self._set(chapter, DOWNLOADING, 0)

    def mark_completed(self, chapter: Chapter, pages: int) -> None:
        self._set(chapter, COMPLETED, pages)

    def mark_failed(self, chapter: Chapter) -> None:
        self._set(chapter, FAILED, 0)

    def completed_count(self) -> int:
        return sum(
            1
            for entry in self._data.get("chapters", {}).values()
            if isinstance(entry, dict) and entry.get("status") == COMPLETED
        )

    def _set(self, chapter: Chapter, status: ChapterStatus, pages: int) -> None:
        self._data.setdefault("chapters", {})[chapter.title] = {
            "status": status,
            "pages_downloaded": pages,
        }
        self._save()

    def _read(self) -> dict | None:
        """Lê o state.json existente. Um arquivo corrompido é descartado, não fatal."""
        if self._path is None or not self._path.exists():
            return None
        try:
            with self._path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            logging.warning(f"Unreadable checkpoint at {self._path}, starting fresh: {exc}")
            return None

        if not isinstance(data, dict) or not isinstance(data.get("chapters"), dict):
            logging.warning(f"Malformed checkpoint at {self._path}, starting fresh.")
            return None
        return data

    def _save(self) -> None:
        """Grava o checkpoint atomicamente (tmp + os.replace).

        `os.replace` é atômico dentro do mesmo volume, então o state.json nunca
        é observado pela metade — mesmo que o processo morra durante a escrita.
        """
        if self._path is None:
            return

        self._data["last_updated"] = datetime.now().isoformat(timespec="seconds")
        tmp = self._path.with_name(self._path.name + ".tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self._path)
        except OSError as exc:
            logging.error(f"Could not persist checkpoint to {self._path}: {exc}")
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                logging.debug(f"Leftover temp checkpoint could not be removed: {tmp}")

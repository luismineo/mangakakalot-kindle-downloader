"""Janela principal da aplicação."""

from html import escape

# pyrefly: ignore [missing-import]
from PySide6.QtCore import Qt, QThread, QUrl
# pyrefly: ignore [missing-import]
from PySide6.QtGui import QDesktopServices, QPalette
# pyrefly: ignore [missing-import]
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.config import BASE_DIR, DEFAULT_WORKERS
from src.core.pipeline import PipelineConfig
from src.gui.profiles import DEFAULT_PROFILE, kindle_profiles
from src.gui.worker import PipelineWorker, QtReporter

# Duas paletas de log: as cores precisam ter contraste tanto no tema claro quanto
# no escuro. Tons fixos pensados para fundo claro somem por completo no escuro.
_LEVEL_COLORS_LIGHT = {"error": "#c0392b", "warning": "#9c6600", "info": "#2c3e50", "muted": "#5f6b7a"}
_LEVEL_COLORS_DARK = {"error": "#ff6b6b", "warning": "#ffa94d", "info": "#e6e9ed", "muted": "#a8b3c0"}

# A barra é dividida entre as duas fases. A conversão fica com uma fatia grande
# de propósito: ela costuma dominar o tempo real, ainda mais quando o checkpoint
# já pulou os downloads.
DOWNLOAD_SHARE = 70
CONVERT_SHARE = 100 - DOWNLOAD_SHARE

STYLESHEET = """
QWidget {{ font-size: 13px; }}
QLabel#heading {{ font-size: 18px; font-weight: 600; }}
QLabel#subheading {{ color: {muted}; }}
QPlainTextEdit {{
    font-family: Consolas, monospace;
    font-size: 12px;
    border: 1px solid palette(mid);
    border-radius: 4px;
}}
QPushButton {{ padding: 7px 18px; border-radius: 4px; }}
QPushButton#start {{ font-weight: 600; }}
QProgressBar {{ height: 20px; border-radius: 4px; text-align: center; }}
"""


class MainWindow(QWidget):
    """Formulário simples: URL, dispositivo, capítulos -> progresso e log."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mangakakalot Kindle Downloader")
        self.setMinimumSize(640, 560)

        self._colors = self._resolve_colors()
        self.setStyleSheet(STYLESHEET.format(muted=self._colors["muted"]))

        self._thread: QThread | None = None
        self._worker: PipelineWorker | None = None
        self._total_chapters = 0
        self._chapter_index = 0
        self._chapter_title = ""

        self._build_ui()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        heading = QLabel("Mangakakalot Kindle Downloader")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        subheading = QLabel("Baixa os capítulos e converte para o seu Kindle.")
        subheading.setObjectName("subheading")
        layout.addWidget(subheading)

        layout.addWidget(self._separator())

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.mangakakalot.gg/manga/nome-do-manga")
        self.url_input.textChanged.connect(self._refresh_start_state)
        form.addRow("URL do mangá", self.url_input)

        self.profile_input = QComboBox()
        for code, label in kindle_profiles():
            self.profile_input.addItem(f"{label}  ({code})", userData=code)
        self._select_default_profile()
        form.addRow("Dispositivo", self.profile_input)

        self.chapters_input = QLineEdit()
        self.chapters_input.setPlaceholderText("ex.: 1-10 ou 15.5   |   vazio = todos")
        form.addRow("Capítulos", self.chapters_input)

        self.workers_input = QSpinBox()
        self.workers_input.setRange(1, 8)
        self.workers_input.setValue(DEFAULT_WORKERS)
        self.workers_input.setToolTip(
            "Downloads simultâneos. Acima de 8, o site tende a responder 429."
        )
        form.addRow("Downloads simultâneos", self.workers_input)

        self.open_folder_input = QCheckBox("Abrir a pasta ao concluir")
        self.open_folder_input.setChecked(True)
        form.addRow("", self.open_folder_input)

        layout.addLayout(form)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status = QLabel("Pronto.")
        self.status.setObjectName("subheading")
        layout.addWidget(self.status)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        layout.addWidget(self.log, stretch=1)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel)
        buttons.addWidget(self.cancel_button)

        self.start_button = QPushButton("Baixar")
        self.start_button.setObjectName("start")
        self.start_button.setDefault(True)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._on_start)
        buttons.addWidget(self.start_button)

        layout.addLayout(buttons)

    def _resolve_colors(self) -> dict[str, str]:
        """Escolhe a paleta de log conforme o tema em uso pelo sistema."""
        window = self.palette().color(QPalette.ColorRole.Window)
        is_dark = window.lightness() < 128
        return _LEVEL_COLORS_DARK if is_dark else _LEVEL_COLORS_LIGHT

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def _select_default_profile(self) -> None:
        index = self.profile_input.findData(DEFAULT_PROFILE)
        if index >= 0:
            self.profile_input.setCurrentIndex(index)

    # --------------------------------------------------------------- ações --
    def _refresh_start_state(self) -> None:
        running = self._thread is not None
        self.start_button.setEnabled(not running and bool(self.url_input.text().strip()))

    def _on_start(self) -> None:
        try:
            config = PipelineConfig(
                url=self.url_input.text().strip(),
                profile=self.profile_input.currentData(),
                chapter_range=self.chapters_input.text().strip() or None,
                workers=self.workers_input.value(),
            )
        except ValueError as exc:
            # Validado antes de subir o navegador (~15s), não depois.
            self._append("error", str(exc))
            return

        self.log.clear()
        self._set_running(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        reporter = QtReporter()
        reporter.manga_ready.connect(self._on_manga_ready)
        reporter.chapter_started.connect(self._on_chapter_started)
        reporter.page_progress.connect(self._on_page_progress)
        reporter.chapter_done.connect(self._on_chapter_done)
        reporter.convert_progress.connect(self._on_convert_progress)
        reporter.stage_changed.connect(self._on_stage)
        reporter.message.connect(self._append)

        self._thread = QThread(self)
        self._worker = PipelineWorker(config, reporter)
        reporter.setParent(self._worker)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

    def _on_cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status.setText("Cancelando após o capítulo atual...")

    def _set_running(self, running: bool) -> None:
        for widget in (
            self.url_input,
            self.profile_input,
            self.chapters_input,
            self.workers_input,
        ):
            widget.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self._refresh_start_state()

    # ---------------------------------------------------------- callbacks ---
    def _on_manga_ready(self, title: str, total: int) -> None:
        self._total_chapters = total
        self._chapter_index = 0
        self._append("info", f"{title} — {total} capítulo(s)")

    def _on_chapter_started(self, title: str, index: int, total: int) -> None:
        self._chapter_index = index
        self._chapter_title = f"{title}  ({index}/{total})"
        self.status.setText(f"Baixando {self._chapter_title}")

    def _on_page_progress(self, done: int, total: int) -> None:
        if not self._total_chapters or not total:
            return
        # Progresso global: capítulos concluídos + fração do capítulo atual.
        chapter_fraction = done / total
        overall = (self._chapter_index - 1 + chapter_fraction) / self._total_chapters
        self.progress.setValue(int(overall * DOWNLOAD_SHARE))
        self.status.setText(f"{self._chapter_title}  —  página {done}/{total}")

    def _on_chapter_done(self, title: str, skipped: bool) -> None:
        if skipped:
            self._chapter_index += 1
            self._append("info", f"{title}: já baixado, pulando.")
        else:
            self._append("info", f"{title}: concluído.")
        if self._total_chapters:
            done = self._chapter_index / self._total_chapters
            self.progress.setValue(int(done * DOWNLOAD_SHARE))

    def _on_convert_progress(self, step: int, total: int, label: str) -> None:
        # A conversão ocupa a faixa final da barra. Sem isto ela ficava parada num
        # "loading" indeterminado justamente na etapa mais demorada.
        fraction = step / total if total else 0
        self.progress.setValue(DOWNLOAD_SHARE + int(fraction * CONVERT_SHARE))
        self.status.setText(f"Convertendo: {label}")

    def _on_stage(self, stage: str) -> None:
        if stage == "converting":
            self.status.setText("Convertendo com o KCC...")
            self.progress.setValue(DOWNLOAD_SHARE)
        elif stage == "downloading":
            self.status.setText("Baixando...")

    def _open_downloads_folder(self) -> None:
        """Abre a pasta de downloads no gerenciador de arquivos do sistema."""
        if not BASE_DIR.exists():
            return
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(BASE_DIR)))
        except OSError as exc:
            self._append("warning", f"Não foi possível abrir a pasta: {exc}")

    def _append(self, level: str, message: str) -> None:
        color = self._colors.get(level, self._colors["info"])
        self.log.appendHtml(f'<span style="color:{color};">{escape(message)}</span>')

    def _on_finished(self, success: bool, message: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if success else self.progress.value())

        if success:
            self.status.setText(f"Concluído. Arquivos em: {BASE_DIR}")
            self._append("info", message)
            if self.open_folder_input.isChecked():
                self._open_downloads_folder()
        else:
            self.status.setText(message)
            self._append("error", message)
            self._append("info", "O progresso foi salvo: rodar de novo continua de onde parou.")

        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self._set_running(False)

    def closeEvent(self, event) -> None:
        """Fecha sem deixar o navegador nem a thread órfãos."""
        if self._worker is not None:
            self._worker.cancel()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(30000)
        event.accept()

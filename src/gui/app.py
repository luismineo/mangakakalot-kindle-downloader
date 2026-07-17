"""Bootstrap da aplicação Qt.

Não é o entry point do executável: o processo entra sempre por `src/main.py`,
que trata o `freeze_support()` e a reentrada como worker do KCC antes de chegar
aqui. Um único entry point também é o que o PyInstaller espera.
"""

import logging
import sys

# pyrefly: ignore [missing-import]
from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow

_SW_HIDE = 0


def _hide_own_console() -> None:
    """Esconde a janela de console, mas só se ela for nossa.

    O executável é console=True de propósito: a CLI precisa de stdout, e o modo
    `--kcc-worker` também. Ao abrir por duplo-clique, o Windows cria um console
    só para nós, que ficaria feio atrás da interface.

    A checagem do `GetConsoleProcessList` é o que torna isto seguro: se houver
    mais de um processo ligado ao console, ele é o terminal de quem nos chamou —
    escondê-lo faria a janela do usuário sumir.
    """
    if not sys.platform.startswith("win"):
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        processes = (ctypes.c_uint * 2)()
        attached = kernel32.GetConsoleProcessList(processes, 2)

        if attached != 1:
            return  # herdamos o console de um terminal: não mexer

        console = kernel32.GetConsoleWindow()
        if console:
            ctypes.windll.user32.ShowWindow(console, _SW_HIDE)
    except (OSError, AttributeError) as exc:
        logging.debug(f"Could not hide the console window: {exc}")


def launch() -> int:
    """Abre a janela e roda o loop de eventos até o usuário fechar."""
    _hide_own_console()

    app = QApplication(sys.argv)
    app.setApplicationName("Mangakakalot Kindle Downloader")
    app.setOrganizationName("Mangakakalot Kindle Downloader")

    window = MainWindow()
    window.show()
    return app.exec()

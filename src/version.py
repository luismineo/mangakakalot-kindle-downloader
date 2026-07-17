"""Fonte única de verdade para a versão da aplicação.

VERSION e CHANNEL são reescritos pelo release.ps1 antes de cada build; não
editar manualmente fora desse fluxo.
"""

APP_NAME = "Mangakakalot Kindle Downloader"
VERSION = "0.0.1"
CHANNEL = "dev"


def display_version() -> str:
    """Ex.: '0.1.0-pre', '1.0.0-stable'."""
    return f"{VERSION}-{CHANNEL}"

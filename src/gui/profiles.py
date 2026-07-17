"""Lista de perfis de dispositivo, lida do próprio KCC.

Ler do KCC evita duplicar a tabela: quando o vendor for atualizado, os aparelhos
novos aparecem sozinhos no dropdown.
"""

import logging
import sys

from src.core.converter import vendor_kcc_dir

DEFAULT_PROFILE = "KPW6"

# Usado apenas se a importação do KCC falhar, para a GUI ainda abrir.
_FALLBACK: list[tuple[str, str]] = [
    ("KPW6", "Kindle Paperwhite 6"),
    ("KPW5", "Kindle Paperwhite 5/Signature Edition"),
    ("K11", "Kindle 11"),
    ("KO", "Kindle Oasis 2/3"),
    ("KS", "Kindle Scribe 1/2"),
    ("KCS", "Kindle Colorsoft"),
]


def kindle_profiles() -> list[tuple[str, str]]:
    """Perfis Kindle como (código, nome amigável), ex.: ("KPW6", "Kindle Paperwhite 6").

    Só os Kindle: o formato padrão é MOBI, que o KCC não gera para Kobo/reMarkable.
    """
    try:
        vendor = str(vendor_kcc_dir())
        if vendor not in sys.path:
            sys.path.insert(0, vendor)

        # pyrefly: ignore [missing-import]
        from kindlecomicconverter.image import ProfileData

        profiles = [(code, data[0]) for code, data in ProfileData.ProfilesKindle.items()]
        if profiles:
            return profiles
        logging.warning("KCC reported no Kindle profiles; using the built-in list.")
    except ImportError as exc:
        logging.warning(f"Could not read profiles from KCC ({exc}); using the built-in list.")

    return list(_FALLBACK)

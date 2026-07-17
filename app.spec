# -*- mode: python ; coding: utf-8 -*-
"""Build do Mangakakalot Kindle Downloader (PyInstaller, --onedir).

Por que --onedir e nao --onefile:
    O onefile extrai tudo para uma pasta temporaria a cada execucao. O
    undetected_chromedriver sobe o Chrome com use_subprocess=True e patcheia o
    chromedriver em disco, o que nao sobrevive bem a essa extracao. O onedir
    tambem inicia mais rapido e e mais facil de diagnosticar.

O que NAO e empacotado (precisa existir na maquina do usuario):
    - Google Chrome: o undetected_chromedriver baixa e patcheia, em runtime, o
      chromedriver compativel com o Chrome instalado. Nao ha o que embutir.
    - 7-Zip e Kindle Previewer 3: o KCC os invoca como executaveis externos.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

PROJECT_ROOT = Path(SPECPATH)
VENDOR_KCC = PROJECT_ROOT / "src" / "vendor" / "kcc"

# O undetected_chromedriver carrega recursos proprios; collect_all traz modulos,
# binarios e dados de uma vez.
uc_datas, uc_binaries, uc_hiddenimports = collect_all("undetected_chromedriver")

# O KCC e vendorizado (nao instalado), entao o PyInstaller so o enxerga com o
# vendor no pathex. Os submodulos entram explicitamente porque comic2ebook os
# importa de forma relativa (`from . import image`), o que a analise estatica
# resolve, mas o KCC_gui e carregado tardiamente dentro de uma funcao.
kcc_hiddenimports = collect_submodules("kindlecomicconverter")

hidden = [
    *uc_hiddenimports,
    *kcc_hiddenimports,
    "kcc",              # kcc.py: fornece o modify_path() usado pelo worker
    "_cffi_backend",    # exigido pelo mozjpeg; vem do proprio .spec do KCC
]

a = Analysis(
    ["src/main.py"],
    pathex=[str(PROJECT_ROOT), str(VENDOR_KCC)],
    binaries=uc_binaries,
    datas=uc_datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pkg_resources", "tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

# 'u' = modo unbuffered do Python, embutido no binario.
#
# Necessario porque o executavel reinvoca a si mesmo como worker do KCC, e o pai
# le esse stdout para mover a barra de progresso. Rodando do fonte basta a variavel
# PYTHONUNBUFFERED, mas o app congelado tem o interpretador embutido e a ignora:
# sem esta opcao, o KCC bufferiza as ~9 etapas e todas chegam juntas no fim, com a
# barra saltando direto para 100%.
python_options = [("u", None, "OPTION")]

exe = EXE(
    pyz,
    a.scripts,
    python_options,
    exclude_binaries=True,
    name="MangakakalotDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # console=True: a CLI continua sendo um modo de uso de primeira classe, e o
    # worker do KCC (--kcc-worker) precisa de stdout para reportar erro.
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MangakakalotDownloader",
)

"""Ponte para o Kindle Comic Converter (KCC).

O KCC roda sempre em **processo separado**, de propósito: ele chama `os.chdir()`,
`sys.exit()` e usa `multiprocessing`, além de manter estado global (`options`).
Um subprocess contém tudo isso — rodá-lo dentro do nosso processo poluiria o CWD
da aplicação e, na GUI, arrastaria Qt para os workers do multiprocessing.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

from src.config import BASE_DIR
from src.core.progress import NullReporter, ProgressReporter

# Sentinela de reentrada: num app congelado, `sys.executable` é o nosso .exe e não
# um interpretador Python, então não há como chamar `python kcc-c2e.py`. O .exe
# reinvoca a si mesmo com esta flag e age como o KCC — mantendo o isolamento.
KCC_WORKER_FLAG = "--kcc-worker"

# O KCC imprime estes marcadores ao longo da conversão. Como ele roda isolado num
# subprocess, o stdout é a única via de progresso disponível — e a conversão é a
# fase mais longa de uma execução.
#
# A ordem abaixo é a OBSERVADA numa conversão real, não a suposta: o KCC emite
# "Creating EPUB file" antes de buildHTML/makeZIP, e não depois.
KCC_STAGES: list[tuple[str, str]] = [
    ("Working on", "Lendo os capítulos..."),
    ("Preparing source images", "Preparando as imagens..."),
    ("Checking images", "Verificando as imagens..."),
    ("Processing images", "Processando as imagens..."),
    ("imgFileProcessing:", "Imagens processadas."),
    ("Creating EPUB file", "Gerando o EPUB..."),
    ("buildHTML:", "Montando o livro..."),
    ("makeZIP time:", "Compactando..."),
    ("Creating MOBI files", "Gerando o MOBI (pode demorar)..."),
]


def vendor_kcc_dir() -> Path:
    """Diretório do KCC, tanto rodando do fonte quanto dentro do bundle."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent / "vendor" / "kcc"


def run_kcc_worker(args: list[str]) -> int:
    """Entrada interna do modo worker (só usada pelo executável congelado).

    Replica o que o `kcc-c2e.py` faz como `__main__`: ajusta o PATH (7-Zip e
    Kindle Previewer) e delega ao KCC, que encerra o processo por conta própria.
    """
    sys.path.insert(0, str(vendor_kcc_dir()))

    # pyrefly: ignore [missing-import]
    from kcc import modify_path

    modify_path()

    # pyrefly: ignore [missing-import]
    from kindlecomicconverter.startup import startC2E

    sys.argv = ["kcc-c2e"] + args
    startC2E()  # termina via sys.exit com o código do KCC
    return 0


class KCCConverter:
    """Converte uma pasta de imagens já processadas num arquivo para Kindle."""

    def __init__(self, profile: str = "KPW6", output_format: str = "MOBI") -> None:
        self.profile = profile
        self.output_format = output_format

    def run(self, manga_title: str, reporter: ProgressReporter | None = None) -> bool:
        """Converte o mangá. Retorna True se o KCC concluiu com sucesso."""
        reporter = reporter or NullReporter()

        manga_path = BASE_DIR / manga_title
        if not manga_path.exists() or not any(manga_path.iterdir()):
            logging.warning(f"No downloaded chapters found for '{manga_title}'. Skipping KCC.")
            return False

        command = self._build_command(manga_path)
        if command is None:
            return False

        logging.info(f"Starting KCC conversion: {manga_title}")
        try:
            return self._run_and_track(command, reporter)
        except OSError as exc:
            logging.error(f"Could not launch KCC: {exc}")
            return False

    def _run_and_track(self, command: list[str], reporter: ProgressReporter) -> bool:
        """Roda o KCC lendo seu stdout linha a linha, para reportar progresso."""
        # PYTHONUNBUFFERED é o que faz o progresso ser ao vivo. Quando o stdout do
        # filho é um pipe, o Python troca buffer de linha por buffer de bloco e
        # segura tudo até o processo sair — as 9 etapas chegariam juntas no fim, e
        # a barra pularia direto para 100%. `bufsize=1` aqui não resolve: ele só
        # afeta a leitura deste lado, não a escrita do lado de lá.
        env = dict(os.environ, PYTHONUNBUFFERED="1")

        process = subprocess.Popen(
            command,
            cwd=self._working_dir(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )

        step = 0
        assert process.stdout is not None
        for raw in process.stdout:
            line = raw.rstrip()
            if not line:
                continue
            logging.debug(f"KCC: {line}")

            matched = self._match_stage(line)
            if matched is None:
                continue

            index, label = matched
            # max(): o KCC repete marcadores por tomo; a barra nunca deve voltar.
            step = max(step, index + 1)
            reporter.on_convert_progress(step, len(KCC_STAGES), label)

        returncode = process.wait()
        if returncode != 0:
            logging.error(f"KCC exited with code {returncode}.")
            return False
        return True

    @staticmethod
    def _match_stage(line: str) -> tuple[int, str] | None:
        for index, (marker, label) in enumerate(KCC_STAGES):
            if marker in line:
                return index, label
        return None

    def _kcc_args(self, manga_path: Path) -> list[str]:
        # Atenção: no KCC, `-d` é `--delete` (store_true), não "directory". Passá-lo
        # apagava a pasta de origem — imagens e state.json — quebrando o checkpoint.
        return [
            "-p",
            self.profile,
            "-m",
            "-f",
            self.output_format,
            "-b",
            "1",
            str(manga_path),
        ]

    def _build_command(self, manga_path: Path) -> list[str] | None:
        args = self._kcc_args(manga_path)

        if getattr(sys, "frozen", False):
            return [sys.executable, KCC_WORKER_FLAG, *args]

        script = vendor_kcc_dir() / "kcc-c2e.py"
        if not script.exists():
            logging.error(f"KCC script not found at: {script}")
            return None
        return [sys.executable, str(script), *args]

    def _working_dir(self) -> str | None:
        # Congelado, o próprio KCC ajusta o CWD via modify_path(); do fonte, ele
        # precisa rodar de dentro da pasta do vendor.
        if getattr(sys, "frozen", False):
            return None
        return str(vendor_kcc_dir())

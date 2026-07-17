import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import logging
from multiprocessing import freeze_support

from src.config import DEFAULT_WORKERS, setup_logging
from src.core.browser import BrowserManager
from src.core.converter import KCC_WORKER_FLAG, run_kcc_worker
from src.core.pipeline import MangaPipeline, PipelineConfig
from src.core.progress import LoggingReporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download manga chapters and convert them to a Kindle format via KCC."
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the graphical interface instead of running on the CLI.",
    )
    parser.add_argument("-u", "--url", help="Manga main page URL (required unless --gui).")
    parser.add_argument("-p", "--profile", default="KPW6", help="KCC device profile.")
    parser.add_argument(
        "-cr",
        "--chapter_range",
        default=None,
        help="Chapter range, e.g. '1-10' or '15.5'. Defaults to all chapters.",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Concurrent image downloads (default: {DEFAULT_WORKERS}).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging, including per-chapter timing breakdown.",
    )
    return parser


def main() -> int:
    # O KCC usa multiprocessing; sem isto o .exe congelado se re-executaria em
    # loop a cada worker que ele abrisse. No-op ao rodar do fonte.
    freeze_support()

    # Reentrada como KCC: precisa vir antes do argparse, pois estes argumentos
    # são do KCC e não os nossos.
    argv = sys.argv[1:]
    if argv and argv[0] == KCC_WORKER_FLAG:
        return run_kcc_worker(argv[1:])

    parser = build_parser()
    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    # Sem nenhum argumento é o caso do duplo-clique no executável: quem abre
    # assim quer a interface, não uma mensagem de uso que pisca e some.
    if args.gui or not argv:
        # Importado sob demanda: o caminho puro de CLI não deve carregar Qt.
        from src.gui.app import launch

        return launch()

    if not args.url:
        parser.error("the following arguments are required: -u/--url (or use --gui)")

    # Validado antes de qualquer trabalho caro: subir o Chrome e passar pelo
    # Cloudflare custa ~15s que não fazem sentido se a faixa está malformada.
    try:
        config = PipelineConfig(
            url=args.url,
            profile=args.profile,
            chapter_range=args.chapter_range,
            workers=args.workers,
        )
    except ValueError as exc:
        logging.error(str(exc))
        return 2

    browser = BrowserManager()
    try:
        MangaPipeline.create(config, browser, LoggingReporter()).run()
    except KeyboardInterrupt:
        logging.warning("Interrupted by user.")
        return 130
    finally:
        browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

# Manga to Kindle Pipeline

A automated pipeline to download manga from MangaKakalot (and compatible clones) and convert them into optimized Kindle formats (MOBI/AZW3) using Kindle Comic Converter (KCC).

## Project Structure

- `src/main.py`: Main entry point orchestrating the download and conversion workflow.
- `src/core/`: Core modules following a clean architecture (`browser.py`, `scraper.py`, `downloader.py`, `converter.py`).
- `src/vendor/kcc/`: Dedicated folder for KCC conversion engine dependencies.
- `downloads/`: Local storage for processed manga chapters.
- `browser_profile_uc/`: Local cache for undetected-chromedriver sessions to effectively bypass Cloudflare.

## Prerequisites

1. [uv](https://docs.astral.sh/uv/getting-started/installation/): manages the environment. **Python itself is not required** — uv downloads and manages its own Python 3.12.
2. Google Chrome (installed in the default system path). Required by `undetected_chromedriver` to bypass Cloudflare.
3. 7-Zip: Must be installed at `C:\Program Files\7-Zip` or `C:\Program Files (x86)\7-Zip` (required for KCC processing). [Download here](https://www.7-zip.org/)
4. Kindle Previewer 3: Required for MOBI/AZW3 compilation only (EPUB works without it). [Download here](https://www.amazon.com/Kindle-Previewer/b?ie=UTF8&node=21381691011)

`setup.ps1` checks all of these and tells you exactly what is missing.

## Installation

1. Open PowerShell.
2. Clone the repository and navigate to the root folder.
3. Run the setup script:
   ```powershell
   .\setup.ps1
   ```

If your execution policy blocks the script, run it as:
```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

`setup.ps1` validates the external dependencies, creates the virtual environment with `uv`, installs everything, and verifies the packages actually import. Use `-Force` to rebuild the environment from scratch.

## Usage

### Interactive Mode

```powershell
.\run.ps1
```
Prompts for the manga URL, chapter range, and device profile, and offers to run setup if the project isn't configured yet. You can also skip the prompts:
```powershell
.\run.ps1 -Url "MANGA_URL" -Chapters "1-10" -Profile KPW6
```

### CLI Mode

```powershell
.\.venv\Scripts\python.exe src\main.py -u "MANGA_URL" -cr "START-END" -p "PROFILE"
```

**Parameters:**
- `-u, --url`: The full URL of the manga main page (e.g. `https://www.mangakakalot.gg/manga/akechi`).
- `-cr, --chapter_range`: Range of chapters to download (e.g., `1-10` or `15.5`). Defaults to all chapters.
- `-p, --profile`: KCC device profile (default is `KPW6` for Kindle Paperwhite 11th/12th Gen).
- `-w, --workers`: Concurrent image downloads (default `6`). Values above 8 risk HTTP 429 / IP bans.
- `-v, --verbose`: DEBUG logging, including a per-chapter timing breakdown.

## Resuming an interrupted download

Progress is checkpointed per chapter in `downloads/<manga>/state.json`. If a run is interrupted — network error, `Ctrl+C`, a crash — simply run the same command again: completed chapters are skipped and the download resumes where it stopped. A chapter that fails does not abort the run; it is retried on the next execution.

## Graphical Interface

```powershell
.\.venv\Scripts\python.exe src\main.py --gui
```
Paste the URL, pick your Kindle model (the list is read from KCC itself), and watch the progress bar. Cancelling stops after the current chapter finishes, and the progress is checkpointed either way. The CLI remains fully supported — the GUI is just another front-end over the same pipeline.

## Building a standalone executable

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1 -Clean
```
Produces `dist\MangakakalotDownloader\` (~220 MB), containing `MangakakalotDownloader.exe`. Distribute the whole folder.

```powershell
MangakakalotDownloader.exe --gui
MangakakalotDownloader.exe -u "MANGA_URL" -p KPW6
```

The build uses PyInstaller in `--onedir` mode: `--onefile` extracts to a temp folder on every launch, which breaks `undetected_chromedriver`'s `use_subprocess=True` driver patching.

**The target machine still needs Google Chrome, 7-Zip, and Kindle Previewer 3** — these cannot be bundled. Chrome in particular is required because `undetected_chromedriver` downloads and patches a matching chromedriver at runtime.

## Credits and Acknowledgments

This project utilizes Kindle Comic Converter (KCC) for the ebook conversion stage. This repository is a custom pipeline and does not claim ownership of the KCC engine. All credits for the conversion logic and Kindle optimization belong to the original KCC developers: https://github.com/ciromattia/kcc

### Third-Party Licensing

The KCC source code included in this repository (under `src/vendor/kcc/`) is distributed under the **ISC License**.
For full license details, copyright notices, and disclaimers regarding the KCC component, please refer to the `vendor/kcc/LICENSE.txt` file included in this distribution.

## Disclaimer

This tool is intended for personal use and backup purposes. Please support the official manga industry by purchasing titles from authorized retailers.

# Manga to Kindle Pipeline

A automated pipeline to download manga from MangaKakalot (and compatible clones) and convert them into optimized Kindle formats (MOBI/AZW3) using Kindle Comic Converter (KCC).

## Project Structure

- `src/main.py`: Main entry point orchestrating the download and conversion workflow.
- `src/core/`: Core modules following a clean architecture (`browser.py`, `scraper.py`, `downloader.py`, `converter.py`).
- `src/vendor/kcc/`: Dedicated folder for KCC conversion engine dependencies.
- `downloads/`: Local storage for processed manga chapters.
- `browser_profile_uc/`: Local cache for undetected-chromedriver sessions to effectively bypass Cloudflare.

## Prerequisites

1. Python 3.12 or higher.
2. Google Chrome (installed in the default system path).
3. 7-Zip: Must be installed at `C:\Program Files\7-Zip` or `C:\Program Files (x86)\7-Zip` (required for KCC processing). [Download here](https://www.7-zip.org/)
4. Kindle Previewer 3: Required for MOBI/AZW3 compilation. [Download here](https://www.amazon.com/Kindle-Previewer/b?ie=UTF8&node=21381691011)

## Installation

1. Open PowerShell or Command Prompt.
2. Clone the repository and navigate to the root folder.
3. Run the setup script:
   ```cmd
   .\setup.bat
   ```

Note: `setup.bat` will automatically verify your Python installation, check for 7-Zip, create a virtual environment, and install all required dependencies safely.

## Usage

You can use the interactive batch script or the command line directly.

### Interactive Mode

Run `run_pop.bat` and follow the interactive prompts to provide the Manga URL, chapter range, and device profile. The script will automatically trigger setup if you haven't run it yet!

### CLI Mode

Navigate to the root folder and use the virtual environment python:
```cmd
.\.venv\Scripts\python.exe src\main.py -u "MANGA_URL" -cr "START-END" -p "PROFILE"
```

**Parameters:**
- `-u, --url`: The full URL of the manga main page (e.g. `https://www.mangakakalot.gg/manga/akechi`).
- `-cr, --chapter_range`: Range of chapters to download (e.g., `1-10` or `15-15.5`).
- `-p, --profile`: KCC device profile (default is `KPW6` for Kindle Paperwhite 11th/12th Gen).

## Credits and Acknowledgments

This project utilizes Kindle Comic Converter (KCC) for the ebook conversion stage. This repository is a custom pipeline and does not claim ownership of the KCC engine. All credits for the conversion logic and Kindle optimization belong to the original KCC developers: https://github.com/ciromattia/kcc

### Third-Party Licensing

The KCC source code included in this repository (under `src/vendor/kcc/`) is distributed under the **ISC License**.
For full license details, copyright notices, and disclaimers regarding the KCC component, please refer to the `vendor/kcc/LICENSE.txt` file included in this distribution.

## Disclaimer

This tool is intended for personal use and backup purposes. Please support the official manga industry by purchasing titles from authorized retailers.

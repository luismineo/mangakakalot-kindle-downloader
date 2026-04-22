# Manga to Kindle Pipeline

A automated pipeline to download manga from MangaKakalot (and compatible clones) and convert them into optimized Kindle formats (MOBI/AZW3) using Kindle Comic Converter (KCC).

## Project Structure

-   src/main.py: Main entry point for the pipeline (scraping and downloading).
-   src/vendor/kcc/: Dedicated folder for KCC conversion engine dependencies.
-   downloads/: Local storage for processed manga chapters.
-   browser_profile_uc/: Local cache for undetected-chromedriver sessions.

## Prerequisites

1. Python 3.12 or higher.
2. Google Chrome (installed in the default system path).
3. 7-Zip: Must be installed at 'C:\Program Files\7-Zip' (required for KCC processing). [Download here](https://www.7-zip.org/)
4. Kindle Previewer 3: Required for MOBI/AZW3 compilation. [Download here](https://www.amazon.com/Kindle-Previewer/b?ie=UTF8&node=21381691011)

## Installation

1. Open PowerShell as Administrator.
2. Clone the repository and navigate to the root folder.
3. Run the setup script:
   .\setup.bat

Note: Running as Administrator is recommended to ensure that environment variables and system dependencies like 7-Zip are properly accessed.

## Usage

You can use the interactive batch script or the command line directly.

### Interactive Mode

Run 'run_pipeline.bat' and follow the instructions to provide the URL and chapter range.

### CLI Mode

Navigate to the root folder and use the virtual environment python:
.venv\Scripts\python.exe src\main.py -u "MANGA_URL" -cr "START-END" -p "PROFILE"

Parameters:
-u, --url: The full URL of the manga main page.
-cr, --chapter_range: Range of chapters to download (e.g., 1-10 or 15-15.5).
-p, --profile: KCC device profile (default is KPW6 for Kindle Paperwhite 11th/12th Gen).

## Credits and Acknowledgments

This project utilizes Kindle Comic Converter (KCC) for the ebook conversion stage. This repository is a custom pipeline and does not claim ownership of the KCC engine. All credits for the conversion logic and Kindle optimization belong to the original KCC developers: https://github.com/ciromattia/kcc

### Third-Party Licensing

The KCC source code included in this repository (under `src/vendor/kcc/`) is distributed under the **ISC License**.
For full license details, copyright notices, and disclaimers regarding the KCC component, please refer to the `vendor/kcc/LICENSE.txt` file included in this distribution.

## Disclaimer

This tool is intended for personal use and backup purposes. Please support the official manga industry by purchasing titles from authorized retailers.

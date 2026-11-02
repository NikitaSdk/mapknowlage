@echo off
cd /d "%~dp0"
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\pyinstaller --noconfirm --windowed --onefile --name MapKnowlage --icon "assets\icon.ico" --add-data "data;data" --add-data "assets;assets" --hidden-import PySide6.QtMultimedia --collect-submodules scipy --collect-submodules opensimplex --exclude-module PySide6.QtWebEngine --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtPdf --exclude-module PySide6.QtPdfWidgets main.py

@echo off
chcp 65001 > nul
title DECADE – Automatische Bericht-Erstellung
echo.
echo ============================================================
echo   DECADE Reporting – Automatischer Modus
echo   (Sucht in REDCap nach neuen Messungen ohne Bericht)
echo ============================================================
echo.
cd /d "%~dp0"

if not exist ".venv\" (
    echo Erstelle virtuelle Umgebung und installiere Pakete ^(einmaliger Vorgang^)...
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
    echo Installation abgeschlossen!
    echo.
)

.venv\Scripts\python src\main.py --auto
echo.
if %ERRORLEVEL% neq 0 (
    echo FEHLER! Das Programm wurde mit einem Fehler beendet.
    echo Bitte schaue in die Datei decade_log.txt für Details.
)
pause

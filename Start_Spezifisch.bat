@echo off
chcp 65001 > nul
title DECADE – Spezifische Bericht-Erstellung
echo.
echo ============================================================
echo   DECADE Reporting – Manueller Modus
echo ============================================================
echo.
cd /d "%~dp0"
set /p IDs="Bitte die Record-IDs eingeben (mit Leerzeichen getrennt, z.B. decad_101 decad_105): "
set /p LANG="Sprache (de/en, Enter fuer de): "
if "%LANG%"=="" set LANG=de
set /p MZP="MZP (optional, z.B. 3 fuer MZP3): "
set MZP_ARG=
if not "%MZP%"=="" set MZP_ARG=--mzp %MZP%

echo.
if not "%MZP%"=="" (
    echo Starte Verarbeitung fuer: %IDs% ^(Sprache: %LANG%, MZP erzwingen: %MZP%^)
) else (
    echo Starte Verarbeitung fuer: %IDs% ^(Sprache: %LANG%^)
)
echo.

if not exist ".venv\" (
    echo Erstelle virtuelle Umgebung und installiere Pakete ^(einmaliger Vorgang^)...
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
    echo Installation abgeschlossen!
    echo.
)

.venv\Scripts\python src\main.py --ids %IDs% --lang %LANG% %MZP_ARG%
echo.
if %ERRORLEVEL% neq 0 (
    echo FEHLER! Das Programm wurde mit einem Fehler beendet.
    echo Bitte schaue in die Datei decade_log.txt fuer Details.
)
pause

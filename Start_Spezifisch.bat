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
echo.
echo Starte Verarbeitung fuer: %IDs% (Sprache: %LANG%)
echo.
python src\main.py --ids %IDs% --lang %LANG%
echo.
if %ERRORLEVEL% neq 0 (
    echo FEHLER! Das Programm wurde mit einem Fehler beendet.
    echo Bitte schaue in die Datei decade_log.txt fuer Details.
)
pause

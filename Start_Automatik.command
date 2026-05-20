#!/bin/bash
# DECADE Reporting – Automatischer Modus (Mac)
# Doppelklick: Finder → Rechtsklick auf Datei → "Öffnen" (einmalig bestätigen)

cd "$(dirname "$0")"

echo ""
echo "============================================================"
echo "  DECADE Reporting – Automatischer Modus"
echo "  (Sucht in REDCap nach neuen Messungen ohne Bericht)"
echo "============================================================"
echo ""

python3 src/main.py --auto

echo ""
if [ $? -ne 0 ]; then
    echo "FEHLER! Das Programm wurde mit einem Fehler beendet."
    echo "Details findest du in der Datei: decade_log.txt"
fi

echo "Drücke ENTER, um das Fenster zu schließen..."
read

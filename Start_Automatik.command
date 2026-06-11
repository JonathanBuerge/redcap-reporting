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

if [ ! -d ".venv" ]; then
    echo "Erstelle virtuelle Umgebung und installiere Pakete (einmaliger Vorgang)..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    echo "Installation abgeschlossen!"
    echo ""
fi

.venv/bin/python src/main.py --auto

echo ""
if [ $? -ne 0 ]; then
    echo "FEHLER! Das Programm wurde mit einem Fehler beendet."
    echo "Details findest du in der Datei: decade_log.txt"
fi

echo "Drücke ENTER, um das Fenster zu schließen..."
read

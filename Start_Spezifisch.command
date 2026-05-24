#!/bin/bash
# DECADE Reporting – Manueller Modus (Mac)
# Doppelklick: Finder → Rechtsklick auf Datei → "Öffnen" (einmalig bestätigen)

cd "$(dirname "$0")"

echo ""
echo "============================================================"
echo "  DECADE Reporting – Manueller Modus"
echo "============================================================"
echo ""
echo "Bitte die Record-IDs eingeben (mit Leerzeichen getrennt):"
echo "Beispiel: decad_101 decad_105 decad_112"
echo ""
read -p "IDs: " IDS_INPUT
read -p "Sprache (de/en, Standard: de): " LANG_INPUT

if [ -z "$LANG_INPUT" ]; then
    LANG_INPUT="de"
fi

echo ""
echo "Starte Verarbeitung für: $IDS_INPUT (Sprache: $LANG_INPUT)"
echo ""

python3 src/main.py --ids $IDS_INPUT --lang $LANG_INPUT

echo ""
if [ $? -ne 0 ]; then
    echo "FEHLER! Das Programm wurde mit einem Fehler beendet."
    echo "Details findest du in der Datei: decade_log.txt"
fi

echo "Drücke ENTER, um das Fenster zu schließen..."
read

# DECADE Report Generator

Dieses System dient der automatisierten Erstellung von strukturierten klinischen Leistungsberichten für die **DECADE-Studie** (DSBG/Universität Basel). Es transformiert Rohdaten aus REDCap in professionelle PDF-Berichte im Corporate Design der Universität Basel.

---

## 🚀 Inbetriebnahme & Installation

### Voraussetzungen
* **Python 3.10+** (auf Mac und Windows)
* Alle benötigten Pakete sind in einer virtuellen Umgebung (`.venv`) installierbar.

### Installation
Führe im Terminal des Projekt-Hauptverzeichnisses folgende Befehle aus:
```bash
# Virtuelle Umgebung erstellen (falls nicht vorhanden)
python3 -m venv .venv

# Virtuelle Umgebung aktivieren
source .venv/bin/activate  # Mac/Linux
# oder unter Windows: .venv\Scripts\activate

# Pakete installieren
pip install -r requirements.txt
```

---

## 💻 Bedienung (Berichte erstellen)

Für eine einfache Bedienung stehen Skripte für Windows (Doppelklick auf `.bat`) und Mac (Rechtsklick -> Öffnen auf `.command`) bereit:

### 1. Automatischer Modus (REDCap-Abgleich)
Sucht in REDCap nach neuen, vollständig ausgefüllten Messungen, für die noch kein Bericht hochgeladen wurde, generiert diese und lädt sie direkt wieder zu REDCap hoch.
* **Mac:** `Start_Automatik.command`
* **Windows:** `Start_Automatik.bat`

### 2. Manueller Modus (Spezifische Patienten)
Erstellt Berichte für spezifische, von dir eingegebene Patient-IDs (z.B. `decad_105`).
* **Mac:** `Start_Spezifisch.command`
* **Windows:** `Start_Spezifisch.bat`

---

## 🌐 Sprachauswahl (Deutsch / Englisch)

Das System unterstützt Berichte auf **Deutsch** (`de`) und **Englisch** (`en`). Die Sprache kann auf zwei Arten gesteuert werden:

### A. Automatisch über REDCap (Standard)
Sobald in den REDCap-Metadaten deines Projekts das Feld `language` mit den Werten `de` oder `en` befüllt ist, liest das System die bevorzugte Sprache des Patienten aus und generiert den Bericht vollautomatisch in der passenden Sprache.

### B. Manuelle Eingabe (Spezifisch)
Wenn du `Start_Spezifisch` ausführst, wirst du nach der Eingabe der IDs gefragt, in welcher Sprache die Berichte generiert werden sollen:
```text
IDs: decad_105 decad_143
Sprache (de/en, Standard: de): en
```
* **Enter:** Erzeugt den Bericht auf Deutsch (Standard).
* **en:** Erzeugt den Bericht auf Englisch.

### C. Über die Kommandozeile
Entwickler können die Sprache direkt beim Ausführen der `main.py` übergeben. Dies überschreibt temporär alle REDCap-Metadaten:
```bash
# Erzeugt den Bericht für decad_105 auf Englisch
.venv/bin/python src/main.py --ids decad_105 --lang en
```

---

## 🎨 Icons / Piktogramme einbinden

Das System fügt im PDF-Bericht automatisch passende Piktogramme links neben die Graphen ein, falls diese vorhanden sind. 

1. Erstelle (falls nicht vorhanden) den Ordner: `data/icons/`
2. Lege deine Symbole dort als **PNG-Dateien** ab.
3. Die Dateinamen müssen exakt dem Schlüssel der jeweiligen Messung entsprechen:

* **groesse_abs.png** (Körpergrösse)
* **gewicht_abs.png** (Körpergewicht)
* **handkraft_abs.png** (Max. Greifkraft Absolut)
* **handkraft_rel.png** (Greifkraft Relativ)
* **sprung_abs.png** (Sprunghöhe)
* **sprung_rel.png** (Sprungkraft Relativ)
* **kreuzheben_abs.png** (Isom. Kreuzheben Absolut)
* **kreuzheben_rel.png** (Ganzkörperkraft Relativ)
* **beinstrecker_abs.png** (Max. Beinstreckkraft Absolut)
* **beinstrecker_rel.png** (Beinkraft Relativ)
* **vo2max_abs.png** (Ausdauer VO2max)
* **leistung_abs.png** (Max. Leistung Ergometer)

*Hinweis: Wenn für eine Messung kein Icon im Ordner existiert, wird der Graph wie gewohnt über die volle Breite gezeichnet (ohne Darstellungsfehler).*

---

## 📁 Ordnerstruktur & Fehlerdiagnose

* `/reports`: Hier werden alle lokal erzeugten PDF-Berichte strukturiert nach Patienten-ID abgelegt.
* `decade_log.txt`: Protokolldatei im Hauptverzeichnis. Bei Fehlern (z.B. fehlenden Spalten in REDCap oder falschen API-Keys) findest du dort detaillierte Fehlermeldungen.
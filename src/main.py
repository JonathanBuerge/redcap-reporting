import argparse
import logging
import os
import sys
import warnings
import traceback
from analyzer import Analyzer
from report_generator import ReportGenerator
from visualizer import Visualizer
from utils import ensure_patient_dirs, load_merged_data
from redcap_api import get_pending_reports, upload_report_to_redcap, download_and_refresh_data

warnings.simplefilter(action='ignore', category=FutureWarning)

DATA_FILE    = "./data/anonym.csv"
API_FILE     = "./data/api_data.csv"
REPORTS_BASE = "./reports"

# ── ENTWICKLUNGS-MODUS ───────────────────────────────────────────────────────
# Solange diese Liste NICHT leer ist, werden NUR diese IDs verarbeitet –
# unabhängig vom gewählten Modus (--auto, --ids oder interaktiv).
# Wenn alles getestet ist und der Vollbetrieb starten soll: Liste leeren → []
# ─────────────────────────────────────────────────────────────────────────────
DEV_IDS: list[str] = ["decad_105", "decad_143", "decad_108", "decad_155", "decad_134"]

# Schalter für Übersichtsberichte (Sammelt alle Daten der CSV für einen Gruppen-Plot)
GENERATE_OVERVIEW: bool = True

# DEFINITION DER PLOTS (Reihenfolge hier = Reihenfolge im PDF)
PLOTS_CONFIG = [
    ("groesse", "groesse_ref.png"), ("gewicht", "gewicht_ref.png"),
    ("handkraft", "handkraft_ref.png"), ("handkraft_rel", "handkraft_rel_ref.png"),
    ("sprung", "sprung_ref.png"), ("pmax_rel", "pmax_rel_ref.png"),
    ("kreuzheben", "kreuzheben_ref.png"), ("mtp_rel", "mtp_rel_ref.png"),
    ("beinstrecker", "beinstrecker_ref.png"), ("leg_ext_rel", "leg_ext_rel_ref.png"),
    ("vo2max", "vo2_ref.png"), ("leistung", "leistung_abs_ref.png")  
]

def setup_logging():
    """Richtet das Logging für Terminal und Datei ein."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # In Datei schreiben
    file_handler = logging.FileHandler("decade_log.txt", mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # In Konsole (Terminal) schreiben
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def fetch_pending_records_from_redcap() -> list:
    """Fragt REDCap nach Records mit vollständigem CRF, aber noch ohne report_upload."""
    logging.info("API Check: Suche in REDCap nach neuen, unberichteten Messungen...")
    return get_pending_reports()

def push_report_to_redcap(patient_id: str, file_path: str) -> None:
    """Lädt das fertige PDF in das korrekte REDCap-Event des Patienten hoch."""
    success = upload_report_to_redcap(patient_id, file_path)
    if not success:
        logging.warning("Patient %s: REDCap Upload nicht erfolgreich.", patient_id)

def main():
    setup_logging()
    logging.info("="*50)
    logging.info("🚀 Starte DECADE Reporting System")
    
    # 1. Argumente auslesen (Automatik vs Manuell)
    parser = argparse.ArgumentParser(description="DECADE Report Generator")
    parser.add_argument("--auto", action="store_true", help="Automatisch neue Messungen aus REDCap ermitteln")
    parser.add_argument("--ids", nargs="+", help="Spezifische IDs manuell verarbeiten (z.B. --ids 101 105)")
    args = parser.parse_args()

    # 2. Zu verarbeitende IDs ermitteln
    patient_ids_to_process = []
    
    if args.auto:
        logging.info("Modus: AUTOMATISCH")
        patient_ids_to_process = fetch_pending_records_from_redcap()
        if not patient_ids_to_process:
            logging.info("Keine neuen Messungen in REDCap gefunden. Beende Programm.")
            return
    elif args.ids:
        logging.info(f"Modus: MANUELL (IDs: {', '.join(args.ids)})")
        patient_ids_to_process = args.ids
    else:
        # Fallback, falls jemand die Datei einfach per Doppelklick startet
        print("\nBitte wähle einen Modus:")
        print("[1] Automatisch (Nach neuen Messungen in REDCap suchen)")
        print("[2] Manuell (Bestimmte IDs eingeben)")
        wahl = input("Eingabe (1 oder 2): ")
        if wahl == "1":
            patient_ids_to_process = fetch_pending_records_from_redcap()
        elif wahl == "2":
            ids_input = input("Bitte IDs kommagetrennt eingeben (z.B. 101, 105): ")
            patient_ids_to_process = [x.strip() for x in ids_input.split(",") if x.strip()]
        else:
            logging.error("Ungültige Eingabe.")
            return

    # DEV-MODUS: Wenn DEV_IDS gesetzt, nur diese verarbeiten
    if DEV_IDS:
        logging.warning(
            "⚠️  ENTWICKLUNGS-MODUS AKTIV – nur %d Test-IDs werden verarbeitet: %s",
            len(DEV_IDS), ', '.join(DEV_IDS)
        )
        patient_ids_to_process = DEV_IDS

    # 3. Daten von REDCap aktualisieren
    logging.info("Aktualisiere lokale Daten aus REDCap...")
    refresh_ok = download_and_refresh_data(anonym_path=DATA_FILE, api_path=API_FILE)
    if not refresh_ok:
        logging.warning("REDCap-Download fehlgeschlagen – versuche es mit vorhandenen lokalen Daten weiter.")

    # 4. Lokale CSV-Daten laden
    logging.info("Lade lokale CSV-Daten...")
    df = load_merged_data(DATA_FILE, API_FILE)
    if df is None:
        logging.error("Kritischer Fehler beim Laden der CSV-Dateien. Bitte sicherstellen, dass die .env korrekt ist.")
        return

    analyzer = Analyzer(df)
    viz = Visualizer()
    count = 0

    dev_overview: dict[str, list] = {'girls': [], 'boys': []}

    # --- NEU: Daten für Übersicht sammeln (ALLE Patienten aus der CSV) ---
    if GENERATE_OVERVIEW:
        logging.info("Sammle Daten für Übersichts-Plots (alle Patienten)...")
        all_ids_in_csv = analyzer.get_all_patient_ids()
        for p_id in all_ids_in_csv:
            mdata = analyzer.get_patient_data(p_id)
            if mdata:
                p_sex = mdata["meta"].get("sex", "girls")
                dev_overview[p_sex].append((str(p_id), mdata))

    # 4. Berichte generieren
    for p_id in patient_ids_to_process:
        str_id = str(p_id)
        logging.info(f"--- BEARBEITE PATIENT {str_id} ---")

        patient_dir, plots_dir = ensure_patient_dirs(REPORTS_BASE, str_id)
        metrics_data = analyzer.get_patient_data(p_id)
        
        if not metrics_data:
            logging.warning(f"Patient {str_id}: Keine Daten in der CSV gefunden.")
            continue

        p_age = metrics_data["meta"].get("age")
        p_sex = metrics_data["meta"].get("sex", "girls")

        logging.info(f"Metadaten geladen: Geschlecht={p_sex}, Alter={p_age}")
        if p_age is None:
            logging.warning(f"Patient {str_id}: Alter fehlt! (Plots können evtl. nicht korrekt skaliert werden)")

        plot_files = []
        for metric_key, filename in PLOTS_CONFIG:
            hist_data = metrics_data.get(metric_key, {}).get("history", [])
            
            if hist_data and p_age is not None:
                plot_path = f"{plots_dir}/{filename}"
                try:
                    patient_weight = metrics_data.get("gewicht", {}).get("post")
                    try:
                        patient_weight = float(patient_weight)
                    except (ValueError, TypeError):
                        patient_weight = None
                        
                    viz.create_reference_plot(metric_key, hist_data, p_sex, plot_path, patient_weight)
                    if os.path.exists(plot_path):
                        plot_files.append(plot_path)
                    else:
                        logging.error(f"Patient {str_id}: Plot-Datei nicht gefunden nach Erstellung: {plot_path}")
                except Exception as e:
                    logging.error(f"Patient {str_id}: CRASH bei {metric_key}-Plot. Grund: {e}")
                    logging.debug(traceback.format_exc())
            else:
                grund = "Alter fehlt" if p_age is None else "Keine validen Historien-Daten"
                logging.info(f"Patient {str_id}: Überspringe {metric_key}-Plot ({grund})")

        # Maturity Plot
        maturity_hist = metrics_data.get("meta", {}).get("maturity_history", [])
        if maturity_hist:
            mat_plot_path = os.path.join(plots_dir, "maturity_plot.png")
            try:
                viz.create_maturity_plot(maturity_hist, p_sex, mat_plot_path)
                if os.path.exists(mat_plot_path):
                    plot_files.append(mat_plot_path)
            except Exception as e:
                logging.error(f"Patient {str_id}: Fehler bei Maturity-Plot: {e}")

        # PDF Generierung & Upload
        report_file = f"{patient_dir}/report.pdf"
        try:
            report = ReportGenerator(report_file)
            report.build_report(metrics_data, plot_files)
            count += 1
            logging.info(f"Patient {str_id}: PDF erfolgreich generiert ({report_file})")
            
            # ---> REDCap Upload anstoßen <---
            push_report_to_redcap(str_id, report_file)
            logging.info(f"Patient {str_id}: Upload-Job für REDCap gesendet.")
            
        except Exception as e:
            logging.error(f"Patient {str_id}: Fehler beim PDF-Bau. Grund: {e}")
            logging.debug(traceback.format_exc())

    logging.info(f"✅ Fertig! {count} Reports wurden erstellt und verarbeitet.")
    logging.info("="*50)

    # 5. Übersichtsreports pro Geschlecht erstellen
    if GENERATE_OVERVIEW:
        logging.info("="*50)
        logging.info("🔍 Erstelle Gruppen-Übersichtsreports...")
        overview_base = os.path.join(REPORTS_BASE, "_dev_overview")
        os.makedirs(overview_base, exist_ok=True)

        for sex in ('girls', 'boys'):
            patients_for_sex = dev_overview[sex]
            if not patients_for_sex:
                logging.info("  Übersicht '%s': Keine Daten vorhanden, überspringe.", sex)
                continue

            sex_label = 'Maedchen' if sex == 'girls' else 'Jungs'
            plots_dir = os.path.join(overview_base, f"plots_{sex_label}")
            os.makedirs(plots_dir, exist_ok=True)

            logging.info("  Übersicht '%s': %d Patient(en).", sex, len(patients_for_sex))

            overview_plot_files = []
            for metric_key, filename in PLOTS_CONFIG:
                # Daten aller Patienten dieses Geschlechts für diese Metrik sammeln
                all_histories = []
                for p_id, mdata in patients_for_sex:
                    hist = mdata.get(metric_key, {}).get("history", [])
                    weight = mdata.get("gewicht", {}).get("post")
                    try:
                        weight = float(weight)
                    except (ValueError, TypeError):
                        weight = None
                    all_histories.append((p_id, hist, weight))

                plot_path = os.path.join(plots_dir, filename)
                try:
                    viz.create_overview_plot(metric_key, all_histories, sex, plot_path)
                    if os.path.exists(plot_path):
                        overview_plot_files.append(plot_path)
                except Exception as e:
                    logging.error("  Übersicht '%s': Fehler bei %s-Plot: %s", sex, metric_key, e)
                    logging.debug(traceback.format_exc())

            # Übersichts-PDF bauen (eine Seite pro Plot, kein Patient-Header)
            overview_pdf = os.path.join(overview_base, f"overview_{sex_label}.pdf")
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.platypus import SimpleDocTemplate, Image, Spacer, Paragraph
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib.units import cm

                doc = SimpleDocTemplate(overview_pdf, pagesize=A4,
                                        rightMargin=1*cm, leftMargin=1*cm,
                                        topMargin=1*cm, bottomMargin=1*cm)
                styles = getSampleStyleSheet()
                story = []
                title_text = f"DEV-Übersicht: {'Mädchen' if sex == 'girls' else 'Jungs'} ({len(patients_for_sex)} Patienten)"
                story.append(Paragraph(title_text, styles['Title']))
                story.append(Spacer(1, 0.5*cm))

                for plot_path in overview_plot_files:
                    story.append(Image(plot_path, width=18*cm, height=11*cm))
                    story.append(Spacer(1, 0.5*cm))

                doc.build(story)
                logging.info("  ✅ Übersichts-PDF: %s", overview_pdf)
            except Exception as e:
                logging.error("  ❌ Fehler beim Bau des Übersichts-PDF ('%s'): %s", sex, e)
                logging.debug(traceback.format_exc())

        logging.info("Gruppen-Übersichtsreports abgeschlossen.")
        logging.info("="*50)

if __name__ == "__main__":
    # Verhindert, dass das Fenster bei einem Doppelklick direkt zugeht
    try:
        main()
    except Exception as e:
        logging.critical(f"UNERWARTETER FEHLER: {e}")
        logging.debug(traceback.format_exc())
    finally:
        input("\nDrücke ENTER, um das Fenster zu schließen...")
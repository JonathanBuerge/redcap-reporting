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
DEV_IDS: list[str] = []

# Schalter für Übersichtsberichte (Sammelt alle Daten der CSV für einen Gruppen-Plot)
GENERATE_OVERVIEW: bool = True

# DEFINITION DER PLOTS (Reihenfolge hier = Reihenfolge im PDF)
PLOTS_CONFIG = [
    ("groesse",        "groesse_abs.png"),
    ("gewicht",        "gewicht_abs.png"),
    ("handkraft",      "handkraft_abs.png"),
    ("handkraft_rel",  "handkraft_rel.png"),
    ("sprung",         "sprung_abs.png"),
    ("sprung_rel",     "sprung_rel.png"),
    ("kreuzheben",     "kreuzheben_abs.png"),
    ("kreuzheben_rel", "kreuzheben_rel.png"),
    ("beinstrecker",   "beinstrecker_abs.png"),
    ("beinstrecker_rel","beinstrecker_rel.png"),
    ("vo2max",         "vo2max_abs.png"),
    ("leistung",       "leistung_abs.png"),
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

def push_report_to_redcap(patient_id: str, file_path: str, mzp: str = None) -> None:
    """Lädt das fertige PDF in das korrekte REDCap-Event des Patienten hoch."""
    success = upload_report_to_redcap(patient_id, file_path, mzp)
    if not success:
        logging.warning("Patient %s: REDCap Upload nicht erfolgreich.", patient_id)

# ============================================================
# DEV-Hilfsfunktion für PHV-Übersichtstabelle
# und Scatter-Plots (effektives Alter vs. biologisches Alter,
# Eq1/2 vs Eq3/4 Vergleich)
# ============================================================
def _dev_build_phv_content(patients_for_sex: list, sex: str, tmp_dir: str):
    """
    Erstellt:
      1. Eine ReportLab-Tabelle mit PHV-Werten aller Patienten (alle MZP)
         – inkl. bio_age_eq12 und bio_age_eq34 sowie deren Differenz zum eff. Alter
      2. Scatter-Plot 1: Eq3/4 – Eff. Alter vs. Biol. Alter
      3. Scatter-Plot 2: Eq1/2 – Eff. Alter vs. Biol. Alter
      4. Scatter-Plot 3: Eq1/2 vs. Eq3/4 (direkter Vergleich)
    Gibt (story_elements, list[scatter_path]) zurück.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet

    styles = getSampleStyleSheet()
    story_elements = []

    # --- Tabelle ---
    header = [
        "ID", "MZP", "Datum",
        "Eff. Alter",
        "Offset Eq3/4", "Bio Eq3/4", "Diff Eq3/4",
        "Offset Eq1/2", "Bio Eq1/2", "Diff Eq1/2",
    ]
    # Sub-header row for raw values (shown once, visually anchored to header)
    subheader = [
        "", "", "↳ Rohdaten:",
        "Grösse (cm)", "Gewicht (kg)", "Sitzhöhe (cm)", "Beinlänge (cm)", "", "", "",
    ]
    rows = [header, subheader]

    scatter_chron       = []
    scatter_bio_eq34    = []
    scatter_bio_eq12    = []
    diff_eq34_list      = []
    diff_eq12_list      = []
    # Track which row indices are "raw" rows (for styling)
    raw_row_indices = [1]  # subheader is index 1
    formula_row_indices = []

    for p_id, mdata in patients_for_sex:
        history = mdata.get("meta", {}).get("maturity_history", [])
        for i, entry in enumerate(history):
            chron       = entry.get("chron_age")
            off_eq34    = entry.get("off_eq34")
            if off_eq34 is None:
                off_eq34 = entry.get("offset")
            bio_eq34    = entry.get("bio_age_eq34")
            if bio_eq34 is None:
                bio_eq34 = entry.get("bio_age")
            off_eq12    = entry.get("off_eq12")
            bio_eq12    = entry.get("bio_age_eq12")
            date        = entry.get("date", "-")
            # Raw input values
            raw_h   = entry.get("raw_h")
            raw_w   = entry.get("raw_w")
            raw_sh  = entry.get("raw_sh")
            raw_leg = entry.get("raw_leg")

            if chron is None:
                continue

            def _diff_str(bio, lst):
                if bio is not None:
                    d = bio - chron
                    lst.append(d)
                    return f"{d:+.2f}"
                return "-"

            diff_34_str = _diff_str(bio_eq34, diff_eq34_list)
            diff_12_str = _diff_str(bio_eq12, diff_eq12_list)

            # --- Zeile 1: Ergebnisse ---
            rows.append([
                str(p_id),
                f"T{i+1}",
                str(date)[:10],
                f"{chron:.1f}",
                f"{off_eq34:.2f}" if off_eq34 is not None else "-",
                f"{bio_eq34:.1f}" if bio_eq34 is not None else "-",
                diff_34_str,
                f"{off_eq12:.2f}" if off_eq12 is not None else "-",
                f"{bio_eq12:.1f}" if bio_eq12 is not None else "-",
                diff_12_str,
            ])

            # --- Zeile 2: Rohdaten ---
            raw_row_indices.append(len(rows))  # index before append
            rows.append([
                "",
                "",
                "↳ Rohwerte:",
                f"G: {raw_h} cm"   if raw_h   is not None else "-",
                f"W: {raw_w} kg"   if raw_w   is not None else "-",
                f"SH: {raw_sh} cm" if raw_sh  is not None else "-",
                f"BL: {raw_leg} cm"if raw_leg is not None else "-",
                "",
                "",
                "",
            ])

            # --- Zeile 3: Rechnung ---
            f_eq34_str = entry.get("f_eq34_str", "-")
            f_eq12_str = entry.get("f_eq12_str", "-")
            formula_row_indices.append(len(rows))
            rows.append([
                "",
                "",
                "↳ Formeln:",
                Paragraph(f"<font size=5><b>Eq3/4:</b> {f_eq34_str}<br/><b>Eq1/2:</b> {f_eq12_str}</font>", styles['Normal']),
                "", "", "", "", "", ""
            ])

            if chron is not None:
                scatter_chron.append(chron)
                if bio_eq34 is not None:
                    scatter_bio_eq34.append(bio_eq34)
                if bio_eq12 is not None:
                    scatter_bio_eq12.append(bio_eq12)


    # Durchschnittszeile
    avg_cells = [
        "", "", "", "Ø Diff.:",
        "", "", Paragraph(f"<b>{np.mean(diff_eq34_list):+.2f}</b>", styles['Normal']) if diff_eq34_list else "-",
        "", "", Paragraph(f"<b>{np.mean(diff_eq12_list):+.2f}</b>", styles['Normal']) if diff_eq12_list else "-"
    ]
    rows.append(avg_cells)

    story_elements.append(Paragraph(
        f"<b>PHV-Daten ({'Mädchen' if sex == 'girls' else 'Jungs'})</b>",
        styles['Heading2']
    ))
    story_elements.append(Spacer(1, 0.3*cm))

    col_widths = [1.8*cm, 1.0*cm, 1.9*cm, 1.6*cm, 1.8*cm, 1.6*cm, 1.7*cm, 1.8*cm, 1.6*cm, 1.7*cm]
    tbl = Table(rows, colWidths=col_widths, repeatRows=2)
    base_style = [
        ('BACKGROUND',    (0, 0),  (-1, 0),   colors.HexColor('#b2dfdb')),
        ('BACKGROUND',    (0, 1),  (-1, 1),   colors.HexColor('#e8f5e9')),
        ('FONTNAME',      (0, 0),  (-1, 1),   'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0),  (-1, -1),  7),
        ('GRID',          (0, 0),  (-1, -1),  0.4, colors.grey),
        ('BACKGROUND',    (0, -1), (-1, -1),  colors.HexColor('#e0f2f1')),
        ('ALIGN',         (3, 0),  (-1, -1),  'CENTER'),
    ]
    # Style raw-value rows: light grey background + italic font
    for ri in raw_row_indices:
        if ri < len(rows):
            base_style.append(('BACKGROUND', (0, ri), (-1, ri), colors.HexColor('#f0f0f0')))
            base_style.append(('FONTNAME',   (0, ri), (-1, ri), 'Helvetica-Oblique'))
            base_style.append(('TEXTCOLOR',  (0, ri), (-1, ri), colors.HexColor('#555555')))
            
    # Style formula rows: light yellow background + span columns
    for ri in formula_row_indices:
        if ri < len(rows):
            base_style.append(('BACKGROUND', (0, ri), (-1, ri), colors.HexColor('#fff9c4')))
            base_style.append(('SPAN', (3, ri), (-1, ri)))
            base_style.append(('ALIGN', (3, ri), (-1, ri), 'LEFT'))
            
    tbl.setStyle(TableStyle(base_style))
    story_elements.append(tbl)
    story_elements.append(Spacer(1, 0.5*cm))

    # --- Scatter-Plots ---
    scatter_paths = []
    sex_label_text = 'Mädchen' if sex == 'girls' else 'Jungs'
    ref_phv = 14.0 if sex == 'boys' else 12.0
    pt_color = '#e53935' if sex == 'boys' else '#8e24aa'

    def _scatter_base(ax, x, y, xlabel, ylabel, title, ref_line=True):
        ax.scatter(x, y, alpha=0.65, s=35, color=pt_color, zorder=3)
        if ref_line:
            all_v = list(x) + list(y)
            lo, hi = min(all_v) - 0.5, max(all_v) + 0.5
            ax.plot([lo, hi], [lo, hi], 'k--', lw=1, label='y = x')
            ax.axhline(ref_phv, color='grey', lw=0.8, ls=':', label=f'Ø PHV ({ref_phv} J.)')
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    # Plot 1: Eq3/4 – eff. Alter vs. biol. Alter
    if scatter_chron and scatter_bio_eq34:
        fig, ax = plt.subplots(figsize=(8, 5))
        _scatter_base(ax, scatter_chron, scatter_bio_eq34,
                      'Effektives Alter (J.)', 'Biologisches Alter Eq3/4 (J.)',
                      f'Eff. vs. Bio. Alter Eq3/4 ({sex_label_text})')
        p = os.path.join(tmp_dir, f"phv_scatter_eq34_{sex}.png")
        fig.tight_layout(); fig.savefig(p, dpi=120); plt.close(fig)
        scatter_paths.append(p)

    # Plot 2: Eq1/2 – eff. Alter vs. biol. Alter
    if scatter_chron and scatter_bio_eq12:
        fig, ax = plt.subplots(figsize=(8, 5))
        _scatter_base(ax, scatter_chron, scatter_bio_eq12,
                      'Effektives Alter (J.)', 'Biologisches Alter Eq1/2 (J.)',
                      f'Eff. vs. Bio. Alter Eq1/2 ({sex_label_text})')
        p = os.path.join(tmp_dir, f"phv_scatter_eq12_{sex}.png")
        fig.tight_layout(); fig.savefig(p, dpi=120); plt.close(fig)
        scatter_paths.append(p)

    # Plot 3: Eq1/2 vs. Eq3/4 – direkter Vergleich
    if scatter_bio_eq12 and scatter_bio_eq34:
        n = min(len(scatter_bio_eq12), len(scatter_bio_eq34))
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.scatter(scatter_bio_eq34[:n], scatter_bio_eq12[:n],
                   alpha=0.65, s=35, color=pt_color, zorder=3)
        lo = min(scatter_bio_eq34[:n] + scatter_bio_eq12[:n]) - 0.5
        hi = max(scatter_bio_eq34[:n] + scatter_bio_eq12[:n]) + 0.5
        ax.plot([lo, hi], [lo, hi], 'k--', lw=1, label='Eq1/2 = Eq3/4')
        ax.set_xlabel('Biologisches Alter Eq3/4 (J.)')
        ax.set_ylabel('Biologisches Alter Eq1/2 (J.)')
        ax.set_title(f'Eq1/2 vs. Eq3/4 Vergleich ({sex_label_text})')
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)
        p = os.path.join(tmp_dir, f"phv_scatter_cmp_{sex}.png")
        fig.tight_layout(); fig.savefig(p, dpi=120); plt.close(fig)
        scatter_paths.append(p)

    return story_elements, scatter_paths
# ============================================================
# ENDE DEV-Hilfsfunktionen
# ============================================================


def main():
    setup_logging()
    logging.info("="*50)
    logging.info("🚀 Starte DECADE Reporting System")
    
    # 1. Argumente auslesen (Automatik vs Manuell)
    parser = argparse.ArgumentParser(description="DECADE Report Generator")
    parser.add_argument("--auto", action="store_true", help="Automatisch neue Messungen aus REDCap ermitteln")
    parser.add_argument("--ids", nargs="+", help="Spezifische IDs manuell verarbeiten (z.B. --ids 101 105)")
    parser.add_argument("--lang", type=str, default=None, choices=["de", "en"], help="Sprache für die Berichte (überschreibt REDCap-Metadaten)")
    parser.add_argument("--mzp", type=str, default=None, help="Optional: Spezifischer Messzeitpunkt (z.B. 3) für den Upload, ignoriert crf_complete")
    parser.add_argument("--no-upload", action="store_true", help="Verhindert den Upload der PDFs zu REDCap (nur lokal speichern)")
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
            args.auto = True
            patient_ids_to_process = fetch_pending_records_from_redcap()
        elif wahl == "2":
            ids_input = input("Bitte IDs eingeben (mit Leerzeichen oder Komma getrennt, z.B. decad_101 decad_105): ")
            raw_ids = [x.strip() for x in ids_input.replace(',', ' ').split() if x.strip()]
            patient_ids_to_process = []
            for raw_id in raw_ids:
                if raw_id.isdigit():
                    patient_ids_to_process.append(f"decad_{raw_id}")
                elif raw_id.startswith("decade_"):
                    patient_ids_to_process.append(raw_id.replace("decade_", "decad_"))
                else:
                    patient_ids_to_process.append(raw_id)
            
            lang_input = input("Sprache (de/en, Standard: de): ").strip()
            if lang_input in ["de", "en"]:
                args.lang = lang_input
            else:
                args.lang = "de"
                
            mzp_input = input("MZP (optional, z.B. 3 für MZP3): ").strip()
            if mzp_input:
                args.mzp = mzp_input
                
            upload_input = input("Soll das PDF in REDCap hochgeladen werden? (j/n, Standard: j): ").strip().lower()
            if upload_input in ["n", "nein"]:
                args.no_upload = True
        else:
            logging.error("Ungültige Eingabe.")
            return

    # DEV-MODUS: Wenn DEV_IDS gesetzt und keine spezifischen IDs übergeben wurden, nur diese verarbeiten
    if DEV_IDS and not args.ids:
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
    
    logging.info("Überprüfe Datenintegrität des gesamten Datensatzes...")
    analyzer.check_data_integrity(logging)
    
    # Sprache für diesen Lauf bestimmen (manuell oder Default)
    run_lang = args.lang if args.lang else 'de'
    viz = Visualizer(lang=run_lang)
    count = 0

    dev_overview: dict[str, list] = {'girls': [], 'boys': []}

    # --- NEU: Daten für Übersicht sammeln (ALLE Patienten aus der CSV) ---
    if GENERATE_OVERVIEW and args.auto:
        logging.info("Sammle Daten für Übersichts-Plots (alle Patienten)...")
        all_ids_in_csv = analyzer.get_all_patient_ids()
        for p_id in all_ids_in_csv:
            mdata = analyzer.get_patient_data(p_id)
            if mdata:
                p_sex = mdata["meta"].get("sex", "unknown")
                if p_sex in dev_overview:
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

        # Körperzusammensetzungs-Plots (konditionell je nach Messmethode)
        bodycomp_method = metrics_data.get("meta", {}).get("bodycomp_method")
        bodycomp_plots = []
        if bodycomp_method == 'dxa':
            bodycomp_plots = [
                ("koerperfett_dxa",  "koerperfett_dxa_abs.png"),
                ("knochendichte",     "knochendichte_abs.png"),
            ]
        elif bodycomp_method == 'inbody':
            bodycomp_plots = [
                ("koerperfett_inbody", "koerperfett_inbody_abs.png"),
            ]

        for metric_key, filename in bodycomp_plots:
            # Nutze 'koerperfett' als Histiorienschlüssel für beide fat-Varianten
            hist_key = 'koerperfett'
            hist_data = metrics_data.get(hist_key, {}).get("history", [])
            if metric_key == 'knochendichte':
                hist_data = metrics_data.get('knochendichte', {}).get("history", [])

            if hist_data and p_age is not None:
                plot_path = f"{plots_dir}/{filename}"
                try:
                    viz.create_reference_plot(metric_key, hist_data, p_sex, plot_path)
                    if os.path.exists(plot_path):
                        plot_files.append(plot_path)
                    else:
                        logging.error(f"Patient {str_id}: Body-Comp-Plot nicht gefunden: {plot_path}")
                except Exception as e:
                    logging.error(f"Patient {str_id}: CRASH bei {metric_key}-Plot. Grund: {e}")
                    logging.debug(traceback.format_exc())
            else:
                grund = "Alter fehlt" if p_age is None else "Keine validen Historien-Daten"
                logging.info(f"Patient {str_id}: Überspringe {metric_key}-Plot ({grund})")

        # PDF Generierung & Upload
        report_file = f"{patient_dir}/report.pdf"
        lang = args.lang if args.lang else metrics_data["meta"].get("language", "de")
        try:
            report = ReportGenerator(report_file, lang=lang)
            report.build_report(metrics_data, plot_files)
            count += 1
            logging.info(f"Patient {str_id}: PDF erfolgreich generiert ({report_file})")
            
            # ---> REDCap Upload anstoßen <---
            if not args.no_upload:
                push_report_to_redcap(str_id, report_file, args.mzp)
                logging.info(f"Patient {str_id}: Upload-Job für REDCap gesendet.")
            else:
                logging.info(f"Patient {str_id}: Upload übersprungen (--no-upload aktiv).")
            
        except Exception as e:
            logging.error(f"Patient {str_id}: Fehler beim PDF-Bau. Grund: {e}")
            logging.debug(traceback.format_exc())

    logging.info(f"✅ Fertig! {count} Reports wurden erstellt und verarbeitet.")
    logging.info("="*50)

    # 5. Übersichtsreports pro Geschlecht erstellen
    if GENERATE_OVERVIEW and args.auto:
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

            # Körperzusammensetzungs-Übersichtsplots
            for ov_key, ov_file, hist_source, req_method in [
                ('koerperfett_dxa',    'koerperfett_dxa_abs.png',    'koerperfett',   'dxa'),
                ('knochendichte',      'knochendichte_abs.png',      'knochendichte', 'dxa'),
                ('koerperfett_inbody', 'koerperfett_inbody_abs.png', 'koerperfett',   'inbody'),
            ]:
                all_histories = []
                for p_id, mdata in patients_for_sex:
                    method = mdata.get("meta", {}).get("bodycomp_method")
                    if method != req_method:
                        continue
                    
                    # Patienten vorübergehend von DXA ausschließen
                    #if req_method == 'dxa' and p_id in ['decad_116', 'decad_137', 'decad_141', 'decad_134']:
                    #    continue

                    hist = mdata.get(hist_source, {}).get("history", [])
                    all_histories.append((p_id, hist, None))
                ov_path = os.path.join(plots_dir, ov_file)
                try:
                    viz.create_overview_plot(ov_key, all_histories, sex, ov_path)
                    if os.path.exists(ov_path):
                        overview_plot_files.append(ov_path)
                except Exception as e:
                    logging.error("  Übersicht '%s': Fehler bei %s-Plot: %s", sex, ov_key, e)
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
                
                note_text = ("<font color='red'><b>Hinweis:</b> Die Patienten 116, 137, 134 und 141 wurden aus den DXA-Plots "
                             "(Körperfett & Knochendichte) vorübergehend ausgeschlossen. "
                             "Sie werden nach der Korrektur ihrer Werte wieder hinzugefügt.</font>")
                story.append(Paragraph(note_text, styles['Normal']))
                story.append(Spacer(1, 0.5*cm))

                # Übersicht-Plots in die richtige Reihenfolge bringen (passend zum Patienten-Report)
                plot_order = [
                    "groesse_abs.png", "gewicht_abs.png",
                    "koerperfett_dxa_abs.png", "knochendichte_abs.png", "koerperfett_inbody_abs.png",
                    "handkraft_abs.png", "handkraft_rel.png",
                    "sprung_abs.png", "sprung_rel.png",
                    "kreuzheben_abs.png", "kreuzheben_rel.png",
                    "beinstrecker_abs.png", "beinstrecker_rel.png",
                    "vo2max_abs.png", "leistung_abs.png"
                ]
                overview_plot_files.sort(key=lambda x: plot_order.index(os.path.basename(x)) if os.path.basename(x) in plot_order else 999)

                for plot_path in overview_plot_files:
                    story.append(Image(plot_path, width=18*cm, height=11*cm))
                    story.append(Spacer(1, 0.5*cm))

                # --- PHV-Tabelle + Scatter ---
                phv_story, scatter_paths = _dev_build_phv_content(
                    patients_for_sex, sex, overview_base
                )
                story.extend(phv_story)
                from reportlab.platypus import Image as RLImage
                for sp in (scatter_paths or []):
                    if sp and os.path.exists(sp):
                        story.append(RLImage(sp, width=17*cm, height=10*cm))
                        story.append(Spacer(1, 0.5*cm))
                # --- ENDE PHV-Tabelle + Scatter ---


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
from analyzer import Analyzer
from report_generator import ReportGenerator
from visualizer import Visualizer
from utils import ensure_patient_dirs
import pandas as pd
import json
import os
import warnings
import traceback

# Unterdrückt Pandas Warnungen für sauberen Output
warnings.simplefilter(action='ignore', category=FutureWarning)

# ----------------------------
# 1. KONFIGURATION
# ----------------------------
DATA_FILE = "./data/anonym.csv"
REPORTS_BASE = "./reports"

# Nur für diese IDs gibt es detaillierte Konsolen-Ausgaben
DEBUG_IDS = ["decad_105", "105"]

# DEFINITION DER PLOTS (Reihenfolge hier = Reihenfolge im PDF)
# Format: (Interner_Name_im_Analyzer, Dateiname_für_Plot)
PLOTS_CONFIG = [
    ("sprung", "sprung_ref.png"),
    ("pmax_rel", "pmax_rel_ref.png"), 
    ("vo2max", "vo2_ref.png"),
    ("mtp_rel", "mtp_rel_ref.png"),         # IMTP Kreuzheben Relativ
    ("leg_ext_rel", "leg_ext_rel_ref.png")  # Beinstrecker Relativ
]

# ----------------------------
# 2. HILFSFUNKTION (Logger)
# ----------------------------
def debug_log(patient_id, message):
    """Gibt die Nachricht nur aus, wenn die ID in der Debug-Liste steht."""
    if str(patient_id) in DEBUG_IDS:
        print(message)

# ----------------------------
# 3. HAUPT-WORKFLOW
# ----------------------------
def main():
    print(f"🚀 Starte DECADE Reporting (Alle Patienten)...")
    print(f"ℹ️  Detail-Logs nur für: {DEBUG_IDS}\n")

    # Daten laden
    try:
        df = pd.read_csv(DATA_FILE, sep=None, engine='python')
    except Exception as e:
        print(f"❌ Kritischer Fehler beim Laden der CSV: {e}")
        return

    analyzer = Analyzer(df)
    all_ids = analyzer.get_all_patient_ids()
    print(f"👥 {len(all_ids)} Patienten in CSV gefunden.\n")

    count = 0
    viz = Visualizer() # Visualizer einmal initialisieren reicht

    for p_id in all_ids:
        str_id = str(p_id)
        debug_log(str_id, f"--- BEARBEITE PATIENT {str_id} ---")

        # Ordner erstellen
        patient_dir, plots_dir = ensure_patient_dirs(REPORTS_BASE, str_id)

        # Daten vom Analyzer holen
        metrics_data = analyzer.get_patient_data(p_id)
        
        if not metrics_data:
            debug_log(str_id, "❌ Keine Daten gefunden.")
            continue

        p_age = metrics_data["meta"].get("age")
        p_sex = metrics_data["meta"].get("sex", "girls")
        
        debug_log(str_id, f"   📋 Metadaten: Geschlecht={p_sex}, Alter={p_age}")
        if p_age is None:
            debug_log(str_id, "   ⚠️  WARNUNG: Alter fehlt! (Plots benötigen ein Alter)")

        # --- DYNAMISCHE PLOT-GENERIERUNG ---
        plot_files = []
        
        for metric_key, filename in PLOTS_CONFIG:
            # Versuche, die Historie für diese Metrik zu holen
            hist_data = metrics_data.get(metric_key, {}).get("history", [])
            
            if hist_data and p_age is not None:
                plot_path = f"{plots_dir}/{filename}"
                try:
                    # Plot zeichnen lassen
                    viz.create_reference_plot(metric_key, hist_data, p_sex, plot_path)
                    
                    if os.path.exists(plot_path):
                        plot_files.append(plot_path)
                        debug_log(str_id, f"   ✅ Plot erstellt: {metric_key} ({len(hist_data)} Messpunkte)")
                    else:
                        debug_log(str_id, f"   ❌ Datei nicht gefunden nach Erstellung: {plot_path}")
                
                except Exception as e:
                    debug_log(str_id, f"   ❌ CRASH bei {metric_key}-Plot: {e}")
                    # Zeigt den genauen Fehlercode (hilft extrem bei der Fehlersuche)
                    if str_id in DEBUG_IDS: 
                        traceback.print_exc()
            else:
                grund = "Alter fehlt" if p_age is None else "Keine validen Historien-Daten (z.B. NaN)"
                debug_log(str_id, f"   ℹ️  Überspringe {metric_key}-Plot ({grund})")

        # --- REPORT GENERIEREN ---
        report_file = f"{patient_dir}/report.pdf"
        try:
            report = ReportGenerator(report_file)
            report.build_report(metrics_data, plot_files)
            count += 1
            debug_log(str_id, f"   📄 PDF generiert: {report_file}")
        except Exception as e:
            print(f"❌ Fehler beim PDF-Bau für {str_id}: {e}")

        debug_log(str_id, "-" * 30 + "\n")

    print(f"✅ Fertig! {count} Reports wurden erstellt.")

if __name__ == "__main__":
    main()
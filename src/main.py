from analyzer import Analyzer
from report_generator import ReportGenerator
from visualizer import Visualizer
from utils import ensure_patient_dirs, load_merged_data
import pandas as pd
import os
import warnings
import traceback

warnings.simplefilter(action='ignore', category=FutureWarning)

DATA_FILE = "./data/anonym.csv"
API_FILE = "./data/api_data.csv"
REPORTS_BASE = "./reports"
DEBUG_IDS = ["decad_105", "105"]

# DEFINITION DER PLOTS (Reihenfolge hier = Reihenfolge im PDF)
PLOTS_CONFIG = [
    # Anthropometrie (Größe/Gewicht)
    ("groesse", "groesse_ref.png"),
    ("gewicht", "gewicht_ref.png"),
    # Kraft
    ("handkraft", "handkraft_ref.png"),
    ("sprung", "sprung_ref.png"),
    ("pmax_rel", "pmax_rel_ref.png"),
    ("kreuzheben", "kreuzheben_ref.png"),
    ("mtp_rel", "mtp_rel_ref.png"),
    ("beinstrecker", "beinstrecker_ref.png"),
    ("vo2max", "vo2_ref.png"),
    ("leistung", "leistung_abs_ref.png")  
]

def debug_log(patient_id, message):
    if str(patient_id) in DEBUG_IDS: print(message)

def main():
    print(f"🚀 Starte DECADE Reporting (Alle Patienten)...")
    print(f"ℹ️  Detail-Logs nur für: {DEBUG_IDS}\n")

    df = load_merged_data(DATA_FILE, API_FILE)
    if df is None:
        print(f"❌ Kritischer Fehler beim Laden der CSV.")
        return


    analyzer = Analyzer(df)
    all_ids = analyzer.get_all_patient_ids()
    print(f"👥 {len(all_ids)} Patienten in CSV gefunden.\n")

    # === SCHRANKE FÜR TESTLÄUFE (ENERGIE SPAREN) ===
    # WICHTIG: Entferne das "[:15]", wenn du später wieder alle Patienten generieren willst!
    #patient_ids_to_process = all_ids#[:15]
    target_ids = ["decad_141", "141", "decad_142", "142", "decad_143", "143", "decad_102", "102", "decad_105", "105"]
    patient_ids_to_process = [pid for pid in all_ids if str(pid) in target_ids] 


    count = 0
    viz = Visualizer()

    for p_id in patient_ids_to_process:
        str_id = str(p_id)
        debug_log(str_id, f"--- BEARBEITE PATIENT {str_id} ---")

        patient_dir, plots_dir = ensure_patient_dirs(REPORTS_BASE, str_id)
        metrics_data = analyzer.get_patient_data(p_id)
        
        if not metrics_data:
            debug_log(str_id, "❌ Keine Daten gefunden.")
            continue

        p_age = metrics_data["meta"].get("age")
        p_sex = metrics_data["meta"].get("sex", "girls")
        
        debug_log(str_id, f"   📋 Metadaten: Geschlecht={p_sex}, Alter={p_age}")
        if p_age is None:
            debug_log(str_id, "   ⚠️  WARNUNG: Alter fehlt! (Plots benötigen ein Alter)")

        plot_files = []
        for metric_key, filename in PLOTS_CONFIG:
            hist_data = metrics_data.get(metric_key, {}).get("history", [])
            
            if hist_data and p_age is not None:
                plot_path = f"{plots_dir}/{filename}"
                try:
                    viz.create_reference_plot(metric_key, hist_data, p_sex, plot_path)
                    if os.path.exists(plot_path):
                        plot_files.append(plot_path)
                        debug_log(str_id, f"   ✅ Plot erstellt: {metric_key} ({len(hist_data)} Messpunkte)")
                    else:
                        debug_log(str_id, f"   ❌ Datei nicht gefunden nach Erstellung: {plot_path}")
                except Exception as e:
                    debug_log(str_id, f"   ❌ CRASH bei {metric_key}-Plot: {e}")
                    if str_id in DEBUG_IDS: traceback.print_exc()
            else:
                grund = "Alter fehlt" if p_age is None else "Keine validen Historien-Daten (z.B. NaN)"
                debug_log(str_id, f"   ℹ️  Überspringe {metric_key}-Plot ({grund})")

        # --- NEU: Maturity Plot (Einmalig pro Patient) ---
        maturity_hist = metrics_data.get("meta", {}).get("maturity_history", [])
        if maturity_hist:
            mat_plot_path = os.path.join(plots_dir, "maturity_plot.png")
            try:
                viz.create_maturity_plot(maturity_hist, p_sex, mat_plot_path)
                if os.path.exists(mat_plot_path):
                    plot_files.append(mat_plot_path)
            except Exception as e:
                debug_log(str_id, f"   ❌ Fehler bei Maturity-Plot: {e}")

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
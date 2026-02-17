from analyzer import Analyzer
from report_generator import ReportGenerator
from visualizer import Visualizer
from utils import ensure_patient_dirs
import pandas as pd
import json
import os
import warnings

# Unterdrückt Pandas Warnungen für sauberen Output
warnings.simplefilter(action='ignore', category=FutureWarning)

# ----------------------------
# Konfiguration
# ----------------------------
DATA_FILE = "./data/anonym.csv"
REPORTS_BASE = "./reports"

# Nur für diese IDs gibt es detaillierte Konsolen-Ausgaben
DEBUG_IDS = ["decad_105", "105"]

def main():
    print(f"🚀 Starte DECADE Reporting (Alle Patienten)...")
    print(f"ℹ️  Detail-Logs nur für: {DEBUG_IDS}")

    # 1. Daten laden
    try:
        df = pd.read_csv(DATA_FILE, sep=None, engine='python')
    except Exception as e:
        print(f"❌ Kritischer Fehler beim Laden der CSV: {e}")
        return

    # 2. Analyzer initialisieren
    analyzer = Analyzer(df)
    all_ids = analyzer.get_all_patient_ids()
    print(f"👥 {len(all_ids)} Patienten in CSV gefunden.\n")

    # 3. Schleife über ALLE Patienten
    count = 0
    for p_id in all_ids:
        # ID sicher als String für Vergleiche
        str_id = str(p_id)
        
        # Flag: Sollen wir für diesen Patienten loggen?
        is_debug = str_id in DEBUG_IDS

        if is_debug:
            print(f"--- BEARBEITE PATIENT {str_id} ---")

        # Ordner erstellen
        patient_dir, plots_dir = ensure_patient_dirs(REPORTS_BASE, str_id)

        # Daten holen (inkl. Alter-Berechnung)
        metrics_data = analyzer.get_patient_data(p_id)
        
        if not metrics_data:
            if is_debug: print("❌ Keine Daten gefunden.")
            continue

        # --- LOGGING (Nur wenn Debug) ---
        p_age = metrics_data["meta"].get("age")
        p_sex = metrics_data["meta"].get("sex", "girls")
        
        if is_debug:
            print(f"   📋 Metadaten: Geschlecht={p_sex}, Alter={p_age}")
            if p_age is None:
                print("   ⚠️  WARNUNG: Alter konnte nicht berechnet werden (Prüfe 'crf_timestamp'/'crf_geb')")

        # --- VISUALISIERUNG ---
        plot_files = []
        viz = Visualizer()
        
        # A) Sprunghöhe
        # Wir holen jetzt 'history' statt 'post'
        hist_sprung = metrics_data.get("sprung", {}).get("history", [])
        
        # Check: Liste darf nicht leer sein
        if hist_sprung:
            plot_path = f"{plots_dir}/sprung_ref.png"
            try:
                # Übergabe der ganzen Historie an den Visualizer
                viz.create_reference_plot("sprung", hist_sprung, p_sex, plot_path)
                
                if os.path.exists(plot_path):
                    plot_files.append(plot_path)
                    if is_debug: print(f"   ✅ Plot erstellt: Sprunghöhe ({len(hist_sprung)} Messpunkte)")
            except Exception as e:
                if is_debug: print(f"   ❌ Fehler bei Sprung-Plot: {e}")
        else:
            if is_debug: print(f"   ℹ️  Kein Sprung-Plot (Keine validen Messdaten mit Alter gefunden)")

        # B) VO2max
        hist_vo2 = metrics_data.get("vo2max", {}).get("history", [])
        
        if hist_vo2:
            plot_path_vo2 = f"{plots_dir}/vo2_ref.png"
            try:
                viz.create_reference_plot("vo2max", hist_vo2, p_sex, plot_path_vo2)
                
                if os.path.exists(plot_path_vo2):
                    plot_files.append(plot_path_vo2)
                    if is_debug: print(f"   ✅ Plot erstellt: VO2max ({len(hist_vo2)} Messpunkte)")
            except Exception as e:
                if is_debug: print(f"   ❌ Fehler bei VO2-Plot: {e}")
        else:
             if is_debug: print(f"   ℹ️  Kein VO2-Plot (Keine Daten)")

        # --- REPORT ---
        report_file = f"{patient_dir}/report.pdf"
        try:
            report = ReportGenerator(report_file)
            report.build_report(metrics_data, plot_files)
            count += 1
            if is_debug: print(f"   📄 PDF erfolgreich generiert: {report_file}")
        except Exception as e:
            print(f"❌ Fehler beim PDF-Bau für {str_id}: {e}")

        if is_debug: print("-" * 30 + "\n")

    print(f"✅ Fertig! {count} Reports wurden erstellt.")

if __name__ == "__main__":
    main()
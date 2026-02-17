from data_loader import DataLoader
from analyzer import Analyzer
from report_generator import ReportGenerator
from utils import ensure_patient_dirs
import pandas as pd
import json

# ----------------------------
# Konfiguration
# ----------------------------
DATA_FILE = "./data/anonym.csv"
REPORTS_BASE = "./reports"

# IDs für den erweiterten Console-Output
DEBUG_IDS = ["decad_105", "decad_106"]

def main():
    print("🚀 Starte DECADE Reporting...")

    # 1. Daten laden (Versucht Trennzeichen automatisch zu finden)
    # Tipp: Wenn es immer noch crasht, ändern Sie sep=None zu sep=';' oder sep=','
    try:
        df = pd.read_csv(DATA_FILE, sep=None, engine='python')
    except Exception as e:
        print(f"❌ Fehler beim Laden der CSV: {e}")
        return

    print(f"📊 CSV geladen. Spalten: {len(df.columns)}")

    # 2. Analyzer initialisieren
    analyzer = Analyzer(df)
    
    # 3. Alle Patienten finden
    patient_ids = analyzer.get_all_patient_ids()
    print(f"👥 {len(patient_ids)} Patienten gefunden.")

    # 4. Schleife
    for p_id in patient_ids:
        # Ordner erstellen
        patient_dir, plots_dir = ensure_patient_dirs(REPORTS_BASE, str(p_id))

        # Daten holen
        metrics_data = analyzer.get_patient_data(p_id)
        
        if not metrics_data:
            continue

        # --- DEBUG LOGIK FÜR IHRE TEST-PATIENTEN ---
        # Wir prüfen, ob die ID in unserer Debug-Liste ist
        if str(p_id) in DEBUG_IDS:
            print(f"\n🔎 DEBUG REPORT: {p_id}")
            print("=" * 40)
            
            # 1. Rohe Zeilen aus dem DataFrame anzeigen (nur relevante Spalten)
            print("Rohdaten aus CSV (Auszug):")
            try:
                # Versuchen, auf record_id zuzugreifen, sonst erste Spalte
                id_col = 'record_id' if 'record_id' in df.columns else df.columns[0]
                cols_of_interest = [id_col, "crf_handgrip", "crf_cmj_height", "crf_mtp_lift", "crf_vo2max"]
                # Nur Spalten nehmen, die wirklich existieren
                existing_cols = [c for c in cols_of_interest if c in df.columns]
                
                raw_rows = df[df[id_col].astype(str) == str(p_id)][existing_cols]
                print(raw_rows.to_string(index=False))
            except Exception as e:
                print(f"(Konnte Rohdaten nicht drucken: {e})")

            print("-" * 40)
            print("Extrahierte Werte für PDF:")
            # JSON formatieren für schöne Lesbarkeit
            print(json.dumps(metrics_data, indent=2, ensure_ascii=False))
            print("=" * 40 + "\n")
        # -------------------------------------------

        # Report erstellen
        report_file = f"{patient_dir}/report.pdf"
        report = ReportGenerator(report_file)
        
        # Leere Liste für Plots übergeben
        report.build_report(metrics_data, [])

    print("✅ Alle Reports generiert.")

if __name__ == "__main__":
    main()
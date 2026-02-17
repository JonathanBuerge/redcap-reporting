from data_loader import DataLoader
from analyzer import Analyzer
from visualizer import Visualizer
from report_generator import ReportGenerator
from utils import ensure_patient_dirs

# ----------------------------
# Konfiguration
# ----------------------------
DATA_FILE = "./data/anonym.csv"
REPORTS_BASE = "./reports"
MEASURE_COLS = ["crf_mns_t1", "crf_mns_t2", "crf_mns_t3", "crf_mns_t4", "crf_mns_t5"]

# Hier kannst du Patienten einfach eintragen:
PATIENTS = [5, 6, 10]  #0-basiert und ohne header-zeile also MINUS 2!! //ID Korrektur als funktion machen??

# ----------------------------
# Workflow
# ----------------------------
def main():
    loader = DataLoader(DATA_FILE, MEASURE_COLS)
    df = loader.load_csv()

    analyzer = Analyzer(df, MEASURE_COLS)
    stats = analyzer.compute_statistics()

    for patient_index in PATIENTS:
        patient_values = analyzer.get_patient_values(patient_index)

        # Patient-Ordner erstellen
        patient_dir, plots_dir = ensure_patient_dirs(REPORTS_BASE, patient_index + 2)

        # Plot speichern
        plot_file = f"{plots_dir}/boxplot.png"
        viz = Visualizer(MEASURE_COLS)
        viz.plot_patient_vs_reference(df, patient_values, plot_file)

        # PDF speichern
        report_file = f"{patient_dir}/report.pdf"
        report = ReportGenerator(report_file)
        report.build_report(stats, patient_values, plot_file)

        print(f"✅ Report erstellt für Patient {patient_index + 1}: {report_file}")

if __name__ == "__main__":
    main()
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import os

# ----------------------------
# Konfiguration
# ----------------------------
DATA_FILE = "./data/Rothdecade_DATA_2025-09-02_1432.csv"
REPORT_FILE = "./reports/patient7_report.pdf"
#MEASURE_COLS = ["IW", "IX", "IY", "IZ", "JA"]
MEASURE_COLS = ["crf_mns_t1", "crf_mns_t2", "crf_mns_t3", "crf_mns_t4",	"crf_mns_t5"]
#MEASURE_COLS = [257, 258, 259, 260, 261]
PATIENT_ROW = 5  # Zeile 7 (0-basiert gezählt! und header weg)

# ----------------------------
# 1. Daten einlesen
# ----------------------------
df = pd.read_csv(DATA_FILE)

# nur die relevanten Spalten und alle einträge werden zu float oder nan gewandelt
df_measures = df[MEASURE_COLS].copy()
for col in MEASURE_COLS:
    df_measures[col] = pd.to_numeric(df_measures[col], errors="coerce")

# NaN-Werte aus den Referenzdaten entfernen
df_measures_clean = df_measures.dropna()
print(df_measures_clean)
print(df_measures_clean.to_string)

# ----------------------------
# 2. Statistische Kennwerte berechnen
# ----------------------------
stats = df_measures_clean.describe().T  # Mittelwert, Std, Min, Max, Quartile
#print(stats[0])
#print(stats.isinstance())
stats["median"] = df_measures_clean.median(skipna=True)

# ----------------------------
# 3. Patientendaten extrahieren
# ----------------------------
patient_values = df_measures.iloc[PATIENT_ROW]

# ----------------------------
# 4. Vergleichsplot erstellen
# ----------------------------
plt.figure(figsize=(8, 5))

# Boxplots für Referenzwerte
df_measures_clean.boxplot(column=MEASURE_COLS)

# Patientwerte als rote Punkte (NaN ignorieren)
for i, col in enumerate(MEASURE_COLS, start=1):
    if pd.notna(patient_values[col]):
        plt.scatter(i, patient_values[col], color="red", label="Patient 7" if i == 1 else "")

# Patientwerte als rote Punkte
#plt.scatter(range(1, len(MEASURE_COLS) + 1), patient_values, color="red", label="Patient 7")

plt.title("Kraftwerte Patient 7 vs. Referenz")
plt.ylabel("Messwert")
plt.legend()

# Plot speichern
plot_file = "./reports/temp_plot.png"
plt.savefig(plot_file, bbox_inches="tight", dpi=150)
plt.close()

# ----------------------------
# 5. PDF Report erstellen
# ----------------------------
doc = SimpleDocTemplate(REPORT_FILE, pagesize=A4)
styles = getSampleStyleSheet()
story = []

story.append(Paragraph("Report: Patient 7", styles["Title"]))
story.append(Spacer(1, 12))

# Statistische Kennwerte als Tabelle (Textform)
for col in MEASURE_COLS:
    text = (
        f"<b>{col}</b>: "
        f"Mittelwert={stats.loc[col, 'mean']:.2f}, "
        f"Std={stats.loc[col, 'std']:.2f}, "
        f"Median={stats.loc[col, 'median']:.2f}, "
        f"Min={stats.loc[col, 'min']:.2f}, "
        f"Max={stats.loc[col, 'max']:.2f}, "
        f"Patient={patient_values[col]:.2f}"
    )
    story.append(Paragraph(text, styles["Normal"]))
    story.append(Spacer(1, 6))

# Plot einfügen
story.append(Spacer(1, 12))
story.append(Image(plot_file, width=400, height=250))

doc.build(story)

# Aufräumen
os.remove(plot_file)

print(f"✅ Report für Patient 7 erstellt: {REPORT_FILE}")

import pandas as pd
import matplotlib.pyplot as plt

class Visualizer:
    def __init__(self, measure_cols: list[str]):
        self.measure_cols = measure_cols

    def plot_patient_vs_reference(self, df: pd.DataFrame, patient_values: pd.Series, out_file: str):
        """Erstellt Boxplots mit Patientendaten und speichert als PNG"""
        plt.figure(figsize=(8, 5))

        # Boxplots für Referenz
        df.boxplot(column=self.measure_cols)

        # Patient als rote Punkte
        for i, col in enumerate(self.measure_cols, start=1):
            if pd.notna(patient_values[col]):
                plt.scatter(i, patient_values[col], color="red", label="Patient" if i == 1 else "")

        plt.title("Patient vs. Referenzwerte")
        plt.ylabel("Messwert")
        plt.legend()

        plt.savefig(out_file, bbox_inches="tight", dpi=150)
        plt.close()

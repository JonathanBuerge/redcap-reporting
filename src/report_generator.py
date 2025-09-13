from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import pandas as pd

class ReportGenerator:
    def __init__(self, out_file: str):
        self.out_file = out_file

    def build_report(self, stats: pd.DataFrame, patient_values: pd.Series, plot_file: str):
        """Erzeugt PDF mit Statistik-Tabelle und Plot"""
        doc = SimpleDocTemplate(self.out_file, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"Report für Patient", styles["Title"]))
        story.append(Spacer(1, 12))

        # Tabelle mit Kennwerten
        data = [["Messung", "Mittelwert", "Std", "Median", "Min", "Max", "Patient"]]
        for col in stats.index:
            data.append([
                col,
                f"{stats.loc[col, 'mean']:.2f}",
                f"{stats.loc[col, 'std']:.2f}",
                f"{stats.loc[col, 'median']:.2f}",
                f"{stats.loc[col, 'min']:.2f}",
                f"{stats.loc[col, 'max']:.2f}",
                f"{patient_values[col]:.2f}" if pd.notna(patient_values[col]) else "NaN"
            ])

        table = Table(data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (1, 1), (-1, -1), "CENTER")
        ]))

        story.append(table)
        story.append(Spacer(1, 24))

        # Plot einfügen
        story.append(Image(plot_file, width=400, height=250))

        doc.build(story)

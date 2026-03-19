from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import os

class ReportGenerator:
    def __init__(self, out_file: str):
        self.out_file = out_file
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

        # --- NEUE STRUKTUR-DEFINITION ---
        # Format: (Kategorie-Titel, [(Anzeige-Name, Metric-Key, Einheit, Plot-Dateiname)])
        self.report_structure = [
            ("Anthropometrie", [
                ("Körpergrösse", "groesse", "cm", "groesse_ref.png"),
                ("Körpergewicht", "gewicht", "kg", "gewicht_ref.png")
            ]),
            ("Kraftmessungen", [
                ("Max. Handkraft", "handkraft", "kg", "handkraft_ref.png"),
                ("Sprunghöhe", "sprung", "cm", "sprung_ref.png"),
                ("Sprungkraft (Relativ)", "pmax_rel", "W/kg", "pmax_rel_ref.png"),
                ("Isom. Kreuzheben (Absolut)", "kreuzheben", "kg", None),
                ("Ganzkörperkraft (Relativ)", "mtp_rel", "kg/kg", "mtp_rel_ref.png"),
                ("Max. Beinstreckkraft (Absolut)", "beinstrecker", "Nm", None),
                ("Beinkraft (Relativ)", "leg_ext_rel", "Nm/kg", "leg_ext_rel_ref.png")
            ]),
            ("Spiroergometrie", [
                ("Ausdauer (VO2max)", "vo2max", "mL/kg/min", "vo2_ref.png"),
                ("Max. Leistung", "leistung", "Watt", "leistung_abs_ref.png")
            ])
        ]

    def _create_custom_styles(self):
        """Definiert Styles für das neue, einspaltige Layout."""
        self.styles.add(ParagraphStyle(name='ReportTitle', parent=self.styles['Heading1'], fontSize=18, leading=22, textColor=colors.darkblue, alignment=TA_CENTER, spaceAfter=15))
        self.styles.add(ParagraphStyle(name='SectionHeader', parent=self.styles['Heading2'], fontSize=14, leading=16, textColor=colors.white, backColor=colors.darkblue, borderPadding=(6, 4, 6, 4), alignment=TA_LEFT, spaceBefore=15, spaceAfter=10))
        self.styles.add(ParagraphStyle(name='MetricLabel', parent=self.styles['Normal'], fontSize=11, leading=14, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='MetricValue', parent=self.styles['Normal'], fontSize=10, leading=12))
        self.styles.add(ParagraphStyle(name='MetricChange', parent=self.styles['Normal'], fontSize=10, leading=12, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='ExplanationSmall', parent=self.styles['Normal'], fontSize=8, leading=11, textColor=colors.darkgrey))

    def _create_header(self, patient_info):
        """Erstellt den Header mit Daten aus dem 'meta' Dictionary."""
        title = Paragraph("DECADE: Entwicklung der körperlichen Leistungsfähigkeit", self.styles['ReportTitle'])
        
        p_id = patient_info.get('ID', '-')
        p_name = patient_info.get('Name', '-')
        p_dob = patient_info.get('Geburtsdatum', '-')

        p_data = [[f"ID: {p_id}", f"Name: {p_name}", f"Geburtsdatum: {p_dob}"]]
        p_table = Table(p_data, colWidths=[5*cm, 8*cm, 5*cm])
        p_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8)
        ]))
        return [title, Spacer(1, 0.5*cm), p_table, Spacer(1, 1*cm)]

    def _create_metric_table(self, label, metric_data, unit=""):
        """Erstellt eine breite, saubere Tabelle für die numerischen Werte einer Metrik."""
        if not metric_data:
            metric_data = {'pre': '-', 'post': '-', 'diff': None}

        old_val = metric_data.get('pre', '-')
        new_val = metric_data.get('post', '-')
        change_pct = metric_data.get('diff', None)

        if isinstance(old_val, (int, float)): old_val = f"{old_val:.1f}"
        if isinstance(new_val, (int, float)): new_val = f"{new_val:.1f}"

        if change_pct is not None and isinstance(change_pct, (int, float)):
            prefix = "+" if change_pct > 0 else ""
            change_str = f"{prefix}{change_pct:.1f}%"
            color = colors.green if change_pct >= 0 else colors.red
        else:
            change_str = "-"
            color = colors.black

        style_change = ParagraphStyle('Change', parent=self.styles['MetricChange'], textColor=color)

        # Tabellendaten: [ Name | Startwert | Aktueller Wert | Differenz ]
        data = [[
            Paragraph(label, self.styles['MetricLabel']),
            Paragraph(f"Start: {old_val} {unit}", self.styles['MetricValue']),
            Paragraph(f"Aktuell: <b>{new_val} {unit}</b>", self.styles['MetricValue']),
            Paragraph(f"Diff: {change_str}", style_change)
        ]]
        
        # Volle Seitenbreite (ca. 18cm nutzbar)
        t = Table(data, colWidths=[6.5*cm, 4*cm, 4*cm, 3.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.lightgrey)
        ]))
        return t

    def build_report(self, metrics, plot_files):
        doc = SimpleDocTemplate(self.out_file, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        story = []
        
        # 1. Header 
        patient_meta = metrics.get("meta", {})
        story.extend(self._create_header(patient_meta))

        # Dateinamen der übergebenen Plots in ein Dictionary mappen für schnellen Zugriff
        plot_dict = {os.path.basename(p): p for p in plot_files}

        # --- NEUER LAYOUT-AUFBAU (Einspaltig) ---
        for section_title, metric_list in self.report_structure:
            # Sektions-Überschrift (z.B. "Kraftmessungen")
            story.append(Paragraph(section_title, self.styles['SectionHeader']))
            
            for display_name, metric_key, unit, expected_plot_name in metric_list:
                metric_data = metrics.get(metric_key)
                
                # Wir fassen Titel, Werte und Plot in einem "KeepTogether"-Block zusammen.
                # So wird verhindert, dass eine Überschrift auf Seite 1 steht und das Bild auf Seite 2 rutscht.
                block = []
                
                # 1. Numerische Werte (Tabelle)
                block.append(self._create_metric_table(display_name, metric_data, unit))
                block.append(Spacer(1, 0.3*cm))
                
                # 2. Diagramm (falls definiert und vorhanden)
                if expected_plot_name:
                    plot_path = plot_dict.get(expected_plot_name)
                    if plot_path and os.path.exists(plot_path):
                        # Bild ist jetzt deutlich größer! (12 x 7.5 cm statt 8 x 5 cm)
                        img = Image(plot_path, width=12*cm, height=7.5*cm)
                        block.append(img)
                    else:
                        # Optional: Falls kein Bild da ist, nichts anzeigen oder einen kleinen Text
                        block.append(Paragraph("<i>Kein Referenzdiagramm verfügbar.</i>", self.styles['ExplanationSmall']))
                
                block.append(Spacer(1, 0.8*cm)) # Abstand zum nächsten Parameter
                
                # Block zum Dokument hinzufügen (zusammenhalten)
                story.append(KeepTogether(block))

        # --- FOOTER ---
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("<b>Erklärung der Messwerte & Hinweise:</b>", self.styles['MetricLabel']))
        story.append(Spacer(1, 0.2*cm))
        
        explanations = [
            "<b>Körpergröße & Gewicht:</b> Als Referenz dienen die mitteleuropäischen Wachstumsnormen (Kromeyer-Hauschild).",
            "<b>Max. Handkraft:</b> Maß für die allgemeine Kraft des Oberkörpers. Die Referenzkurve gilt für die starke (dominante) Hand.",
            "<b>Sprunghöhe & Sprungkraft:</b> Zeigt die Explosivität und Schnellkraft der Beinmuskulatur.",
            "<b>Isom. Kreuzheben (Ganzkörperkraft):</b> Misst die statische Maximalkraft des gesamten Körpers. <b>Wichtig:</b> Die Referenzkurven für diese Metrik stammen aus einer Population von jungen Leistungssportlern (NSCA). Ein Wert unter dem Median ist für Nicht-Athleten völlig normal.",
            "<b>Max. Beinstreckkraft:</b> Zeigt die isolierte Kraft der vorderen Oberschenkelmuskulatur. Hinweis: Die Referenz basiert auf Werten handgehaltener Dynamometrie (HHD).",
            "<b>Ausdauer (VO2max) & Leistung:</b> Die Sauerstoffaufnahme ist der beste Wert für die Herz-Kreislauf-Fitness. Referenzwerte basieren auf SentrySuite/Takken.",
            "<b>Relative Werte (pro kg):</b> Um faire Vergleiche zu ermöglichen, wird Kraft/Leistung oft durch das eigene Körpergewicht geteilt."
        ]
        
        for text in explanations:
            story.append(Paragraph(text, self.styles['ExplanationSmall']))
            story.append(Spacer(1, 0.1*cm))

        doc.build(story)
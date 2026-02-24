from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
import os

class ReportGenerator:
    def __init__(self, out_file: str):
        self.out_file = out_file
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Definiert Styles."""
        self.styles.add(ParagraphStyle(name='ReportTitle', parent=self.styles['Heading1'], fontSize=16, leading=20, textColor=colors.darkblue, alignment=TA_LEFT, spaceAfter=10))
        self.styles.add(ParagraphStyle(name='SectionHeader', parent=self.styles['Heading2'], fontSize=12, leading=14, textColor=colors.white, backColor=colors.darkblue, borderPadding=(5, 2, 5, 2), alignment=TA_LEFT, spaceBefore=10, spaceAfter=5))
        self.styles.add(ParagraphStyle(name='MetricLabel', parent=self.styles['Normal'], fontSize=10, leading=12, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='MetricValue', parent=self.styles['Normal'], fontSize=10, leading=12, alignment=TA_RIGHT))
        self.styles.add(ParagraphStyle(name='MetricChange', parent=self.styles['Normal'], fontSize=9, leading=12, textColor=colors.green, alignment=TA_RIGHT))
        self.styles.add(ParagraphStyle(name='ExplanationSmall', parent=self.styles['Normal'], fontSize=8, leading=10, textColor=colors.darkgrey))

    def _create_header(self, patient_info):
        """Erstellt den Header mit Daten aus dem 'meta' Dictionary."""
        title = Paragraph("DECADE: Entwicklung der körperlichen Leistungsfähigkeit", self.styles['ReportTitle'])
        
        p_id = patient_info.get('ID', '-')
        p_name = patient_info.get('Name', '-')
        p_dob = patient_info.get('Geburtsdatum', '-')

        p_data = [[f"ID: {p_id}", f"Name: {p_name}", f"Geburtsdatum: {p_dob}"]]
        p_table = Table(p_data, colWidths=[4*cm, 7*cm, 5*cm])
        p_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6)
        ]))
        return [title, Spacer(1, 0.5*cm), p_table, Spacer(1, 1*cm)]

    def _create_metric_row(self, label, metric_data, unit=""):
        """Erstellt Zeile basierend auf Dictionary Daten {'pre': 10, 'post': 12, 'diff': 20}"""
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

        row = [
            Paragraph(label, self.styles['MetricLabel']),
            Paragraph(f"{old_val} {unit}", self.styles['MetricValue']),
            Paragraph(f"<b>{new_val} {unit}</b>", self.styles['MetricValue']),
            Paragraph(change_str, style_change)
        ]
        return row

    def _create_placeholder_img(self, text, w, h):
        d = Drawing(w, h)
        d.add(Rect(0, 0, w, h, fillColor=colors.lightgrey, strokeColor=colors.black))
        d.add(String(w/2, h/2, text, textAnchor='middle', fillColor=colors.black))
        return d

    def build_report(self, metrics, plot_files):
        doc = SimpleDocTemplate(self.out_file, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        story = []
        
        # 1. Header 
        patient_meta = metrics.get("meta", {})
        story.extend(self._create_header(patient_meta))

        # --- BLÖCKE FÜR DIE LINKE SPALTE VORBEREITEN ---
        left_blocks = []
        
        # Block 1: KRAFT
        block_kraft = []
        block_kraft.append(Paragraph("Kraftmessungen", self.styles['SectionHeader']))
        kraft_data = []
        kraft_data.append([Paragraph("", self.styles['Normal']), Paragraph("Start", self.styles['ExplanationSmall']), Paragraph("Aktuell", self.styles['ExplanationSmall']), Paragraph("Diff", self.styles['ExplanationSmall'])])
        kraft_data.append(self._create_metric_row("Max. Handkraft", metrics.get("handkraft"), "kg"))
        kraft_data.append(self._create_metric_row("Sprunghöhe", metrics.get("sprung"), "cm"))
        kraft_data.append(self._create_metric_row("Isom. Kreuzheben", metrics.get("kreuzheben"), "kg"))
        kraft_data.append(self._create_metric_row("Max. Beinstreckkraft", metrics.get("beinstrecker"), "Nm"))
        t_kraft = Table(kraft_data, colWidths=[4.2*cm, 1.8*cm, 1.8*cm, 1.5*cm])
        t_kraft.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,0), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0)]))
        block_kraft.append(t_kraft)
        left_blocks.append(block_kraft)

        # Block 2: SPIRO
        block_spiro = []
        block_spiro.append(Paragraph("Spiroergometrie", self.styles['SectionHeader']))
        spiro_data = []
        spiro_data.append(self._create_metric_row("VO2max", metrics.get("vo2max"), "ml/kg/min"))
        spiro_data.append(self._create_metric_row("Max. Leistung", metrics.get("leistung"), "Watt"))
        t_spiro = Table(spiro_data, colWidths=[4.2*cm, 1.8*cm, 1.8*cm, 1.5*cm])
        t_spiro.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0)]))
        block_spiro.append(t_spiro)
        left_blocks.append(block_spiro)

        # Block 3: ANTHRO
        block_anthro = []
        block_anthro.append(Paragraph("Anthropometrie", self.styles['SectionHeader']))
        anthro_data = []
        anthro_data.append(self._create_metric_row("Körpergrösse", metrics.get("groesse"), "cm"))
        anthro_data.append(self._create_metric_row("Gewicht", metrics.get("gewicht"), "kg"))
        t_anthro = Table(anthro_data, colWidths=[4.2*cm, 1.8*cm, 1.8*cm, 1.5*cm])
        t_anthro.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0)]))
        block_anthro.append(t_anthro)
        left_blocks.append(block_anthro)

        # --- BLÖCKE FÜR DIE RECHTE SPALTE VORBEREITEN (Plots) ---
        right_blocks = []
        
        if not plot_files:
            # Wenn keine Plots da sind, machen wir einen Dummy-Block
            content = [
                Paragraph("<b>Referenzwerte:</b>", self.styles['MetricLabel']),
                Paragraph("Perzentilkurven bieten eine visuelle Darstellung...", self.styles['ExplanationSmall']),
                Spacer(1, 0.2*cm),
                self._create_placeholder_img("Keine Plots vorhanden", 8*cm, 5*cm)
            ]
            right_blocks.append(content)
        else:
            for i, plot_path in enumerate(plot_files):
                content = []
                # Nur beim ersten Plot kommt die Überschrift dazu
                if i == 0:
                    content.append(Paragraph("<b>Referenzwerte:</b>", self.styles['MetricLabel']))
                    content.append(Paragraph("Perzentilkurven bieten eine visuelle Darstellung...", self.styles['ExplanationSmall']))
                    content.append(Spacer(1, 0.2*cm))
                
                # Plot oder Platzhalter laden
                if os.path.exists(plot_path):
                    content.append(Image(plot_path, width=8*cm, height=5*cm))
                else:
                    content.append(self._create_placeholder_img("Plot fehlt", 8*cm, 5*cm))
                
                right_blocks.append(content)

        # --- LAYOUT ZUSAMMENBAUEN (In mehrere Zeilen aufteilen) ---
        main_table_data = []
        max_rows = max(len(left_blocks), len(right_blocks))
        
        for i in range(max_rows):
            # Holt den Block oder eine leere Liste, falls keine mehr da sind
            l_cell = left_blocks[i] if i < len(left_blocks) else []
            r_cell = right_blocks[i] if i < len(right_blocks) else []
            main_table_data.append([l_cell, r_cell])

        # Die Tabelle kann jetzt zwischen den Zeilen auf eine neue Seite umbrechen!
        main_table = Table(main_table_data, colWidths=[10*cm, 8.5*cm])
        main_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'), 
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10) # Etwas Luft zwischen den Zeilen/Plots
        ]))
        story.append(main_table)
        
        # --- FOOTER ---
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("<b>Erklärung der Messwerte:</b>", self.styles['MetricLabel']))
        story.append(Spacer(1, 0.2*cm))
        
        explanations = [
            "<b>Max. Handkraft:</b> Maß für die allgemeine Kraft des Oberkörpers und die Griffkraft.",
            "<b>Sprunghöhe & Sprungkraft:</b> Zeigt die Explosivität und Schnellkraft der Beinmuskulatur.",
            "<b>Isom. Kreuzheben (Ganzkörperkraft):</b> Misst die statische Maximalkraft des gesamten Körpers (Rücken, Beine, Rumpf).",
            "<b>Max. Beinstreckkraft:</b> Zeigt die isolierte Kraft der vorderen Oberschenkelmuskulatur.",
            "<b>Ausdauer (VO2max):</b> Die maximale Sauerstoffaufnahme ist der beste Wert für die Herz-Kreislauf-Fitness.",
            "<b>Relative Werte (pro kg):</b> Um faire Vergleiche zu ermöglichen, wird die Kraft oft durch das eigene Körpergewicht geteilt (z.B. bedeutet 2,0 das Zweifache des eigenen Gewichts)."
        ]
        
        for text in explanations:
            story.append(Paragraph(text, self.styles['ExplanationSmall']))
            story.append(Spacer(1, 0.1*cm))

        doc.build(story)
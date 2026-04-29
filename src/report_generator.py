from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import os

# --- UNIBAS CORPORATE DESIGN FARBEN ---
UNIBAS_MINT = HexColor('#A5D7D2')
UNIBAS_MINT_HELL = HexColor('#D2EBE9')
UNIBAS_ROT = HexColor('#D20537')
UNIBAS_ANTHRAZIT = HexColor('#2D373C')
UNIBAS_ANTHRAZIT_HELL = HexColor('#46505A')
UNIBAS_GREEN = HexColor('#2E7D32')

class ReportGenerator:
    def __init__(self, out_file: str):
        self.out_file = out_file
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

        # --- NEUE STRUKTUR: (Name, Key, Einheit, Plot-Name, Erklärung, Referenz-Daten, is_dummy) ---
        self.report_structure = [
            ("Anthropometrie", [
                ("Körpergrösse", "groesse", "cm", "groesse_ref.png", 
                 "Zeigt das Längenwachstum im Vergleich zur altersentsprechenden Norm.", 
                 "Ref: Deutschland, gesunde Kinder (KiGGS) | DOI: 10.1007/s001120170107", False),
                 
                ("Körpergewicht", "gewicht", "kg", "gewicht_ref.png", 
                 "Zeigt die Gewichtsentwicklung im Vergleich zur altersentsprechenden Norm.", 
                 "Ref: Deutschland, gesunde Kinder (KiGGS) | DOI: 10.1007/s001120170107", False)
            ]),
            ("Kraftmessungen", [
                ("Max. Handkraft", "handkraft", "kg", "handkraft_ref.png", 
                 "Maß für die allgemeine Kraft des Oberkörpers (gezeigt für die dominante Hand).", 
                 "Ref: USA (NHANES), gesunde pädiatrische Population | DOI: 10.1080/03014460.2023.2298474", True),
                 
                ("Sprunghöhe", "sprung", "cm", "sprung_ref.png", 
                 "Zeigt die Explosivität, Beinkraft und koordinative Schnellkraft.", 
                 "Ref: Tschechien, gesunde Kinder und Jugendliche | DOI: 10.1016/j.bone.2013.06.012", False),
                 
                ("Sprungkraft (Relativ)", "pmax_rel", "W/kg", "pmax_rel_ref.png", 
                 "Zeigt die pure maximale mechanische Leistung der Beinmuskulatur pro kg Körpergewicht.", 
                 "Ref: Tschechien, gesunde Kinder und Jugendliche | DOI: 10.1016/j.bone.2013.06.012", False),
                 
                ("Isom. Kreuzheben (Absolut)", "kreuzheben", "kg", None, 
                 "Misst die statische Maximalkraft des gesamten Körpers.", "", True),
                 
                ("Ganzkörperkraft (Relativ)", "mtp_rel", "kg/kg", "mtp_rel_ref.png", 
                 "Statische Maximalkraft des Körpers im Verhältnis zum Körpergewicht.", 
                 "Ref: UK, junge Elite-Leistungssportler (Achtung: Athleten-Norm!) | DOI: 10.1519/JSC.0000000000002673", False),
                 
                ("Max. Beinstreckkraft (Absolut)", "beinstrecker", "Nm", None, 
                 "Zeigt die isolierte, absolute Kraft der vorderen Oberschenkelmuskulatur.", "", True),
                 
                ("Beinkraft (Relativ)", "leg_ext_rel", "Nm/kg", "leg_ext_rel_ref.png", 
                 "Isolierte Oberschenkelkraft im Verhältnis zum Körpergewicht.", 
                 "DUMMY REFERENZ: HHD-Werte (Kraft) aktuell nicht kompatibel mit Isomed (Drehmoment Nm)! | DOI: 10.1212/WNL.0000000000003466", True)
            ]),
            ("Spiroergometrie", [
                ("Ausdauer (VO2max)", "vo2max", "mL/kg/min", "vo2_ref.png", 
                 "Die maximale Sauerstoffaufnahme ist der Goldstandard für die Herz-Kreislauf-Fitness.", 
                 "Ref: Niederlande, gesunde Kinder und Jugendliche (SentrySuite) | DOI: 10.1513/AnnalsATS.201611-912FR", False),
                 
                ("Max. Leistung", "leistung", "Watt", "leistung_abs_ref.png", 
                 "Maximale mechanische Ausdauer-Leistung auf dem Fahrrad-Ergometer.", 
                 "Ref: Niederlande, gesunde Kinder und Jugendliche (SentrySuite) | DOI: 10.1513/AnnalsATS.201611-912FR", False)
            ])
        ]

    def _create_custom_styles(self):
        """Definiert Styles basierend auf dem CD der Uni Basel."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle', parent=self.styles['Heading1'], 
            fontName='Times-Bold', fontSize=22, leading=26, 
            textColor=UNIBAS_ANTHRAZIT, alignment=TA_LEFT, spaceAfter=0
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportSubTitle', parent=self.styles['Normal'], 
            fontName='Helvetica', fontSize=12, leading=16, 
            textColor=UNIBAS_ANTHRAZIT_HELL, alignment=TA_LEFT, spaceAfter=15
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader', parent=self.styles['Heading2'], 
            fontName='Times-Bold', fontSize=14, leading=16, 
            textColor=UNIBAS_ANTHRAZIT, backColor=UNIBAS_MINT, 
            borderPadding=(6, 4, 6, 4), alignment=TA_LEFT, spaceBefore=5, spaceAfter=10
        ))
        
        self.styles.add(ParagraphStyle(name='MetricLabel', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=UNIBAS_ANTHRAZIT))
        self.styles.add(ParagraphStyle(name='MetricValue', parent=self.styles['Normal'], fontName='Helvetica', fontSize=10, leading=12, textColor=UNIBAS_ANTHRAZIT))
        self.styles.add(ParagraphStyle(name='MetricChange', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12))
        
        # --- NEUE STYLES FÜR ERKLÄRUNGEN UND REFERENZEN ---
        self.styles.add(ParagraphStyle(name='ExplanationSmall', parent=self.styles['Normal'], fontName='Helvetica-Oblique', fontSize=9, leading=12, textColor=UNIBAS_ANTHRAZIT, spaceBefore=5))
        self.styles.add(ParagraphStyle(name='ReferenceNormal', parent=self.styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10, textColor=UNIBAS_ANTHRAZIT_HELL, spaceBefore=2))
        self.styles.add(ParagraphStyle(name='ReferenceDummy', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=UNIBAS_ROT, spaceBefore=2))

    def _create_header(self, patient_info):
        elements = []
        title = Paragraph("DECADE Report", self.styles['ReportTitle'])
        subtitle = Paragraph("Entwicklung der körperlichen Leistungsfähigkeit", self.styles['ReportSubTitle'])
        
        # --- LOGO SUCHT JETZT IM DATA ORDNER ---
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, '..', 'data', 'logo.png')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(script_dir, '..', 'data', 'logo.jpg')

        if os.path.exists(logo_path):
            img = Image(logo_path, width=5*cm, height=2*cm, kind='proportional')
            header_table = Table([[ [title, subtitle], img ]], colWidths=[11*cm, 7*cm])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (0,0), 'LEFT'),
                ('ALIGN', (1,0), (1,0), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ]))
            elements.append(header_table)
        else:
            elements.append(title)
            elements.append(subtitle)
            elements.append(Spacer(1, 0.5*cm))

        p_id = patient_info.get('ID', '-')
        p_name = patient_info.get('Name', '-')
        p_dob = patient_info.get('Geburtsdatum', '-')

        p_data = [[f"Patienten-ID: {p_id}", f"Name: {p_name}", f"Geburtsdatum: {p_dob}"]]
        p_table = Table(p_data, colWidths=[5*cm, 8*cm, 5*cm])
        p_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), UNIBAS_MINT_HELL),
            ('TEXTCOLOR', (0, 0), (-1, -1), UNIBAS_ANTHRAZIT),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEABOVE', (0,0), (-1,-1), 1, UNIBAS_MINT),
            ('LINEBELOW', (0,0), (-1,-1), 1, UNIBAS_MINT),
        ]))
        
        elements.append(p_table)
        elements.append(Spacer(1, 1*cm))
        return elements

    def _create_metric_table(self, label, metric_data, unit=""):
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
            color = UNIBAS_GREEN if change_pct >= 0 else UNIBAS_ROT
        else:
            change_str = "-"
            color = UNIBAS_ANTHRAZIT

        style_change = ParagraphStyle('Change', parent=self.styles['MetricChange'], textColor=color)

        data = [[
            Paragraph(label, self.styles['MetricLabel']),
            Paragraph(f"Start: {old_val} {unit}", self.styles['MetricValue']),
            Paragraph(f"Aktuell: <b>{new_val} {unit}</b>", self.styles['MetricValue']),
            Paragraph(f"Diff: {change_str}", style_change)
        ]]
        
        t = Table(data, colWidths=[6.5*cm, 4*cm, 4*cm, 3.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, UNIBAS_MINT_HELL)
        ]))
        return t

    def build_report(self, metrics, plot_files):
        doc = SimpleDocTemplate(self.out_file, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        story = []
        
        patient_meta = metrics.get("meta", {})
        story.extend(self._create_header(patient_meta))

        plot_dict = {os.path.basename(p): p for p in plot_files}

        for i, (section_title, metric_list) in enumerate(self.report_structure):
            if i > 0:
                story.append(PageBreak())
                
            story.append(Paragraph(section_title, self.styles['SectionHeader']))
            
            # NEU: Erklärung, Referenz und is_dummy beim Entpacken der Liste mit auslesen!
            for display_name, metric_key, unit, expected_plot_name, explanation, reference, is_dummy in metric_list:
                metric_data = metrics.get(metric_key)
                block = []
                
                # 1. Die Wertetabelle
                block.append(self._create_metric_table(display_name, metric_data, unit))
                
                # 2. Das Bild (falls vorhanden)
                if expected_plot_name:
                    block.append(Spacer(1, 0.2*cm))
                    plot_path = plot_dict.get(expected_plot_name)
                    if plot_path and os.path.exists(plot_path):
                        img = Image(plot_path, width=12*cm, height=7.5*cm)
                        block.append(img)
                        
                # 3. Die Erklärung unter der Tabelle/dem Bild
                if explanation:
                    block.append(Paragraph(explanation, self.styles['ExplanationSmall']))
                    
                # 4. Die Referenz-Infos (Mit Schalter für Rote Dummy-Daten)
                if reference:
                    ref_style = self.styles['ReferenceDummy'] if is_dummy else self.styles['ReferenceNormal']
                    block.append(Paragraph(reference, ref_style))
                
                block.append(Spacer(1, 0.8*cm)) 
                story.append(KeepTogether(block))

        doc.build(story)
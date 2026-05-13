from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from datetime import datetime, timedelta
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
                ("Max. Greifkraft (Absolut)", "handkraft", "kg", "handkraft_ref.png", 
                 "Maß für die allgemeine Kraft des Oberkörpers (gezeigt für die dominante Hand). Methodischer Hinweis: Messung im Sitzen (Ellenbogen 90° flektiert, Unterarm neutral) mittels digitalem Jamar-Dynamometer (Griffposition 2).", 
                 "Ref: Bohannon et al. (2017), Pediatric Physical Therapy. | Populationsbasierte Normwerte aus dem NIH Toolbox Projekt (n = 2.706).", False),
                 
                ("Greifkraft (Relativ)", "handkraft_rel", "kg/kg", "handkraft_rel_ref.png", 
                 "Maximale Handkraft im Verhältnis zum Körpergewicht. Methodischer Hinweis: Messung im Sitzen (Ellenbogen 90° flektiert, Unterarm neutral) mittels digitalem Jamar-Dynamometer (Griffposition 2).", 
                 "Ref: Bohannon et al. (2017), Pediatric Physical Therapy. | Populationsbasierte Normwerte aus dem NIH Toolbox Projekt (n = 2.706).", False),
                 
                ("Sprunghöhe", "sprung", "cm", "sprung_ref.png", 
                 "Zeigt die Explosivität, Beinkraft und koordinative Schnellkraft.", 
                 "Ref: Tschechien, gesunde Kinder und Jugendliche | DOI: 10.1016/j.bone.2013.06.012", False),
                 
                ("Sprungkraft (Relativ)", "pmax_rel", "W/kg", "pmax_rel_ref.png", 
                 "Zeigt die pure maximale mechanische Leistung der Beinmuskulatur pro kg Körpergewicht.", 
                 "Ref: Tschechien, gesunde Kinder und Jugendliche | DOI: 10.1016/j.bone.2013.06.012", False),
                 
                ("Isom. Kreuzheben (Absolut)", "kreuzheben", "kg", "kreuzheben_ref.png", 
                 "Misst die statische Maximalkraft des gesamten Körpers. Achtung: Verglichen mit NachwuchsathletInnen!", 
                 "Ref: Morris et al. (2020) Jungs & Salter et al. (2025) Mädchen (Athleten-Norm!)", False),
                 
                ("Ganzkörperkraft (Relativ)", "mtp_rel", "kg/kg", "mtp_rel_ref.png", 
                 "Statische Maximalkraft des Körpers im Verhältnis zum Körpergewicht. Achtung: Verglichen mit NachwuchsathletInnen!", 
                 "Ref: Morris et al. (2020) Jungs & Salter et al. (2025) Mädchen (Athleten-Norm!)", False),
                 
                ("Max. Beinstreckkraft (Absolut)", "beinstrecker", "Nm", "beinstrecker_ref.png", 
                 "Zeigt die isolierte, absolute Kraft der vorderen Oberschenkelmuskulatur (Drehmoment).", 
                 "Ref: Kanada, gesunde Kinder und Jugendliche | Hébert et al. (2015)", False),
                 
                ("Beinkraft (Relativ)", "leg_ext_rel", "Nm/kg", "leg_ext_rel_ref.png", 
                 "Isolierte Oberschenkelkraft im Verhältnis zum Körpergewicht.", 
                 "Ref: Kanada, gesunde Kinder und Jugendliche | Hébert et al. (2015)", False)
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
        
        # --- STYLE FÜR IMPRESSUM ---
        self.styles.add(ParagraphStyle(name='Impressum', parent=self.styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=UNIBAS_ANTHRAZIT_HELL))

    def _create_header(self, patient_info):
        elements = []
        title = Paragraph("<para align=center>DECADE Report</para>", self.styles['ReportTitle'])
        subtitle = Paragraph("<para align=center>Entwicklung der körperlichen Leistungsfähigkeit</para>", self.styles['ReportSubTitle'])
        
        # --- LOGOS IM DATA ORDNER SUCHEN ---
        script_dir = os.path.dirname(os.path.abspath(__file__))
        decade_logo_path = os.path.join(script_dir, '..', 'data', 'decade_logo.jpg')
        if not os.path.exists(decade_logo_path):
            decade_logo_path = os.path.join(script_dir, '..', 'data', 'decade_logo.png')
            
        unibas_logo_path = os.path.join(script_dir, '..', 'data', 'logo.png')

        if os.path.exists(decade_logo_path) and os.path.exists(unibas_logo_path):
            img_decade = Image(decade_logo_path, width=4*cm, height=1.6*cm, kind='proportional')
            img_unibas = Image(unibas_logo_path, width=4*cm, height=1.6*cm, kind='proportional')
            header_table = Table([[img_unibas, [title, subtitle], img_decade]], colWidths=[4*cm, 10*cm, 4*cm])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (0,0), 'LEFT'),
                ('ALIGN', (1,0), (1,0), 'CENTER'),
                ('ALIGN', (2,0), (2,0), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ]))
            elements.append(header_table)
        else:
            elements.append(title)
            elements.append(subtitle)
            elements.append(Spacer(1, 0.5*cm))

        p_id = patient_info.get('ID', '-')
        p_date = patient_info.get('Messdatum', '-')
        p_sex_raw = patient_info.get('sex', '-')
        p_sex = "Weiblich" if p_sex_raw == 'girls' else "Männlich" if p_sex_raw == 'boys' else "-"

        p_data = [[f"Patienten-ID: {p_id}", f"Geschlecht: {p_sex}", f"Messung vom: {p_date}"]]
        p_table = Table(p_data, colWidths=[6*cm, 6*cm, 6*cm])
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

    def _get_german_month(self, month_num):
        months = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
                  "Juli", "August", "September", "Oktober", "November", "Dezember"]
        return months[month_num - 1]

    def _create_maturity_block(self, meta, plot_dict):
        elements = []
        offset = meta.get("maturity_offset")
        bio_age = meta.get("biological_age")
        history = meta.get("maturity_history", [])
        
        if offset is None or not history:
            return []
            
        latest = history[-1]
        chron_age = latest['chron_age']
        dev_age = bio_age - chron_age

        elements.append(Paragraph("Biologischer Reifegrad (Maturity)", self.styles['SectionHeader']))
        
        # 1. Zusammenfassung (Farbig) - 2x2 Layout für mehr Platz
        summary_data = [
            [
                Paragraph(f"Effektives Alter: <b>{chron_age:.1f} J.</b>", self.styles['MetricLabel']),
                Paragraph(f"Biologisches Alter: <b>{bio_age:.1f} J.</b>", self.styles['MetricLabel'])
            ],
            [
                Paragraph(f"Diff. Biologisches Alter - Effektives Alter.: <b>{dev_age:+.1f} J.</b>", self.styles['MetricLabel']),
                Paragraph(f"Diff. zu PHV (Wachstumsschub): <b>{offset:+.1f} J.</b>", self.styles['MetricLabel'])
            ]
        ]
        t_sum = Table(summary_data, colWidths=[9*cm, 9*cm])
        t_sum.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), UNIBAS_MINT_HELL),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, UNIBAS_MINT_HELL),
        ]))
        elements.append(t_sum)
        elements.append(Spacer(1, 0.3*cm))

        # 2. Historie-Tabelle
        header = ["MZP", "Messdatum", "Effektives Alter", "Biologisches Alter"]
        table_rows = [header]
        
        for i, entry in enumerate(history):
            date_val = entry.get('date', '-')
            try:
                dt = datetime.strptime(date_val, '%Y-%m-%d')
                date_str = dt.strftime('%d.%m.%Y')
            except:
                date_str = date_val
                
            table_rows.append([
                f"T{i+1}",
                date_str,
                f"{entry['chron_age']:.1f} J.",
                f"{entry['bio_age']:.1f} J."
            ])

        # Nächste Messung als extra Zeile
        next_text = "Nächste Messung empfohlen: in ca. 10 Monaten"
        d_str = latest.get('date')
        if d_str and str(d_str) not in ('-', 'nan', 'None'):
            try:
                import pandas as pd
                last_date_dt = pd.to_datetime(d_str, errors='coerce')
                
                if pd.notna(last_date_dt):
                    # 10 Monate später
                    next_date = last_date_dt + timedelta(days=304)
                    month_name = self._get_german_month(next_date.month)
                    next_text = f"Nächste Messung empfohlen: ca. {month_name} {next_date.year}"
            except Exception as e:
                pass
        
        table_rows.append([next_text, "", "", ""])

        t_hist = Table(table_rows, colWidths=[2*cm, 5*cm, 5.5*cm, 5.5*cm])
        t_hist.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
        ]))
        
        # Falls nächste Messung Zeile existiert, spanne sie über die ganze Breite
        if len(table_rows) > len(history) + 1:
            last_idx = len(table_rows) - 1
            t_hist.setStyle(TableStyle([
                ('SPAN', (0, last_idx), (-1, last_idx)),
                ('ALIGN', (0, last_idx), (-1, last_idx), 'CENTER'),
                ('FONTNAME', (0, last_idx), (-1, last_idx), 'Helvetica-BoldOblique'),
                ('BACKGROUND', (0, last_idx), (-1, last_idx), UNIBAS_MINT_HELL),
                ('TOPPADDING', (0, last_idx), (-1, last_idx), 10),
                ('BOTTOMPADDING', (0, last_idx), (-1, last_idx), 10),
                ('LINEABOVE', (0, last_idx), (-1, last_idx), 1, colors.grey),
            ]))

        elements.append(t_hist)
        
        # Graphik
        plot_path = plot_dict.get("maturity_plot.png")
        if plot_path and os.path.exists(plot_path):
            elements.append(Spacer(1, 0.3*cm))
            # 15cm Breite / 1.71 Ratio (6/3.5) = ca. 8.75cm Höhe für Unverzerrtheit
            img = Image(plot_path, width=15*cm, height=8.75*cm)
            elements.append(img)
            
        doi_link = '<a href="https://doi.org/10.1249/00005768-200204000-00020" color="blue">10.1249/00005768-200204000-00020</a>'
        info_text = f"""
        <i>Berechnet nach Mirwald et al. (2002), DOI: {doi_link}.<br/>
        Der Wachstumsschub (PHV) tritt bei Mädchen typischerweise um das 12. Lebensjahr und bei Jungen um das 14. Lebensjahr auf. 
        Die Grafik zeigt, wie viele Jahre das Kind noch vom Schub entfernt ist (negativ) oder wie lange dieser bereits zurückliegt (positiv).</i>
        """
        elements.append(Paragraph(info_text, self.styles['ExplanationSmall']))
        elements.append(Spacer(1, 0.5*cm))
        return elements

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

            # NEU: Maturity Block nach der Anthropometrie (erste Sektion)
            if section_title == "Anthropometrie":
                story.extend(self._create_maturity_block(patient_meta, plot_dict))

        # --- IMPRESSUM AM ENDE ---
        impressum_block = []
        impressum_block.append(Spacer(1, 1*cm))
        impressum_block.append(Paragraph("Kontakt & Impressum", self.styles['SectionHeader']))
        
        impressum_text_left = """<br/>
        <b>DECADE Studie:</b> <a href="https://decade.dsbg.unibas.ch/de/" color="blue">https://decade.dsbg.unibas.ch/de/</a><br/>
        <b>Leitung:</b> Romina Ledergerber & Ralf Roth<br/>
        <b>Kontakt:</b> <a href="mailto:romina.ledergerber@unibas.ch" color="blue">romina.ledergerber@unibas.ch</a> | +41 61 207 47 73
        """
        
        impressum_text_right = """<br/>
        <b>Adresse:</b><br/>
        Departement für Sport, Bewegung und Gesundheit<br/>
        Grosse Allee 6, 4052 Basel, Switzerland
        """
        
        p_left = Paragraph(impressum_text_left, self.styles['Impressum'])
        p_right = Paragraph(impressum_text_right, self.styles['Impressum'])
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, '..', 'data', 'decade_logo.jpg')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(script_dir, '..', 'data', 'decade_logo.png')
        
        img_impressum = ""
        if os.path.exists(logo_path):
            img_impressum = Image(logo_path, width=4*cm, height=1.6*cm, kind='proportional')
        
        table = Table([[p_left, p_right, img_impressum]], colWidths=[8*cm, 6.5*cm, 4*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        impressum_block.append(table)
        story.append(KeepTogether(impressum_block))

        doc.build(story)
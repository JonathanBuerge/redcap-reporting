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
    def __init__(self, out_file: str, lang: str = 'de'):
        self.out_file = out_file
        self.lang = lang
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

        # --- MEHRSPRACHIGE LABELS ---
        self._labels = {
            'de': {
                'start':             'Start',
                'current':           'Aktuell',
                'diff':              'Diff',
                'anthropometrie':    'Anthropometrie',
                'kraft':             'Kraftmessungen',
                'spiro':             'Spiroergometrie',
                # Header
                'report_subtitle':   'Entwicklung der körperlichen Leistungsfähigkeit',
                'patient_id':        'ID',
                'sex_label':         'Geschlecht',
                'date_label':        'Messung vom',
                'sex_male':          'Männlich',
                'sex_female':        'Weiblich',
                # Intro page
                'begruessung':       (
                    "Dieser Bericht fasst die Ergebnisse der körperlichen Leistungsfähigkeit zusammen, welche im Rahmen der DECADE-Studie erhoben wurde. "
                    "Er dient dazu, individuelle Stärken aufzuzeigen und die Entwicklung über die Zeit zu dokumentieren."
                ),
                'intro_h1':          'Wie lese ich die Grafiken?',
                'intro_grafik':      (
                    "Die meisten Ergebnisse werden als Perzentilkurven dargestellt. Diese vergleichen die Leistung "
                    "mit einer gesunden Referenzgruppe gleichen Alters und Geschlechts. Die x-Achse (horizontal) ist jeweils die Zeit (Alter), die y-Achse (vertikal) die Messung.<br/><br/>"
                    "&#8226; Die mittlere, dicke Linie (P50) ist der exakte Durchschnitt.<br/>"
                    "&#8226; Liegt ein Wert auf der P75-Linie, bedeutet das: 75% der Vergleichsgruppe sind schwächer, "
                    "25% sind stärker. Diese Aussage gilt analog für die anderen Kurven.<br/><br/>"
                    "Die roten Punkte zeigen den individuellen Verlauf. Der Startwert ist der Wert der ersten Messung. "
                    "Der Report zu einem Messzeitpunkt hat auch alle früheren Messwerte in die Graphen eingezeichnet. "
                    "Die ausgewiesene Differenz in den Tabellen ist immer vom letzten zum ersten Messtermin prozentual gerechnet."
                ),
                'intro_h2':          'Absolute vs. Relative Werte',
                'intro_relativ':     (
                    "Viele Kraft- und Ausdauerwerte werden zusätzlich ‘relativ’ angegeben (z.\u202FB. W/kg oder kg/kg). "
                    "Hierbei wird die reine absolute Leistung durch das aktuelle Körpergewicht geteilt. "
                    "Dies ermöglicht einen faireren Vergleich, da schwerere Personen oft absolut mehr Kraft haben, "
                    "diese aber auch im Alltag bewegen müssen."
                ),
                'intro_h3':          'Hinweise zur Aussagekraft',
                'intro_hinweis':     (
                    "Bitte beachte: Messwerte unterliegen natürlichen Tagesform-Schwankungen. Zudem basieren die "
                    "Kurven auf spezifischen Referenzgruppen (z.\u202FB. internationale Kohorten oder Nachwuchsathleten). "
                    "Einige Referenzwerte können aufgrund kleiner Stichprobengrössen der zugrundeliegenden Studien ungenau sein. "
                    "Kleinere Abweichungen bei der Testdurchführung können die Ergebnisse ebenfalls beeinflussen. "
                    "Die Auswertung erfolgt auf Basis des kalendarischen Alters. Da sich Kinder biologisch jedoch unterschiedlich schnell entwickeln " 
                    "– der individuelle Reifeprozess kann gegenüber dem Durchschnitt um bis zu drei Jahre variieren –, sind Abweichungen " 
                    "von der Normkurve häufig völlig normal und kein Grund zur Sorge. "
                    "Die Daten dienen der Orientierung und ersetzen keine medizinische Diagnose."
                ),
                # Maturity block
                'mat_heading':       'Biologischer Reifegrad (Maturity)',
                'mat_eff_age':       'Effektives Alter',
                'mat_bio_age':       'Biologisches Alter',
                'mat_diff_bio_eff':  'Diff. Biol. - Eff. Alter',
                'mat_diff_phv':      'Diff. zu PHV (Wachstumsschub)',
                'mat_col_mzp':       'MZP',
                'mat_col_date':      'Messdatum',
                'mat_col_eff':       'Effektives Alter',
                'mat_col_bio':       'Biologisches Alter',
                'mat_next_default':  'Nächste Messung empfohlen: in ca. 10 Monaten',
                'mat_next_text':     'Nächste Messung empfohlen: ca. {month} {year}',
                'mat_info':          (
                    "<i>Berechnet nach Mirwald et al. (2002), DOI: {doi}.<br/>"
                    "Der Wachstumsschub (PHV) tritt bei Mädchen typischerweise um das 12. Lebensjahr "
                    "und bei Jungen um das 14. Lebensjahr auf. "
                    "Die Grafik zeigt, wie viele Jahre das Kind noch vom Schub entfernt ist (negativ) "
                    "oder wie lange dieser bereits zurückliegt (positiv).</i>"
                ),
                'mat_warning':       (
                    "Die anthropometrische Reifeschätzung nach Mirwald et al. (2002) ist nahe dem Wachstumsschub "
                    "am genauesten – insbesondere im Alter von etwa 10 bis 13 Jahren (Wenger & Csapo, 2025). "
                    "Ausserhalb davon nimmt der Schätzfehler zu: Bei früh Reifenden wird das Alter am PHV über-, "
                    "bei spät Reifenden unterschätzt (Regression zur Mitte). Die Werte sind eine grobe Näherung "
                    "und besonders bei sehr jungen Kindern mit Vorsicht zu interpretieren."
                ),
                'mat_years':         'J.',
                # Impressum
                'contact_heading':   'Kontakt &amp; Impressum',
                # Körperzusammensetzung
                'bodycomp_heading':      'Körperzusammensetzung',
                'bodycomp_method_dxa':   'Messung: DXA (Dual-Energie-Röntgenabsorptiometrie)',
                'bodycomp_method_inbody':'Messung: InBody (Bioelektrische Impedanzanalyse)',
                'koerperfett_label':     'Körperfettanteil',
                'koerperfett_dxa_expl':  (
                    "Der Körperfettanteil beschreibt, wie viel Prozent der gesamten Körpermasse aus Fettgewebe besteht. "
                    "Ein angemessener Körperfettanteil ist wichtig für die Gesundheit, hormonelle Regulation und sportliche Leistungsfähigkeit. "
                    "Sehr hohe wie auch sehr tiefe Werte können die körperliche Entwicklung beeinflussen. "
                    "Die Messung mit DXA gilt als eine der präzisesten nicht-invasiven Methoden zur Bestimmung der Körperzusammensetzung."
                ),
                'koerperfett_dxa_ref':   (
                    "Ref: de Groot et al. (2025), Eur J Endocrinol (Generation R Studie, niederländische Kohorte, n=6102). "
                    "DOI: 10.1093/ejendo/lvaf245."
                ),
                'koerperfett_inbody_expl': (
                    "Der Körperfettanteil wurde mit der InBody-Methode (bioelektrische Impedanzanalyse) gemessen. "
                    "Die Referenzkurven basieren auf einem massiven asiatischen Datensatz von über 22\u2019000 Kindern und Jugendlichen, "
                    "was eine hohe statistische Stabilität über den gesamten Wachstumsverlauf (6–18 Jahre) garantiert."
                ),
                'koerperfett_inbody_ref':  (
                    "Ref: Chun et al. (2024), BMC Pediatrics (koreanische Kohorte, n > 22\u2019000). "
                    "DOI: 10.1186/s12887-024-05166-3."
                ),
                'knochendichte_label':    'Knochendichte (BMD)',
                'knochendichte_expl':     (
                    "Die Knochendichte (Bone Mineral Density, BMD) beschreibt die Mineralmasse pro Fläche im Knochen (g/cm²) "
                    "und ist ein Mass für die Knochenfestigkeit. Hier wird die Knochendichte des gesamten Körpers ohne Kopf (Total Body Less Head, TBLH-BMD) gemessen und verglichen. "
                    "Die Knochendichte nimmt in der Kindheit und Jugend stetig zu und erreicht die Spitzenknochendichte "
                    "typischerweise im frühen Erwachsenenalter."
                ),
                # ALTE REFERENZ:
                # 'knochendichte_ref': "Ref: Zemel et al. (2011), Bone Mineral Density in Childhood Study (BMDCS), J Clin Endocrinol Metab. DOI: 10.1210/jc.2011-1111. Gemessen mit Hologic DXA-Gerät (Lendenwirbelsäule L1–L4).",
                'knochendichte_ref':      (
                    "Ref: de Groot et al. (2025), Eur J Endocrinol (Generation R Studie, TBLH-BMD, n=6102). "
                    "DOI: 10.1093/ejendo/lvaf245."
                ),
            },
            'en': {
                'start':             'Baseline',
                'current':           'Current',
                'diff':              'Change',
                'anthropometrie':    'Anthropometry',
                'kraft':             'Strength Measurements',
                'spiro':             'Cardiopulmonary Exercise',
                # Header
                'report_subtitle':   'Development of Physical Performance',
                'patient_id':        'Patient ID',
                'sex_label':         'Sex',
                'date_label':        'Measurement Date',
                'sex_male':          'Male',
                'sex_female':        'Female',
                # Intro page
                'begruessung':       (
                    "This report summarises the results of physical fitness testing. "
                    "It aims to highlight individual strengths and document development over time."
                ),
                'intro_h1':          'How to read the charts?',
                'intro_grafik':      (
                    "Most results are displayed as percentile curves, comparing performance "
                    "with a healthy reference group of the same age and sex. The x-axis represents time (age), the y-axis the measurement.<br/><br/>"
                    "&#8226; The thick middle line (P50) is the exact average.<br/>"
                    "&#8226; A value on the P75 line means: 75% of the reference group are weaker, "
                    "25% are stronger. This applies analogously to all other curves.<br/><br/>"
                    "Red dots show the individual trend. The baseline is the value of the first measurement. "
                    "Each report includes all previous measurements in the graphs. "
                    "The reported difference in the tables is always calculated from the last to the first measurement."
                ),
                'intro_h2':          'Absolute vs. Relative Values',
                'intro_relativ':     (
                    "Many strength and endurance values are also reported ‘relatively’ (e.g. W/kg or kg/kg). "
                    "Here, the absolute performance is divided by current body weight. "
                    "This allows fairer comparisons, as heavier individuals often have more absolute strength "
                    "but also need to move that body weight in daily life."
                ),
                'intro_h3':          'Notes on Interpretation',
                'intro_hinweis':     (
                    "Please note: measurements are subject to natural day-to-day variation. In addition, "
                    "reference curves are based on specific populations (e.g. international cohorts or youth athletes). "
                    "Some reference values may be imprecise due to small sample sizes in the underlying studies. "
                    "Minor deviations in test execution can also affect results. "
                    "The evaluation is based on chronological age. However, since children develop biologically at different rates "
                    "– the individual maturation process can vary by up to three years compared to the average –, deviations "
                    "from the norm curve are often completely normal and no cause for concern. "
                    "Data are for guidance only and do not replace medical diagnosis."
                ),
                # Maturity block
                'mat_heading':       'Biological Maturity',
                'mat_eff_age':       'Chronological Age',
                'mat_bio_age':       'Biological Age',
                'mat_diff_bio_eff':  'Diff. Biol. Age – Chron. Age',
                'mat_diff_phv':      'Diff. to PHV (Growth Spurt)',
                'mat_col_mzp':       'TP',
                'mat_col_date':      'Measurement Date',
                'mat_col_eff':       'Chronological Age',
                'mat_col_bio':       'Biological Age',
                'mat_next_default':  'Next measurement recommended: in approx. 10 months',
                'mat_next_text':     'Next measurement recommended: approx. {month} {year}',
                'mat_info':          (
                    "<i>Calculated according to Mirwald et al. (2002), DOI: {doi}.<br/>"
                    "The growth spurt (PHV) typically occurs around age 12 in girls "
                    "and around age 14 in boys. "
                    "The chart shows how many years the child is from the spurt (negative) "
                    "or how long ago it occurred (positive).</i>"
                ),
                'mat_warning':       (
                    "The anthropometric maturity estimation according to Mirwald et al. (2002) is most accurate near the growth spurt "
                    "– especially between the ages of roughly 10 and 13 years (Wenger & Csapo, 2025). "
                    "Outside of this range, the estimation error increases: in early maturers, age at PHV is overestimated, "
                    "in late maturers it is underestimated (regression to the mean). The values are a rough approximation "
                    "and should be interpreted with caution, especially in very young children."
                ),
                'mat_years':         'yrs.',
                # Impressum
                'contact_heading':   'Contact &amp; Imprint',
                # Body Composition
                'bodycomp_heading':      'Body Composition',
                'bodycomp_method_dxa':   'Method: DXA (Dual-energy X-ray Absorptiometry)',
                'bodycomp_method_inbody':'Method: InBody (Bioelectrical Impedance Analysis)',
                'koerperfett_label':     'Body Fat %',
                'koerperfett_dxa_expl':  (
                    "Body fat percentage indicates the proportion of total body mass that consists of fat tissue. "
                    "An appropriate body fat level is important for health, hormonal regulation and athletic performance. "
                    "Both very high and very low values can affect physical development. "
                    "DXA is considered one of the most precise non-invasive methods for body composition assessment."
                ),
                'koerperfett_dxa_ref':   (
                    "Ref: de Groot et al. (2025), Eur J Endocrinol (Generation R Study, Dutch cohort, n=6102). "
                    "DOI: 10.1093/ejendo/lvaf245."
                ),
                'koerperfett_inbody_expl': (
                    "Body fat percentage was measured using the InBody method (bioelectrical impedance analysis). "
                    "The reference curves are based on a large Asian dataset of over 22,000 children and adolescents, "
                    "ensuring high statistical stability across the entire growth range (ages 6\u201318 years)."
                ),
                'koerperfett_inbody_ref':  (
                    "Ref: Chun et al. (2024), BMC Pediatrics (Korean cohort, n > 22,000). "
                    "DOI: 10.1186/s12887-024-05166-3."
                ),
                'knochendichte_label':    'Bone Mineral Density (BMD)',
                'knochendichte_expl':     (
                    "Bone Mineral Density (BMD) describes the mineral mass per area in bone (g/cm²) and is a measure of bone strength. "
                    "Here, BMD is measured and compared specifically for the entire body excluding the head (Total Body Less Head, TBLH-BMD). "
                    "Bone density increases steadily throughout childhood and adolescence, "
                    "typically reaching peak bone density in early adulthood."
                ),
                # OLD REFERENCE:
                # 'knochendichte_ref': "Ref: Zemel et al. (2011), Bone Mineral Density in Childhood Study (BMDCS), J Clin Endocrinol Metab. DOI: 10.1210/jc.2011-1111. Measured with a Hologic DXA device (lumbar spine L1–L4).",
                'knochendichte_ref':      (
                    "Ref: de Groot et al. (2025), Eur J Endocrinol (Generation R Study, TBLH-BMD, n=6102). "
                    "DOI: 10.1093/ejendo/lvaf245."
                ),
            },
        }
        self._t = self._labels.get(lang, self._labels['de'])

        # --- SEKTION-TITEL (sprachabhängig) ---
        self._section_title_map = {
            'Anthropometrie':     self._t['anthropometrie'],
            'Kraftmessungen':     self._t['kraft'],
            'Spiroergometrie':    self._t['spiro'],
            'Koerperzusammensetzung': self._t['bodycomp_heading'],
        }

        # --- NEUE STRUKTUR: (Name, Key, Einheit, Plot-Name, Erklärung, Referenz-Daten, is_dummy) ---
        _rs = {
            'de': [
                ("Anthropometrie", [
                    ("Körpergrösse", "groesse", "cm", "groesse_abs.png",
                     "Zeigt das Längenwachstum im Vergleich zur altersentsprechenden Norm.",
                     "Ref: Kromeyer-Hauschild et al. (2001), Deutschland, gesunde Kinder. | DOI: 10.1007/s001120170107", False),
                    ("Körpergewicht", "gewicht", "kg", "gewicht_abs.png",
                     "Zeigt die Gewichtsentwicklung im Vergleich zur altersentsprechenden Norm.",
                     "Ref: Kromeyer-Hauschild et al. (2001), Deutschland, gesunde Kinder. | DOI: 10.1007/s001120170107", False)
                ]),
                ("Kraftmessungen", [
                    ("Greifkraft (Absolut)", "handkraft", "kg", "handkraft_abs.png",
                     "Mass für die allgemeine Kraft des Oberkörpers (gezeigt für die dominante Hand). Methodischer Hinweis: Messung der maximalen isometrischen Kraft mittels standardisiertem Hand-Dynamometer.",
                     "Ref: Bohannon et al. (2017), populationsbasierte Normwerte aus dem NIH Toolbox Projekt (n=2'706). | DOI: 10.1097/PEP.0000000000000366", False),
                    ("Greifkraft (Relativ)", "handkraft_rel", "kg/kg", "handkraft_rel.png",
                     "Maximale Handkraft im Verhältnis zum Körpergewicht. Methodischer Hinweis: Messung der maximalen isometrischen Kraft mittels standardisiertem Hand-Dynamometer.",
                     "Ref: Bohannon et al. (2017), populationsbasierte Normwerte aus dem NIH Toolbox Projekt (n=2'706). | DOI: 10.1097/PEP.0000000000000366", False),
                    ("Sprunghöhe", "sprung", "cm", "sprung_abs.png",
                     "Zeigt die Explosivität, Beinkraft und koordinative Schnellkraft. "
                     "Methodischer Hinweis: Da die Referenzdaten ursprünglich mit Armschwung erhoben wurden, "
                     "unsere Messung jedoch ohne Armeinsatz stattfand, wurden die Normkurven um einen pauschalen "
                     "Korrekturfaktor angepasst, um einen fairen Vergleich zu ermöglichen.",
                     "Ref: Šumník et al. (2013), Tschechien, gesunde Kinder und Jugendliche. | PMID: 23989251", False),
                    ("Max. Sprungpower", "sprung_rel", "W/kg", "sprung_rel.png",
                     "Zeigt die maximale mechanische Leistung/Beschleunigung der Beinmuskulatur (Power) pro kg Körpergewicht während des Sprungs. "
                     "Methodischer Hinweis: Da die Referenzdaten ursprünglich mit Armschwung erhoben wurden, "
                     "unsere Messung jedoch ohne Armeinsatz stattfand, wurden die Normkurven um einen pauschalen "
                     "Korrekturfaktor angepasst, um einen fairen Vergleich zu ermöglichen.",
                     "Ref: Šumník et al. (2013), Tschechien, gesunde Kinder und Jugendliche. | PMID: 23989251", False),
                    ("Isom. Kreuzheben (Absolut)", "kreuzheben", "kg", "kreuzheben_abs.png",
                     "Misst die statische Maximalkraft des gesamten Körpers beim Kreuzheben. Achtung: Verglichen mit NachwuchsathletInnen!",
                     "Ref: Morris et al. (2020) Knaben & Salter et al. (2025) Mädchen (Athleten-Norm!). | DOI: 10.1519/JSC.0000000000002673 & 10.1519/JSC.0000000000005029", False),
                    ("Isom. Kreuzheben (Relativ)", "kreuzheben_rel", "kg/kg", "kreuzheben_rel.png",
                     "Statische Maximalkraft des Körpers im Verhältnis zum Körpergewicht. Achtung: Verglichen mit NachwuchsathletInnen!",
                     "Ref: Morris et al. (2020) Knaben & Salter et al. (2025) Mädchen (Athleten-Norm!). | DOI: 10.1519/JSC.0000000000002673 & 10.1519/JSC.0000000000005029", False),
                    ("Beinstreckkraft (Absolut)", "beinstrecker", "Nm", "beinstrecker_abs.png",
                     "Zeigt die isolierte, absolute Kraft der vorderen Oberschenkelmuskulatur (Drehmoment).",
                     "Ref: Hébert et al. (2015), Kanada, gesunde Kinder und Jugendliche. | DOI: 10.1097/PEP.0000000000000179", False),
                    ("Beinstreckkraft (Relativ)", "beinstrecker_rel", "Nm/kg", "beinstrecker_rel.png",
                     "Isolierte Oberschenkelkraft im Verhältnis zum Körpergewicht.",
                     "Ref: Hébert et al. (2015), Kanada, gesunde Kinder und Jugendliche. | DOI: 10.1097/PEP.0000000000000179", False)
                ]),
                ("Spiroergometrie", [
                    ("Ausdauer (VO2max)", "vo2max", "mL/kg/min", "vo2max_abs.png",
                     "Die VO2max gilt als der 'Goldstandard' zur Bestimmung der Herz-Kreislauf-Fitness. Sie misst, "
                     "wie viel Sauerstoff dein Körper unter maximaler Belastung aufnehmen, in den Blutkreislauf transportieren "
                     "und in die Muskeln weiterleiten kann, um Energie zu erzeugen. Da dieser Wert relativ zum Körpergewicht gemessen wird "
                     "(in ml pro kg Körpergewicht pro Minute), ermöglicht er einen fairen Vergleich der Leistungsfähigkeit unabhängig von der individuellen Körpermasse.",
                     "Ref: Takken et al. (2017), Niederlande, gesunde Kinder und Jugendliche (SentrySuite). | DOI: 10.1513/AnnalsATS.201611-912FR", False),
                    ("Max. Leistung Ergometer", "leistung", "Watt", "leistung_abs.png",
                     "Maximale mechanische Ausdauer-Leistung auf dem Fahrrad-Ergometer.",
                     "Ref: Takken et al. (2017), Niederlande, gesunde Kinder und Jugendliche (SentrySuite). | DOI: 10.1513/AnnalsATS.201611-912FR", False)
                ])
            ],
            'en': [
                ("Anthropometrie", [
                    ("Body Height", "groesse", "cm", "groesse_abs.png",
                     "Shows height development compared to the age-appropriate norm.",
                     "Ref: Kromeyer-Hauschild et al. (2001), Germany, healthy children. | DOI: 10.1007/s001120170107", False),
                    ("Body Weight", "gewicht", "kg", "gewicht_abs.png",
                     "Shows weight development compared to the age-appropriate norm.",
                     "Ref: Kromeyer-Hauschild et al. (2001), Germany, healthy children. | DOI: 10.1007/s001120170107", False)
                ]),
                ("Kraftmessungen", [
                    ("Grip Strength (Absolute)", "handkraft", "kg", "handkraft_abs.png",
                     "Indicator of general upper-body strength (dominant hand). Methodological note: Maximum isometric force measured with a standardised hand dynamometer.",
                     "Ref: Bohannon et al. (2017), population-based norms from the NIH Toolbox Project (n=2,706). | DOI: 10.1097/PEP.0000000000000366", False),
                    ("Grip Strength (Relative)", "handkraft_rel", "kg/kg", "handkraft_rel.png",
                     "Maximum grip strength relative to body weight. Methodological note: Maximum isometric force measured with a standardised hand dynamometer.",
                     "Ref: Bohannon et al. (2017), population-based norms from the NIH Toolbox Project (n=2,706). | DOI: 10.1097/PEP.0000000000000366", False),
                    ("Jump Height", "sprung", "cm", "sprung_abs.png",
                     "Reflects explosive power, leg strength and coordinative speed-strength. "
                     "Methodological note: Since the reference data were originally collected with arm swing, "
                     "but our measurement was performed without arm use, the normative curves were adjusted by a flat "
                     "correction factor to allow for a fair comparison.",
                     "Ref: Šumník et al. (2013), Czech Republic, healthy children and adolescents. | PMID: 23989251", False),
                    ("Max. Jump Power", "sprung_rel", "W/kg", "sprung_rel.png",
                     "Shows the maximum mechanical power output of the leg muscles (power) per kg of body weight during the jump. "
                     "Methodological note: Since the reference data were originally collected with arm swing, "
                     "but our measurement was performed without arm use, the normative curves were adjusted by a flat "
                     "correction factor to allow for a fair comparison.",
                     "Ref: Šumník et al. (2013), Czech Republic, healthy children and adolescents. | PMID: 23989251", False),
                    ("Isom. Deadlift (Absolute)", "kreuzheben", "kg", "kreuzheben_abs.png",
                     "Measures static whole-body strength. Note: Compared with youth athletes!",
                     "Ref: Morris et al. (2020) Boys & Salter et al. (2025) Girls (Athlete Norm!). | DOI: 10.1519/JSC.0000000000002673 & 10.1519/JSC.0000000000005029", False),
                    ("Isom. Deadlift (Relative)", "kreuzheben_rel", "kg/kg", "kreuzheben_rel.png",
                     "Static whole-body strength relative to body weight. Note: Compared with youth athletes!",
                     "Ref: Morris et al. (2020) Boys & Salter et al. (2025) Girls (Athlete Norm!). | DOI: 10.1519/JSC.0000000000002673 & 10.1519/JSC.0000000000005029", False),
                    ("Leg Extension Strength (Absolute)", "beinstrecker", "Nm", "beinstrecker_abs.png",
                     "Shows isolated absolute strength of the quadriceps (torque).",
                     "Ref: Hébert et al. (2015), Canada, healthy children and adolescents. | DOI: 10.1097/PEP.0000000000000179", False),
                    ("Leg Extension Strength (Relative)", "beinstrecker_rel", "Nm/kg", "beinstrecker_rel.png",
                     "Isolated quadriceps strength relative to body weight.",
                     "Ref: Hébert et al. (2015), Canada, healthy children and adolescents. | DOI: 10.1097/PEP.0000000000000179", False)
                ]),
                ("Spiroergometrie", [
                    ("Cardiorespiratory Fitness (VO2max)", "vo2max", "mL/kg/min", "vo2max_abs.png",
                     "VO2max is considered the 'gold standard' for determining cardiorespiratory fitness. It measures "
                     "how much oxygen your body can take in under maximal exertion, transport into the bloodstream, "
                     "and deliver to the muscles to produce energy. Because this value is measured relative to body weight "
                     "(in ml per kg of body weight per minute), it allows for a fair comparison of performance independent of individual body mass.",
                     "Ref: Takken et al. (2017), Netherlands, healthy children and adolescents (SentrySuite). | DOI: 10.1513/AnnalsATS.201611-912FR", False),
                    ("Max. Power Output (Ergometer)", "leistung", "Watts", "leistung_abs.png",
                     "Maximum mechanical endurance power output on the cycle ergometer.",
                     "Ref: Takken et al. (2017), Netherlands, healthy children and adolescents (SentrySuite). | DOI: 10.1513/AnnalsATS.201611-912FR", False)
                ])
            ]
        }
        self.report_structure = _rs.get(lang, _rs['de'])

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
            textColor=UNIBAS_ANTHRAZIT_HELL, alignment=TA_LEFT, spaceAfter=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader', parent=self.styles['Heading2'], 
            fontName='Times-Bold', fontSize=14, leading=16, 
            textColor=UNIBAS_ANTHRAZIT, backColor=UNIBAS_MINT, 
            borderPadding=(6, 4, 6, 4), alignment=TA_LEFT, spaceBefore=5, spaceAfter=4,
            keepWithNext=True
        ))
        
        self.styles.add(ParagraphStyle(name='MetricLabel', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=UNIBAS_ANTHRAZIT))
        self.styles.add(ParagraphStyle(name='MetricValue', parent=self.styles['Normal'], fontName='Helvetica', fontSize=10, leading=12, textColor=UNIBAS_ANTHRAZIT))
        self.styles.add(ParagraphStyle(name='MetricChange', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12))
        
        # --- NEUE STYLES FÜR ERKLÄRUNGEN UND REFERENZEN ---
        self.styles.add(ParagraphStyle(name='ExplanationSmall', parent=self.styles['Normal'], fontName='Helvetica-Oblique', fontSize=9, leading=12, textColor=UNIBAS_ANTHRAZIT, spaceBefore=5))
        self.styles.add(ParagraphStyle(name='ReferenceNormal', parent=self.styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10, textColor=UNIBAS_ANTHRAZIT_HELL, spaceBefore=2))
        self.styles.add(ParagraphStyle(name='ReferenceDummy', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=UNIBAS_ROT, spaceBefore=2))
        self.styles.add(ParagraphStyle(name='MaturityWarning', parent=self.styles['Normal'], fontName='Helvetica-BoldOblique', fontSize=8.5, leading=12, textColor=UNIBAS_ROT, spaceBefore=6))
        
        # --- STYLE FÜR IMPRESSUM ---
        self.styles.add(ParagraphStyle(name='Impressum', parent=self.styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=UNIBAS_ANTHRAZIT_HELL))

        # --- STYLES FÜR INTRO-SEITE ---
        self.styles.add(ParagraphStyle(
            name='IntroHeader', parent=self.styles['Heading2'], 
            fontName='Times-Bold', fontSize=14, leading=16, 
            textColor=UNIBAS_ANTHRAZIT, alignment=TA_LEFT, spaceBefore=5, spaceAfter=10,
            keepWithNext=True
        ))
        self.styles.add(ParagraphStyle(
            name='IntroBegruessung', parent=self.styles['Normal'],
            fontName='Helvetica', fontSize=10, leading=15,
            textColor=UNIBAS_ANTHRAZIT, spaceBefore=8, spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name='IntroBody', parent=self.styles['Normal'],
            fontName='Helvetica', fontSize=9.5, leading=14,
            textColor=UNIBAS_ANTHRAZIT, spaceBefore=5, spaceAfter=8
        ))

    def _create_header(self, patient_info):
        elements = []
        title = Paragraph("<para align=center>DECADE Report</para>", self.styles['ReportTitle'])
        subtitle_text = self._t['report_subtitle']
        subtitle = Paragraph(f"<para align=center>{subtitle_text}</para>", self.styles['ReportSubTitle'])
        
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
        p_sex = self._t['sex_female'] if p_sex_raw == 'girls' else self._t['sex_male'] if p_sex_raw == 'boys' else "-"

        p_data = [[f"{self._t['patient_id']}: {p_id}", f"{self._t['sex_label']}: {p_sex}", f"{self._t['date_label']}: {p_date}"]]
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
        elements.append(Spacer(1, 0.5*cm))
        return elements

    def _create_metric_table(self, label, metric_data, unit=""):
        if not metric_data:
            metric_data = {'pre': '-', 'post': '-', 'diff': None}

        t = self._t  # language labels
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
            Paragraph(f"{t['start']}: {old_val} {unit}", self.styles['MetricValue']),
            Paragraph(f"{t['current']}: <b>{new_val} {unit}</b>", self.styles['MetricValue']),
            Paragraph(f"{t['diff']}: {change_str}", style_change)
        ]]
        
        tbl = Table(data, colWidths=[6.5*cm, 4*cm, 4*cm, 3.5*cm])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, UNIBAS_MINT_HELL)
        ]))
        return tbl

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
        t = self._t  # language labels

        # 1. Zusammenfassung (Farbig) - 2x2 Layout für mehr Platz
        summary_data = [
            [
                Paragraph(f"{t['mat_eff_age']}: <b>{chron_age:.1f} {t['mat_years']}</b>", self.styles['MetricLabel']),
                Paragraph(f"{t['mat_bio_age']}: <b>{bio_age:.1f} {t['mat_years']}</b>", self.styles['MetricLabel'])
            ],
            [
                Paragraph(f"{t['mat_diff_bio_eff']}: <b>{dev_age:+.1f} {t['mat_years']}</b>", self.styles['MetricLabel']),
                Paragraph(f"{t['mat_diff_phv']}: <b>{offset:+.1f} {t['mat_years']}</b>", self.styles['MetricLabel'])
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
        
        elements.append(KeepTogether([
            Paragraph(t['mat_heading'], self.styles['SectionHeader']),
            t_sum
        ]))
        elements.append(Spacer(1, 0.3*cm))

        # 2. Historie-Tabelle
        header = [t['mat_col_mzp'], t['mat_col_date'], t['mat_col_eff'], t['mat_col_bio']]
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
                f"{entry['chron_age']:.1f} {t['mat_years']}",
                f"{entry['bio_age']:.1f} {t['mat_years']}"
            ])

        # Nächste Messung als extra Zeile
        next_text = t['mat_next_default']
        d_str = latest.get('date')
        if d_str and str(d_str) not in ('-', 'nan', 'None'):
            try:
                import pandas as pd
                last_date_dt = pd.to_datetime(d_str, errors='coerce')
                if pd.notna(last_date_dt):
                    next_date = last_date_dt + timedelta(days=304)
                    if self.lang == 'en':
                        import calendar
                        month_name = calendar.month_name[next_date.month]
                    else:
                        month_name = self._get_german_month(next_date.month)
                    next_text = t['mat_next_text'].format(month=month_name, year=next_date.year)
            except Exception:
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
            
        doi_link = '10.1249/00005768-200204000-00020'
        info_text = t['mat_info'].format(doi=doi_link)
        elements.append(Paragraph(info_text, self.styles['ExplanationSmall']))
        elements.append(Paragraph(t['mat_warning'], self.styles['MaturityWarning']))
        elements.append(Spacer(1, 0.2*cm))
        return elements

    def _create_body_composition_block(self, patient_meta, metrics_data, plot_dict):
        """
        Erstellt den Körperzusammensetzungs-Abschnitt abhängig von der Messmethode:
        - 'dxa':    Körperfettanteil + Knochendichte (beide mit DXA-Referenz)
        - 'inbody': Nur Körperfettanteil (InBody-Referenz, mit Hinweis)
        - 'other'/None: Kein Abschnitt
        """
        bodycomp_method = patient_meta.get('bodycomp_method')
        if bodycomp_method not in ('dxa', 'inbody'):
            return []

        t = self._t
        elements = []
        elements.append(PageBreak())
        
        # Methoden-Hinweis im Titel
        method_name = "DXA" if bodycomp_method == 'dxa' else "InBody"
        heading_text = f"{t['bodycomp_heading']} ({method_name})"
        elements.append(Paragraph(heading_text, self.styles['SectionHeader']))
        
        elements.append(Spacer(1, 0.2*cm))

        # --- Körperfettanteil ---
        koerperfett_data = metrics_data.get('koerperfett')
        fat_block = []
        fat_block.append(self._create_metric_table(t['koerperfett_label'], koerperfett_data, '%'))
        fat_block.append(Spacer(1, 0.2*cm))

        if bodycomp_method == 'dxa':
            fat_plot_name = 'koerperfett_dxa_abs.png'
            fat_expl = t['koerperfett_dxa_expl']
            fat_ref  = t['koerperfett_dxa_ref']
            ref_style = self.styles['ReferenceNormal']
        else:
            fat_plot_name = 'koerperfett_inbody_abs.png'
            fat_expl = t['koerperfett_inbody_expl']
            fat_ref  = t['koerperfett_inbody_ref']
            ref_style = self.styles['ReferenceNormal']  # Chun et al. 2024 – vollständige altersaufgelöste Norm

        fat_plot_path = plot_dict.get(fat_plot_name)
        if fat_plot_path and os.path.exists(fat_plot_path):
            fat_block.append(self._build_plot_with_icon('koerperfett', fat_plot_path))
        fat_block.append(Paragraph(fat_expl, self.styles['ExplanationSmall']))
        fat_block.append(Paragraph(fat_ref, ref_style))
        fat_block.append(Spacer(1, 0.2*cm))
        elements.append(KeepTogether(fat_block))

        # --- Knochendichte (nur bei DXA) ---
        if bodycomp_method == 'dxa':
            bmd_data = metrics_data.get('knochendichte')
            bmd_block = []
            bmd_block.append(self._create_metric_table(t['knochendichte_label'], bmd_data, 'g/cm²'))
            bmd_block.append(Spacer(1, 0.2*cm))

            bmd_plot_path = plot_dict.get('knochendichte_abs.png')
            if bmd_plot_path and os.path.exists(bmd_plot_path):
                bmd_block.append(self._build_plot_with_icon('knochendichte', bmd_plot_path))
            bmd_block.append(Paragraph(t['knochendichte_expl'], self.styles['ExplanationSmall']))
            bmd_block.append(Paragraph(t['knochendichte_ref'], self.styles['ReferenceNormal']))
            bmd_block.append(Spacer(1, 0.2*cm))
            elements.append(KeepTogether(bmd_block))

        return elements

    def _build_plot_with_icon(self, metric_key, plot_path):
        """Gibt ein Table-Element zurück: links das Icon (falls vorhanden), rechts der Graph."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, '..', 'data', 'icons', f'{metric_key}.png')

        graph_img = Image(plot_path, width=12*cm, height=7.5*cm)

        if os.path.exists(icon_path):
            icon_img = Image(icon_path, width=2.5*cm, height=2.5*cm, kind='proportional')
            row = [[icon_img, graph_img]]
            tbl = Table(row, colWidths=[3*cm, 15*cm])
            tbl.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN',  (0, 0), (0, 0),  'CENTER'),
                ('LEFTPADDING',  (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            return tbl
        else:
            return graph_img

    def _create_impressum(self):
        """Erstellt den Impressum-Block als Liste von Flowables."""
        elements = []
        elements.append(Spacer(1, 0.8*cm))
        elements.append(Paragraph(self._t['contact_heading'], self.styles['SectionHeader']))

        impressum_text_left = (
            "<br/>"
            "<b>DECADE Studie:</b> <a href=\"https://decade.dsbg.unibas.ch/de/\" color=\"blue\">https://decade.dsbg.unibas.ch/de/</a><br/>"
            "<b>Leitung:</b> Romina Ledergerber &amp; Ralf Roth<br/>"
            "<b>Kontakt:</b> <a href=\"mailto:romina.ledergerber@unibas.ch\" color=\"blue\">romina.ledergerber@unibas.ch</a> | +41 61 207 47 73"
        )
        impressum_text_right = (
            "<br/>"
            "<b>Adresse:</b><br/>"
            "Departement für Sport, Bewegung und Gesundheit<br/>"
            "Grosse Allee 6, 4052 Basel, Schweiz"
        )

        p_left  = Paragraph(impressum_text_left,  self.styles['Impressum'])
        p_right = Paragraph(impressum_text_right, self.styles['Impressum'])

        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path  = os.path.join(script_dir, '..', 'data', 'decade_logo.jpg')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(script_dir, '..', 'data', 'decade_logo.png')

        img_impressum = ""
        if os.path.exists(logo_path):
            img_impressum = Image(logo_path, width=4.5*cm, height=1.8*cm, kind='proportional')

        table = Table([["", p_left, p_right, img_impressum]], colWidths=[0.21*cm, 8*cm, 6.5*cm, 3.29*cm])
        table.setStyle(TableStyle([
            ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
            ('ALIGN',        (3, 0), (3, 0),   'RIGHT'),
            ('LEFTPADDING',  (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(table)
        return elements

    def _create_intro_page(self, patient_meta):
        """Erstellt die Einführungsseite (Seite 1) des Reports."""
        elements = []

        # 1. Header (Logos + Patienten-Tabelle)
        elements.extend(self._create_header(patient_meta))

        # 2. Begrüssungstext
        elements.append(Paragraph(self._t['begruessung'], self.styles['IntroBegruessung']))

        # 3. Abschnitt: Wie lese ich die Grafiken?
        elements.append(Paragraph(self._t['intro_h1'], self.styles['IntroHeader']))
        elements.append(Paragraph(self._t['intro_grafik'], self.styles['IntroBody']))

        # Platzhalter-Bild für das Grafik-Guide
        script_dir = os.path.dirname(os.path.abspath(__file__))
        guide_img_path = os.path.join(script_dir, '..', 'data', 'report_guide.png')
        if os.path.exists(guide_img_path):
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Image(guide_img_path, width=12*cm, height=7*cm))
            elements.append(Spacer(1, 0.3*cm))

        # 4. Abschnitt: Absolute vs. Relative Werte
        elements.append(Paragraph(self._t['intro_h2'], self.styles['IntroHeader']))
        elements.append(Paragraph(self._t['intro_relativ'], self.styles['IntroBody']))

        # 5. Abschnitt: Hinweise zur Aussagekraft
        elements.append(Paragraph(self._t['intro_h3'], self.styles['IntroHeader']))
        elements.append(Paragraph(self._t['intro_hinweis'], self.styles['IntroBody']))

        return elements

    def build_report(self, metrics, plot_files):
        doc = SimpleDocTemplate(
            self.out_file, pagesize=A4,
            rightMargin=1.5*cm, leftMargin=1.5*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm
        )
        story = []

        patient_meta = metrics.get("meta", {})

        # --- SEITE 1: Einführungsseite ---
        story.extend(self._create_intro_page(patient_meta))

        plot_dict = {os.path.basename(p): p for p in plot_files}

        for i, (section_title, metric_list) in enumerate(self.report_structure):
            if i > 0:
                story.append(PageBreak())

            # Sprachabhängigen Sektionstitel ausgeben
            display_section = self._section_title_map.get(section_title, section_title)
            story.append(Paragraph(display_section, self.styles['SectionHeader']))

            # Erklärung, Referenz und is_dummy beim Entpacken auslesen
            for display_name, metric_key, unit, expected_plot_name, explanation, reference, is_dummy in metric_list:
                metric_data = metrics.get(metric_key)
                block = []

                # 1. Die Wertetabelle
                block.append(self._create_metric_table(display_name, metric_data, unit))

                # 2. Das Bild (falls vorhanden) — mit optionalem Icon links daneben
                if expected_plot_name:
                    block.append(Spacer(1, 0.2*cm))
                    plot_path = plot_dict.get(expected_plot_name)
                    if plot_path and os.path.exists(plot_path):
                        block.append(self._build_plot_with_icon(metric_key, plot_path))

                # 3. Die Erklärung unter der Tabelle/dem Bild
                if explanation:
                    block.append(Paragraph(explanation, self.styles['ExplanationSmall']))

                # 4. Die Referenz-Infos (Mit Schalter für Rote Dummy-Daten)
                if reference:
                    ref_style = self.styles['ReferenceDummy'] if is_dummy else self.styles['ReferenceNormal']
                    block.append(Paragraph(reference, ref_style))

                block.append(Spacer(1, 0.2*cm))
                story.append(KeepTogether(block))

            # Maturity Block nach der Anthropometrie (erste Sektion)
            if section_title == "Anthropometrie":
                story.extend(self._create_body_composition_block(patient_meta, metrics, plot_dict))
                story.append(PageBreak())
                story.extend(self._create_maturity_block(patient_meta, plot_dict))

        # --- IMPRESSUM AM ENDE ---
        story.append(KeepTogether(self._create_impressum()))

        doc.build(story)
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from reference_data import (
    get_pmax_mass_reference, get_vo2max_reference, PMAX_ABS_DATA,
    MTP_REL_DATA, MTP_ABS_DATA, KNEE_EXT_ABS_HEBERT, KNEE_EXT_REL_HEBERT, HANDGRIP_DOM_BOHANNON, get_relative_handgrip_bohannon, HEIGHT_DATA, WEIGHT_DATA,
    get_jump_height_reference, get_smoothed_reference
)

class Visualizer:
    def __init__(self, lang: str = 'de'):
        self.lang = lang
        self.colors = {
            'P97': '#cccccc', 'P90': '#cccccc', 'P75': '#888888',
            'P50': 'black',
            'P25': '#888888', 'P10': '#cccccc', 'P3': '#cccccc'
        }
        self.z_scores_lms = {
            'P97': 1.88, 'P90': 1.28, 'P75': 0.675, 'P50': 0.0,
            'P25': -0.675, 'P10': -1.28, 'P3': -1.88
        }
        _labels = {
            'de': {
                'girls':            'Mädchen',
                'boys':             'Jungs',
                'age_axis':         'Alter [Jahre]',
                'you':              'Du',
                'your_maturity':    'Dein Reifegrad',
                # plot titles
                'sprung_title':         'Sprunghöhe',
                'sprung_ylabel':        'Sprunghöhe (cm)',
                'sprung_rel_title':     'Max. Sprungpower',
                'sprung_rel_ylabel':    'Power (W/kg)',
                'vo2max_title':         'Ausdauer (VO2max)',
                'vo2max_ylabel':        'Sauerstoff (mL/kg/min)',
                'leistung_title':       'Max. Leistung Ergometer',
                'leistung_ylabel':      'Leistung (Watt)',
                'kreuzheben_rel_title': 'Ganzkörperkraft (Relativ) [Athleten-Norm!]',
                'kreuzheben_rel_ylabel':'Kraft / Gewicht (kg/kg)',
                'beinstrecker_title':   'Max. Beinstreckkraft',
                'beinstrecker_ylabel':  'Kraft (Nm)',
                'beinstrecker_rel_title':  'Beinkraft Relativ',
                'beinstrecker_rel_ylabel': 'Kraft (Nm/kg)',
                'handkraft_title':      'Maximale Greifkraft der dominanten Hand (kg)',
                'handkraft_ylabel':     'Maximale Kraft [kg]',
                'handkraft_rel_title':  'Relative Greifkraft der dominanten Hand (kg/kg)',
                'handkraft_rel_ylabel': 'Kraft / Körpergewicht [kg/kg]',
                'kreuzheben_title':     'Isom. Kreuzheben (Absolut) [Athleten-Norm!]',
                'kreuzheben_ylabel':    'Kraft (kg)',
                'groesse_title':        'Körpergrösse',
                'groesse_ylabel':       'Grösse (cm)',
                'gewicht_title':        'Körpergewicht',
                'gewicht_ylabel':       'Gewicht (kg)',
                # maturity plot
                'mat_phv_label':    'Wachstumsschub (PHV)',
                'mat_status_in':    'Mitten im Schub',
                'mat_status_before':'Noch ca. {y:.1f} J. bis zum Schub',
                'mat_status_after': 'Schub vor ca. {y:.1f} J. erfolgt',
                'mat_title':        'Biologischer Reifegrad (Verlauf)',
                'mat_xlabel':       'Chronologisches Alter (Jahre)',
                'mat_ylabel':       'Jahre bis/seit dem Wachstumsschub',
                # overview suffix
                'all_suffix':       '\u2013 ALLE',
                'patients_legend':  'Patienten',
            },
            'en': {
                'girls':            'Girls',
                'boys':             'Boys',
                'age_axis':         'Age [Years]',
                'you':              'You',
                'your_maturity':    'Your Maturity',
                # plot titles
                'sprung_title':         'Jump Height',
                'sprung_ylabel':        'Jump Height (cm)',
                'sprung_rel_title':     'Max. Jump Power',
                'sprung_rel_ylabel':    'Power (W/kg)',
                'vo2max_title':         'Cardiorespiratory Fitness (VO2max)',
                'vo2max_ylabel':        'Oxygen (mL/kg/min)',
                'leistung_title':       'Max. Power Output (Ergometer)',
                'leistung_ylabel':      'Power (Watts)',
                'kreuzheben_rel_title': 'Whole-Body Strength (Relative) [Athlete Norm!]',
                'kreuzheben_rel_ylabel':'Force / Body Weight (kg/kg)',
                'beinstrecker_title':   'Max. Leg Extension Strength',
                'beinstrecker_ylabel':  'Force (Nm)',
                'beinstrecker_rel_title':  'Leg Strength (Relative)',
                'beinstrecker_rel_ylabel': 'Force (Nm/kg)',
                'handkraft_title':      'Max. Grip Strength – Dominant Hand (kg)',
                'handkraft_ylabel':     'Max. Force [kg]',
                'handkraft_rel_title':  'Relative Grip Strength – Dominant Hand (kg/kg)',
                'handkraft_rel_ylabel': 'Force / Body Weight [kg/kg]',
                'kreuzheben_title':     'Isom. Deadlift (Absolute) [Athlete Norm!]',
                'kreuzheben_ylabel':    'Force (kg)',
                'groesse_title':        'Body Height',
                'groesse_ylabel':       'Height (cm)',
                'gewicht_title':        'Body Weight',
                'gewicht_ylabel':       'Weight (kg)',
                # maturity plot
                'mat_phv_label':    'Growth Spurt (PHV)',
                'mat_status_in':    'Currently at Peak',
                'mat_status_before':'Approx. {y:.1f} yrs until growth spurt',
                'mat_status_after': 'Growth spurt approx. {y:.1f} yrs ago',
                'mat_title':        'Biological Maturity (Trend)',
                'mat_xlabel':       'Chronological Age (Years)',
                'mat_ylabel':       'Years before/after Growth Spurt',
                # overview suffix
                'all_suffix':       '\u2013 ALL',
                'patients_legend':  'Patients',
            },
        }
        self._vt = _labels.get(lang, _labels['de'])

    def _calc_lms(self, l, m, s, z):
        """LMS Formel: L=0 -> Log-Normal (Exp), sonst Standard-Box-Cox"""
        if l == 0:
            return m * np.exp(s * z)
        else:
            return m * ((1 + l * s * z) ** (1/l))

    def create_reference_plot(self, metric_type, history_data, sex, output_path, patient_weight=None):
        plt.figure(figsize=(6, 4))
        # Höhere Auflösung für glatte Kurven
        ages = np.linspace(6, 18, 100)
        percentiles_data = {p: [] for p in self.colors.keys()}


        
        # --- REFERENZDATEN LADEN JE NACH METRIK ---
        vt = self._vt
        sex_label = vt['girls'] if sex == 'girls' else vt['boys']

        if metric_type == 'sprung':
            title = f"{vt['sprung_title']} ({sex_label})"
            ylabel = vt['sprung_ylabel']
            for age in ages:
                refs = get_jump_height_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        elif metric_type == 'sprung_rel':
            title = f"{vt['sprung_rel_title']} ({sex_label})"
            ylabel = vt['sprung_rel_ylabel']
            for age in ages:
                refs = get_pmax_mass_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        elif metric_type == 'vo2max':
            title = f"{vt['vo2max_title']} ({sex_label})"
            ylabel = vt['vo2max_ylabel']
            for age in ages:
                refs = get_vo2max_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])
                
        elif metric_type == 'leistung':
            title = f"{vt['leistung_title']} ({sex_label})"
            ylabel = vt['leistung_ylabel']
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, PMAX_ABS_DATA)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'kreuzheben_rel':
            title = vt['kreuzheben_rel_title']
            ylabel = vt['kreuzheben_rel_ylabel']
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, MTP_REL_DATA)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'beinstrecker':
            title = f"{vt['beinstrecker_title']} ({sex_label})"
            ylabel = vt['beinstrecker_ylabel']
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, KNEE_EXT_ABS_HEBERT)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])
                    
        elif metric_type == 'beinstrecker_rel':
            title = f"{vt['beinstrecker_rel_title']} ({sex_label})"
            ylabel = vt['beinstrecker_rel_ylabel']
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, KNEE_EXT_REL_HEBERT)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])
                    
        elif metric_type == 'handkraft':
            title = vt['handkraft_title']
            ylabel = vt['handkraft_ylabel']
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, HANDGRIP_DOM_BOHANNON)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])
                    
        elif metric_type == 'handkraft_rel':
            title = vt['handkraft_rel_title']
            ylabel = vt['handkraft_rel_ylabel']
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                w = patient_weight if patient_weight and patient_weight > 0 else 50.0
                vals = get_relative_handgrip_bohannon(age, sex, w)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'kreuzheben':
            title = vt['kreuzheben_title']
            ylabel = vt['kreuzheben_ylabel']
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, MTP_ABS_DATA)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'groesse':
            title = f"{vt['groesse_title']} ({sex_label})"
            ylabel = vt['groesse_ylabel']
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, HEIGHT_DATA)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'gewicht':
            title = f"{vt['gewicht_title']} ({sex_label})"
            ylabel = vt['gewicht_ylabel']
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, WEIGHT_DATA)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        # --- ZEICHNEN DER REFERENZKURVEN ---
        for p_name in ['P3', 'P10', 'P25', 'P75', 'P90', 'P97', 'P50']:
            y_vals = percentiles_data[p_name]
            if not y_vals: continue # Überspringe, wenn für diese Perzentile keine Daten vorliegen
            width = 2 if p_name == 'P50' else 1
            style = '-' if p_name == 'P50' else '--'
            plt.plot(ages, y_vals, color=self.colors[p_name], linestyle=style, linewidth=width)
            if len(y_vals) > 0 and not np.isnan(y_vals[-1]):
                plt.text(ages[-1] + 0.2, y_vals[-1], p_name, fontsize=7, color=self.colors[p_name], va='center')

        # --- ZEICHNEN DER PATIENTENHISTORIE ---
        if history_data and len(history_data) > 0:
            p_ages, p_vals = zip(*history_data)

            plt.plot(p_ages, p_vals, color='red', linestyle='-', linewidth=2, alpha=0.7, zorder=9)
            plt.plot(p_ages[:-1], p_vals[:-1], 'ro', markersize=5, zorder=9)
            
            last_age, last_val = p_ages[-1], p_vals[-1]
            plt.plot(last_age, last_val, 'ro', markersize=9, zorder=10)
            plt.text(last_age, last_val + (last_val*0.05), vt['you'], color='red', fontweight='bold', ha='center', zorder=11)

        plt.title(title)
        plt.xlabel(vt['age_axis'])
        plt.ylabel(ylabel)
        plt.grid(True, which='both', linestyle=':', alpha=0.6)
        plt.xlim(5.5, 19.5)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
    def create_maturity_plot(self, history, sex, output_path):
        """Erstellt eine Visualisierung für den Reifegrad-Verlauf (Mirwald)."""
        vt = self._vt
        plt.figure(figsize=(6, 3.5))
        
        # Horizontaler Bereich für PHV
        plt.axhline(0, color='green', linestyle='--', alpha=0.5, linewidth=2)
        plt.fill_between([5, 20], -0.5, 0.5, color='green', alpha=0.1) # Peak-Bereich
        
        # Achsen-Limits
        if history:
            if isinstance(history[0], dict):
                all_ages = [h['chron_age'] for h in history]
            else:
                all_ages = [h[0] for h in history]
        else:
            all_ages = [6, 18]
        plt.xlim(min(all_ages)-1, max(all_ages)+1)
        plt.ylim(-4, 4)

        plt.text(plt.xlim()[0] + 0.5, 0.6, vt['mat_phv_label'], ha='left', color='green', fontsize=9, fontweight='bold')
        
        if history:
            if isinstance(history[0], dict):
                ages = [h['chron_age'] for h in history]
                offsets = [h['offset'] for h in history]
            else:
                ages, offsets = zip(*history)
                
            plt.plot(ages, offsets, 'ro-', linewidth=2, markersize=6, label=vt['your_maturity'])
            # Letzten Punkt hervorheben
            plt.plot(ages[-1], offsets[-1], 'ro', markersize=10, markeredgecolor='white')
            
            # Aktueller Status Text
            curr_off = offsets[-1]
            if abs(curr_off) < 0.5:
                status = vt['mat_status_in']
            elif curr_off < 0:
                status = vt['mat_status_before'].format(y=abs(curr_off))
            else:
                status = vt['mat_status_after'].format(y=curr_off)
            
            plt.annotate(status, xy=(ages[-1], offsets[-1]), xytext=(0, 20),
                         textcoords='offset points', ha='center', 
                         bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='red', alpha=0.8),
                         fontsize=8, color='red', fontweight='bold')

        plt.title(vt['mat_title'], fontsize=11, fontweight='bold')
        plt.xlabel(vt['mat_xlabel'], fontsize=9)
        plt.ylabel(vt['mat_ylabel'], fontsize=9)
        plt.grid(True, linestyle=':', alpha=0.6)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()

    def create_overview_plot(self, metric_type, all_patients_histories, sex, output_path):
        """
        Zeichnet einen Übersichts-Plot mit Referenzkurven und den Verläufen
        ALLER übergebenen Patienten auf einem Graphen.

        Args:
            metric_type:            Metrischer Schlüssel (z.B. 'groesse', 'vo2max')
            all_patients_histories: Liste von Tupeln (patient_id, history_data, patient_weight)
            sex:                    'girls' oder 'boys'
            output_path:            Zieldateipfad
        """
        patient_colors = [
            '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
            '#42d4f4', '#f032e6', '#bfef45', '#469990', '#dcbeff',
            '#9A6324', '#800000', '#aaffc3', '#808000', '#000075',
            '#a9a9a9', '#000000', '#ffd8b1', '#fabed4', '#fffac8',
        ]
        vt = self._vt

        fig, ax = plt.subplots(figsize=(10, 6))
        ages = np.linspace(6, 18, 100)
        percentiles_data = {p: [] for p in self.colors.keys()}
        p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']

        sex_label = vt['girls'] if sex == 'girls' else vt['boys']
        all_sfx = vt['all_suffix']
        ylabel = ""

        if metric_type == 'sprung':
            title, ylabel = f"{vt['sprung_title']} {all_sfx} ({sex_label})", vt['sprung_ylabel']
            for age in ages:
                refs = get_jump_height_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        elif metric_type == 'sprung_rel':
            title, ylabel = f"{vt['sprung_rel_title']}/kg {all_sfx} ({sex_label})", vt['sprung_rel_ylabel']
            for age in ages:
                refs = get_pmax_mass_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        elif metric_type == 'vo2max':
            title, ylabel = f"VO2max {all_sfx} ({sex_label})", vt['vo2max_ylabel']
            for age in ages:
                refs = get_vo2max_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        elif metric_type == 'leistung':
            title, ylabel = f"{vt['leistung_title']} {all_sfx} ({sex_label})", vt['leistung_ylabel']
            for age in ages:
                vals = get_smoothed_reference(age, sex, PMAX_ABS_DATA)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'kreuzheben_rel':
            title, ylabel = f"{vt['kreuzheben_rel_title']} {all_sfx}", vt['kreuzheben_rel_ylabel']
            for age in ages:
                vals = get_smoothed_reference(age, sex, MTP_REL_DATA)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'beinstrecker':
            title, ylabel = f"{vt['beinstrecker_title']} {all_sfx} ({sex_label})", vt['beinstrecker_ylabel']
            for age in ages:
                vals = get_smoothed_reference(age, sex, KNEE_EXT_ABS_HEBERT)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'beinstrecker_rel':
            title, ylabel = f"{vt['beinstrecker_rel_title']} {all_sfx} ({sex_label})", vt['beinstrecker_rel_ylabel']
            for age in ages:
                vals = get_smoothed_reference(age, sex, KNEE_EXT_REL_HEBERT)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'handkraft':
            title, ylabel = f"{vt['handkraft_title']} {all_sfx} ({sex_label})", vt['handkraft_ylabel']
            for age in ages:
                vals = get_smoothed_reference(age, sex, HANDGRIP_DOM_BOHANNON)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'handkraft_rel':
            title, ylabel = f"{vt['handkraft_rel_title']} {all_sfx} ({sex_label})", vt['handkraft_rel_ylabel']
            weights = [w for _, _, w in all_patients_histories if w and w > 0]
            avg_weight = float(np.mean(weights)) if weights else 40.0
            for age in ages:
                vals = get_relative_handgrip_bohannon(age, sex, avg_weight)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'kreuzheben':
            title, ylabel = f"{vt['kreuzheben_title']} {all_sfx}", vt['kreuzheben_ylabel']
            for age in ages:
                vals = get_smoothed_reference(age, sex, MTP_ABS_DATA)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'groesse':
            title, ylabel = f"{vt['groesse_title']} {all_sfx} ({sex_label})", vt['groesse_ylabel']
            for age in ages:
                vals = get_smoothed_reference(age, sex, HEIGHT_DATA)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'gewicht':
            title, ylabel = f"{vt['gewicht_title']} {all_sfx} ({sex_label})", vt['gewicht_ylabel']
            for age in ages:
                vals = get_smoothed_reference(age, sex, WEIGHT_DATA)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])
        else:
            plt.close(fig)
            return

        # Referenzkurven zeichnen
        for p_name in ['P3', 'P10', 'P25', 'P75', 'P90', 'P97', 'P50']:
            y_vals = percentiles_data[p_name]
            if not y_vals:
                continue
            width = 2 if p_name == 'P50' else 1
            style = '-' if p_name == 'P50' else '--'
            ax.plot(ages, y_vals, color=self.colors[p_name], linestyle=style,
                    linewidth=width, zorder=2)
            if not np.isnan(y_vals[-1]):
                ax.text(ages[-1] + 0.2, y_vals[-1], p_name, fontsize=7,
                        color=self.colors[p_name], va='center')

        # Alle Patientenlinien zeichnen
        for idx, (p_id, history, _weight) in enumerate(all_patients_histories):
            if not history:
                continue
            color = patient_colors[idx % len(patient_colors)]
            p_ages, p_vals = zip(*history)
            ax.plot(p_ages, p_vals, color=color, linestyle='-', linewidth=1.5,
                    alpha=0.85, zorder=5, label=str(p_id))
            ax.plot(p_ages[-1], p_vals[-1], 'o', color=color, markersize=6, zorder=6)

        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel(vt['age_axis'])
        ax.set_ylabel(ylabel)
        ax.grid(True, which='both', linestyle=':', alpha=0.5)
        ax.set_xlim(5.5, 19.5)

        if all_patients_histories:
            ax.legend(fontsize=7, loc='upper left', bbox_to_anchor=(1.01, 1),
                      borderaxespad=0, title=vt['patients_legend'], title_fontsize=8)

        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

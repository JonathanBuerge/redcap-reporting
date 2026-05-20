import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from reference_data import (
    get_pmax_mass_reference, get_vo2max_reference, PMAX_ABS_DATA,
    MTP_REL_DATA, MTP_ABS_DATA, KNEE_EXT_ABS_HEBERT, KNEE_EXT_REL_HEBERT, HANDGRIP_DOM_BOHANNON, get_relative_handgrip_bohannon, HEIGHT_DATA, WEIGHT_DATA,
    get_jump_height_reference, get_smoothed_reference
)

class Visualizer:
    def __init__(self):
        self.colors = {
            'P97': '#cccccc', 'P90': '#cccccc', 'P75': '#888888',
            'P50': 'black',
            'P25': '#888888', 'P10': '#cccccc', 'P3': '#cccccc'
        }
        self.z_scores_lms = {
            'P97': 1.88, 'P90': 1.28, 'P75': 0.675, 'P50': 0.0,
            'P25': -0.675, 'P10': -1.28, 'P3': -1.88
        }

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
        if metric_type == 'sprung':
            title = f"Sprunghöhe ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Sprunghöhe (cm)"
            for age in ages:
                refs = get_jump_height_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        elif metric_type == 'pmax_rel':
            title = f"Sprungkraft pro kg ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Leistung (W/kg)"
            for age in ages:
                refs = get_pmax_mass_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        elif metric_type == 'vo2max':
            title = f"Ausdauer (VO2max) ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Sauerstoff (mL/kg/min)"
            for age in ages:
                refs = get_vo2max_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])
                
        elif metric_type == 'leistung':
            title = f"Max. Leistung Ergometer ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Leistung (Watt)"
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, PMAX_ABS_DATA)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'mtp_rel':
            title = f"Ganzkörperkraft (Relativ) [Athleten-Norm!]"
            ylabel = "Kraft / Gewicht (kg/kg)"
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, MTP_REL_DATA)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'beinstrecker':
            title = f"Max. Beinstreckkraft ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Kraft (Nm)"
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, KNEE_EXT_ABS_HEBERT)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])
                    
        elif metric_type == 'leg_ext_rel':
            title = f"Beinkraft Relativ ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Kraft (Nm/kg)"
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, KNEE_EXT_REL_HEBERT)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])
                    
        elif metric_type == 'handkraft':
            title = f"Maximale Greifkraft der dominanten Hand (kg)"
            ylabel = "Maximale Kraft [kg]"
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, HANDGRIP_DOM_BOHANNON)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])
                    
        elif metric_type == 'handkraft_rel':
            title = f"Relative Greifkraft der dominanten Hand (kg/kg)"
            ylabel = "Kraft / Körpergewicht [kg/kg]"
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                # If patient_weight is provided, use it. Otherwise, default to something to avoid crashing (e.g., 50kg)
                w = patient_weight if patient_weight and patient_weight > 0 else 50.0
                vals = get_relative_handgrip_bohannon(age, sex, w)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'kreuzheben':
            title = f"Isom. Kreuzheben (Absolut) [Athleten-Norm!]"
            ylabel = "Kraft (kg)"
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, MTP_ABS_DATA)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'groesse':
            title = f"Körpergrösse ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Grösse (cm)"
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_smoothed_reference(age, sex, HEIGHT_DATA)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'gewicht':
            title = f"Körpergewicht ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Gewicht (kg)"
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
            plt.text(last_age, last_val + (last_val*0.05), "Du", color='red', fontweight='bold', ha='center', zorder=11)

        plt.title(title)
        plt.xlabel("Alter [Jahre]")
        plt.ylabel(ylabel)
        plt.grid(True, which='both', linestyle=':', alpha=0.6)
        plt.xlim(5.5, 19.5)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
    def create_maturity_plot(self, history, sex, output_path):
        """Erstellt eine Visualisierung für den Reifegrad-Verlauf (Mirwald)."""
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

        plt.text(plt.xlim()[0] + 0.5, 0.6, "Wachstumsschub (PHV)", ha='left', color='green', fontsize=9, fontweight='bold')
        
        if history:
            if isinstance(history[0], dict):
                ages = [h['chron_age'] for h in history]
                offsets = [h['offset'] for h in history]
            else:
                ages, offsets = zip(*history)
                
            plt.plot(ages, offsets, 'ro-', linewidth=2, markersize=6, label='Dein Reifegrad')
            # Letzten Punkt hervorheben
            plt.plot(ages[-1], offsets[-1], 'ro', markersize=10, markeredgecolor='white')
            
            # Aktueller Status Text
            curr_off = offsets[-1]
            if abs(curr_off) < 0.5: status = "Mitten im Schub"
            elif curr_off < 0: status = f"Noch ca. {abs(curr_off):.1f} J. bis zum Schub"
            else: status = f"Schub vor ca. {curr_off:.1f} J. erfolgt"
            
            plt.annotate(status, xy=(ages[-1], offsets[-1]), xytext=(0, 20),
                         textcoords='offset points', ha='center', 
                         bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='red', alpha=0.8),
                         fontsize=8, color='red', fontweight='bold')

        plt.title("Biologischer Reifegrad (Verlauf)", fontsize=11, fontweight='bold')
        plt.xlabel("Chronologisches Alter (Jahre)", fontsize=9)
        plt.ylabel("Jahre bis/seit dem Wachstumsschub", fontsize=9)
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

        fig, ax = plt.subplots(figsize=(10, 6))
        ages = np.linspace(6, 18, 100)
        percentiles_data = {p: [] for p in self.colors.keys()}
        p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']

        sex_label = 'Mädchen' if sex == 'girls' else 'Jungs'
        ylabel = ""

        if metric_type == 'sprung':
            title, ylabel = f"Sprunghöhe – ALLE ({sex_label})", "Sprunghöhe (cm)"
            for age in ages:
                refs = get_jump_height_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        elif metric_type == 'pmax_rel':
            title, ylabel = f"Sprungkraft/kg – ALLE ({sex_label})", "Leistung (W/kg)"
            for age in ages:
                refs = get_pmax_mass_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        elif metric_type == 'vo2max':
            title, ylabel = f"VO2max – ALLE ({sex_label})", "mL/kg/min"
            for age in ages:
                refs = get_vo2max_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        elif metric_type == 'leistung':
            title, ylabel = f"Max. Leistung – ALLE ({sex_label})", "Leistung (Watt)"
            for age in ages:
                vals = get_smoothed_reference(age, sex, PMAX_ABS_DATA)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'mtp_rel':
            title, ylabel = "Ganzkörperkraft Relativ – ALLE [Athleten-Norm!]", "kg/kg"
            for age in ages:
                vals = get_smoothed_reference(age, sex, MTP_REL_DATA)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'beinstrecker':
            title, ylabel = f"Max. Beinstreckkraft – ALLE ({sex_label})", "Kraft (Nm)"
            for age in ages:
                vals = get_smoothed_reference(age, sex, KNEE_EXT_ABS_HEBERT)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'leg_ext_rel':
            title, ylabel = f"Beinkraft Relativ – ALLE ({sex_label})", "Kraft (Nm/kg)"
            for age in ages:
                vals = get_smoothed_reference(age, sex, KNEE_EXT_REL_HEBERT)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'handkraft':
            title, ylabel = f"Greifkraft Absolut – ALLE ({sex_label})", "Kraft (kg)"
            for age in ages:
                vals = get_smoothed_reference(age, sex, HANDGRIP_DOM_BOHANNON)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'handkraft_rel':
            title, ylabel = f"Greifkraft Relativ – ALLE ({sex_label})", "kg/kg"
            weights = [w for _, _, w in all_patients_histories if w and w > 0]
            avg_weight = float(np.mean(weights)) if weights else 40.0
            for age in ages:
                vals = get_relative_handgrip_bohannon(age, sex, avg_weight)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'kreuzheben':
            title, ylabel = "Isom. Kreuzheben – ALLE [Athleten-Norm!]", "Kraft (kg)"
            for age in ages:
                vals = get_smoothed_reference(age, sex, MTP_ABS_DATA)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'groesse':
            title, ylabel = f"Körpergrösse – ALLE ({sex_label})", "Grösse (cm)"
            for age in ages:
                vals = get_smoothed_reference(age, sex, HEIGHT_DATA)
                for i, p in enumerate(p_names): percentiles_data[p].append(vals[i])

        elif metric_type == 'gewicht':
            title, ylabel = f"Körpergewicht – ALLE ({sex_label})", "Gewicht (kg)"
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
        ax.set_xlabel("Alter [Jahre]")
        ax.set_ylabel(ylabel)
        ax.grid(True, which='both', linestyle=':', alpha=0.5)
        ax.set_xlim(5.5, 19.5)

        if all_patients_histories:
            ax.legend(fontsize=7, loc='upper left', bbox_to_anchor=(1.01, 1),
                      borderaxespad=0, title="Patienten", title_fontsize=8)

        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

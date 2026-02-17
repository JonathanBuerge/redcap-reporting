import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from reference_data import JUMP_HEIGHT_LMS, get_vo2max_reference

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
        return m * ((1 + l * s * z) ** (1/l))

    def create_reference_plot(self, metric_type, history_data, sex, output_path):
        """
        history_data: Liste von Tupeln [(age1, val1), (age2, val2), ...]
        """
        plt.figure(figsize=(6, 4))
        
        ages = np.arange(6, 19, 1)
        percentiles_data = {p: [] for p in self.colors.keys()}
        
        # --- 1. Referenzkurven ---
        if metric_type == 'sprung':
            title = f"Sprunghöhe ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Sprunghöhe (m)"
            ref_dict = JUMP_HEIGHT_LMS.get(sex, {})
            for age in ages:
                if age in ref_dict:
                    l, m, s = ref_dict[age]
                    for p, z in self.z_scores_lms.items():
                        percentiles_data[p].append(self._calc_lms(l, m, s, z))
                else:
                    for p in percentiles_data: percentiles_data[p].append(np.nan)
                    
        elif metric_type == 'vo2max':
            title = f"VO2peak ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "VO2peak (mL/kg/min)"
            for age in ages:
                refs = get_vo2max_reference(age, sex)
                for p in refs: percentiles_data[p].append(refs[p])

        # Referenz zeichnen
        for p_name in ['P3', 'P10', 'P25', 'P75', 'P90', 'P97', 'P50']:
            y_vals = percentiles_data[p_name]
            width = 2 if p_name == 'P50' else 1
            style = '-' if p_name == 'P50' else '--'
            plt.plot(ages, y_vals, color=self.colors[p_name], linestyle=style, linewidth=width)
            if len(y_vals) > 0 and not np.isnan(y_vals[-1]):
                plt.text(ages[-1] + 0.2, y_vals[-1], p_name, fontsize=7, color=self.colors[p_name], va='center')

        # --- 2. Patientenhistorie zeichnen (NEU) ---
        # history_data ist z.B. [(10.5, 25), (11.5, 30)]
        if history_data and len(history_data) > 0:
            # Entpacken in x und y Listen
            p_ages, p_vals = zip(*history_data)
            
            # Umrechnung Sprunghöhe cm -> m (für alle Werte)
            if metric_type == 'sprung':
                p_vals = [v / 100 if v > 5 else v for v in p_vals]

            # A) Linie zeichnen (Trajektorie)
            plt.plot(p_ages, p_vals, color='red', linestyle='-', linewidth=2, alpha=0.7, zorder=9)
            
            # B) Ältere Punkte (kleiner)
            plt.plot(p_ages[:-1], p_vals[:-1], 'ro', markersize=5, zorder=9)
            
            # C) Aktueller Punkt (groß und fett)
            last_age, last_val = p_ages[-1], p_vals[-1]
            plt.plot(last_age, last_val, 'ro', markersize=9, zorder=10)
            plt.text(last_age, last_val + (last_val*0.05), "Du", color='red', fontweight='bold', ha='center', zorder=11)

        # Styling
        plt.title(title)
        plt.xlabel("Alter (Jahre)")
        plt.ylabel(ylabel)
        plt.grid(True, which='both', linestyle=':', alpha=0.6)
        plt.xlim(5.5, 19.5)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from reference_data import (
    get_pmax_mass_reference, get_vo2max_reference, PMAX_ABS_DATA,
    MTP_REL_DATA, MTP_ABS_DATA, LEG_EXT_DATA, HANDGRIP_DOM_DATA, HEIGHT_DATA, WEIGHT_DATA,
    get_jump_height_reference
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

    def create_reference_plot(self, metric_type, history_data, sex, output_path):
        plt.figure(figsize=(6, 4))
        # Höhere Auflösung für glatte Kurven
        ages = np.linspace(6, 18, 100)
        percentiles_data = {p: [] for p in self.colors.keys()}

        def get_interpolated_ref(age, ref_dict):
            """Hilfsfunktion für lineare Interpolation in Dictionaries."""
            keys = sorted(ref_dict.keys())
            if not keys: return [np.nan] * 7
            age_clamped = max(min(age, max(keys)), min(keys))
            if age_clamped in ref_dict: return ref_dict[age_clamped]
            
            low = max([k for k in keys if k <= age_clamped])
            high = min([k for k in keys if k >= age_clamped])
            
            v_low = np.array(ref_dict[low])
            v_high = np.array(ref_dict[high])
            weight = (age_clamped - low) / (high - low)
            return v_low + weight * (v_high - v_low)
        
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
            ref_dict = PMAX_ABS_DATA.get(sex, {})
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_interpolated_ref(age, ref_dict)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'mtp_rel':
            title = f"Ganzkörperkraft (Vergleich: Athleten!)"
            ylabel = "Kraft / Gewicht (kg/kg)"
            ref_dict = MTP_REL_DATA.get(sex, {})
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_interpolated_ref(age, ref_dict)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'beinstrecker':
            title = f"Max. Beinstreckkraft ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Kraft (Nm)"
            ref_dict = LEG_EXT_DATA.get(sex, {})
            p_names = ['P3', 'P10', 'P50', 'P90', 'P97']
            for age in ages:
                vals = get_interpolated_ref(age, ref_dict)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])
                    
        elif metric_type == 'handkraft':
            title = f"Max. Handkraft ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Kraft (kg)"
            ref_dict = HANDGRIP_DOM_DATA.get(sex, {})
            p_names = ['P3', 'P10', 'P50', 'P90', 'P97']
            for age in ages:
                vals = get_interpolated_ref(age, ref_dict)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'kreuzheben':
            title = f"Ganzkörperkraft (Absolut)"
            ylabel = "Kraft (kg)"
            ref_dict = MTP_ABS_DATA.get(sex, {})
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_interpolated_ref(age, ref_dict)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'groesse':
            title = f"Körpergrösse ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Grösse (cm)"
            ref_dict = HEIGHT_DATA.get(sex, {})
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_interpolated_ref(age, ref_dict)
                for i, p in enumerate(p_names):
                    percentiles_data[p].append(vals[i])

        elif metric_type == 'gewicht':
            title = f"Körpergewicht ({'Mädchen' if sex == 'girls' else 'Jungs'})"
            ylabel = "Gewicht (kg)"
            ref_dict = WEIGHT_DATA.get(sex, {})
            p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
            for age in ages:
                vals = get_interpolated_ref(age, ref_dict)
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
        plt.xlabel("Alter (Jahre)")
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

import pandas as pd
import numpy as np

class Analyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        
        # HIER IST DER FIX: Die echten CSV-Namen nutzen!
        self.metric_map = {
            "handkraft": "crf_handgrip",
            "sprung": "crf_cmj_height",
            "kreuzheben": "crf_mtp_lift",
            "vo2max": "crf_vo2max",
            "leistung": "crf_pmax",
            "groesse": "crf_height",
            "gewicht": "crf_weight"
        }
        # Die 3 Beinstrecker-Spalten
        self.leg_cols = ["crf_isom_max1", "crf_isom_max2", "crf_isom_max3"]

    def _safe_numeric(self, series):
        """Wandelt Komma-Strings sicher in Zahlen um."""
        s = series.astype(str)
        s = s.str.replace(',', '.', regex=False)
        return pd.to_numeric(s, errors='coerce')

    def get_all_patient_ids(self):
        """Versucht die ID-Spalte zu finden (meist 'record_id' oder die erste Spalte)"""
        if not self.df.empty:
            # Prio 1: Wenn 'record_id' existiert, nimm die
            if 'record_id' in self.df.columns:
                return self.df['record_id'].dropna().unique()
            # Prio 2: Nimm einfach die erste Spalte
            else:
                return self.df.iloc[:, 0].dropna().unique()
        return []

    def get_patient_data(self, patient_id):
        # ID Spalte identifizieren
        if 'record_id' in self.df.columns:
            id_col = 'record_id'
        else:
            id_col = self.df.columns[0]
        
        # Filter nach ID (als String, um sicher zu sein)
        p_df = self.df[self.df[id_col].astype(str) == str(patient_id)].copy()

        if p_df.empty:
            return None

        results = {}

        # 1. Beinstrecker Spezial-Berechnung (Max aus 3 Spalten)
        valid_leg_cols = []
        for col in self.leg_cols:
            if col in p_df.columns:
                p_df[col] = self._safe_numeric(p_df[col])
                valid_leg_cols.append(col)
        
        if valid_leg_cols:
            p_df["beinstrecker_combined"] = p_df[valid_leg_cols].max(axis=1)
        else:
            p_df["beinstrecker_combined"] = np.nan
        
        # 2. Alle Metriken durchgehen
        full_map = self.metric_map.copy()
        full_map["beinstrecker"] = "beinstrecker_combined"

        for metric_name, col_name in full_map.items():
            val_pre = "-"
            val_post = "-"
            diff_pct = None

            if col_name in p_df.columns:
                if col_name != "beinstrecker_combined":
                    series = self._safe_numeric(p_df[col_name])
                else:
                    series = p_df[col_name]
                
                valid_values = series.dropna()

                if not valid_values.empty:
                    val_pre = valid_values.iloc[0]
                    val_post = valid_values.iloc[-1]
                    
                    if len(valid_values) > 1 and val_pre != 0:
                        diff_pct = ((val_post - val_pre) / val_pre) * 100
            
            results[metric_name] = {
                "pre": val_pre,
                "post": val_post,
                "diff": diff_pct
            }
        
        # Meta-Daten (Versucht Name/Geburtsdatum zu finden, falls vorhanden)
        # Falls Ihre CSV Spalten wie 'name' oder 'dob' hat, hier eintragen
        results["meta"] = {
            "ID": patient_id,
            "Name": "", 
            "Geburtsdatum": ""
        }
        
        return results
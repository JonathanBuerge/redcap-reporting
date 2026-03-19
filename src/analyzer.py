import pandas as pd
import numpy as np

class Analyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        
        # HIER SIND DIE ABSOLUTEN WERTE (Für die Tabelle links)
        self.metric_map = {
            "handkraft": "crf_handgrip",
            "sprung": "crf_cmj_height",
            "kreuzheben": "crf_mtp_lift",      # <- Absolutes Kreuzheben!
            "vo2max": "crf_vo2max",
            "leistung": "crf_pmax",
            "groesse": "crf_height",
            "gewicht": "crf_weight"
        }
        self.leg_cols = ["crf_isom_max1", "crf_isom_max2", "crf_isom_max3"]

    def _safe_numeric(self, series):
        """Wandelt Strings mit Komma in Zahlen um."""
        s = series.astype(str).str.replace(',', '.', regex=False)
        return pd.to_numeric(s, errors='coerce')

    def _parse_dates(self, series):
        return pd.to_datetime(series, errors='coerce')

    def get_all_patient_ids(self):
        if not self.df.empty:
            if 'record_id' in self.df.columns:
                return self.df['record_id'].dropna().unique()
            return self.df.iloc[:, 0].dropna().unique()
        return []

    def get_patient_data(self, patient_id):
        if 'record_id' in self.df.columns:
            id_col = 'record_id'
        else:
            id_col = self.df.columns[0]
            
        p_df = self.df[self.df[id_col].astype(str) == str(patient_id)].copy()
        if p_df.empty: return None

        is_debug = str(patient_id) in ["decad_105", "105"]

        # --- 1. Zeitachse & Alter berechnen (Wieder mit Timestamps & Fallback) --- Alterative wäre crf_date oder so
        p_df['age_calculated'] = np.nan
        
        if 'crf_geb' in p_df.columns:
            # Fallback-Logik: Nimm crf_timestamp, wenn leer nimm parq_timestamp
            ts_crf = p_df['crf_timestamp'] if 'crf_timestamp' in p_df.columns else pd.Series(np.nan, index=p_df.index)
            ts_parq = p_df['parq_timestamp'] if 'parq_timestamp' in p_df.columns else pd.Series(np.nan, index=p_df.index)
            
            ts_crf = ts_crf.replace(r'^\s*$', np.nan, regex=True)
            ts_parq = ts_parq.replace(r'^\s*$', np.nan, regex=True)
            
            combined_ts = ts_crf.fillna(ts_parq)
            
            if combined_ts.isna().all() and is_debug:
                print(f"   [❌ DEBUG ANALYZER] Fehler bei Patient {patient_id}: Weder 'crf_timestamp' noch 'parq_timestamp' enthalten gültige Werte!")

            mess_dates = self._parse_dates(combined_ts)
            geb_str = str(p_df['crf_geb'].iloc[0])
            geb_date = pd.to_datetime(geb_str, errors='coerce')
            
            if pd.notna(geb_date):
                # Alter berechnen
                p_df['age_calculated'] = (mess_dates - geb_date).dt.days / 365.25

        current_age = p_df['age_calculated'].iloc[-1] if not p_df['age_calculated'].isna().all() else None
        if current_age: current_age = round(current_age, 1)

        # --- Geschlecht ---
        sex_str = 'girls' 
        found_sex_val = None
        for s_col in ['q_sex2', 'q_sex', 'sex', 'Gender']:
            if s_col in p_df.columns:
                vals = p_df[s_col].dropna()
                if not vals.empty: found_sex_val = vals.iloc[-1]
        
        if found_sex_val is not None:
            try:
                val_int = int(float(found_sex_val))
                if val_int == 1: sex_str = 'girls'
                elif val_int == 2: sex_str = 'boys'
            except: pass

        results = {
            "meta": {
                "ID": patient_id,
                "Name": "", 
                "Geburtsdatum": p_df['crf_geb'].iloc[0] if 'crf_geb' in p_df.columns else "",
                "age": current_age,
                "sex": sex_str
            }
        }

        # --- 2. Beinstrecker vorbereiten (ABSOLUT) ---
        valid_leg_cols = [c for c in self.leg_cols if c in p_df.columns]
        if valid_leg_cols:
            for c in valid_leg_cols: p_df[c] = self._safe_numeric(p_df[c])
            p_df["beinstrecker_combined"] = p_df[valid_leg_cols].max(axis=1) # <- Absoluter Beinstrecker!
        else:
            p_df["beinstrecker_combined"] = np.nan

        # --- 3. Relative Max Power (Pmax ist bereits relativ, also KEINE Teilung durchs Gewicht) ---
        if 'crf_cmj_pmax' in p_df.columns:
            pmax_rel = self._safe_numeric(p_df['crf_cmj_pmax'])
            p_df['pmax_rel_calculated'] = pmax_rel
        else:
            p_df['pmax_rel_calculated'] = np.nan

        # --- 4. Relative Kraftwerte berechnen (Division durch Gewicht) ---
        if 'crf_weight' in p_df.columns:
            weight = self._safe_numeric(p_df['crf_weight'])
            
            # IMTP Relativ
            if 'crf_mtp_lift' in p_df.columns:
                mtp_abs = self._safe_numeric(p_df['crf_mtp_lift'])
                p_df['mtp_rel_calculated'] = mtp_abs / weight
            else:
                p_df['mtp_rel_calculated'] = np.nan
                
            # Beinstrecker Relativ
            p_df['leg_ext_rel_calculated'] = p_df['beinstrecker_combined'] / weight
        else:
            p_df['mtp_rel_calculated'] = np.nan
            p_df['leg_ext_rel_calculated'] = np.nan

        # --- 5. Metriken extrahieren (Alle: Absolut & Relativ) ---
        full_map = self.metric_map.copy()
        
        # Wir fügen die neu berechneten Spalten hinzu
        full_map["beinstrecker"] = "beinstrecker_combined"       # ABSOLUT
        full_map["pmax_rel"] = "pmax_rel_calculated"             # RELATIV
        full_map["mtp_rel"] = "mtp_rel_calculated"               # RELATIV
        full_map["leg_ext_rel"] = "leg_ext_rel_calculated"       # RELATIV

        for metric_name, col_name in full_map.items():
            val_pre, val_post, diff_pct = "-", "-", None
            history = [] 

            if col_name in p_df.columns:
                # Unterscheidung: selbst berechnete oder originale Spalten
                if col_name in ["beinstrecker_combined", "pmax_rel_calculated", "mtp_rel_calculated", "leg_ext_rel_calculated"]:
                    series = p_df[col_name]
                else:
                    series = self._safe_numeric(p_df[col_name])
                
                # Filtert Paare aus, bei denen entweder Alter oder Wert fehlt
                temp_df = pd.DataFrame({
                    'age': p_df['age_calculated'],
                    'val': series
                }).dropna() 

                if not temp_df.empty:
                    val_pre = temp_df['val'].iloc[0]
                    val_post = temp_df['val'].iloc[-1]
                    
                    if len(temp_df) > 1 and val_pre != 0:
                        diff_pct = ((val_post - val_pre) / val_pre) * 100
                    
                    history = list(zip(temp_df['age'].astype(float), temp_df['val'].astype(float)))

            # Speichert Pre, Post und Historie für JEDE Metrik
            results[metric_name] = {
                "pre": val_pre, 
                "post": val_post, 
                "diff": diff_pct,
                "history": history 
            }
        
        return results
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

        last_date = ""
        if 'crf_date' in p_df.columns:
            last_date_raw = p_df['crf_date'].dropna().iloc[-1] if not p_df['crf_date'].dropna().empty else ""
            if pd.notna(last_date_raw):
                try:
                    last_date = pd.to_datetime(last_date_raw).strftime('%d.%m.%Y')
                except: last_date = str(last_date_raw)

        results = {
            "meta": {
                "ID": patient_id,
                "Name": "", 
                "Messdatum": last_date,
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
            
            # Handkraft Relativ
            if 'crf_handgrip' in p_df.columns:
                hand_abs = self._safe_numeric(p_df['crf_handgrip'])
                p_df['handkraft_rel_calculated'] = hand_abs / weight
            else:
                p_df['handkraft_rel_calculated'] = np.nan
        else:
            p_df['mtp_rel_calculated'] = np.nan
            p_df['leg_ext_rel_calculated'] = np.nan
            p_df['handkraft_rel_calculated'] = np.nan

        # --- 5. Maturity Offset nach Mirwald (NEU mit Verlauf) ---
        maturity_history = []
        if 'crf_sitting_height' in p_df.columns and 'crf_height' in p_df.columns and 'crf_weight' in p_df.columns:
            mat_temp_df = p_df.copy()
            mat_temp_df['h_num'] = self._safe_numeric(mat_temp_df['crf_height'])
            mat_temp_df['w_num'] = self._safe_numeric(mat_temp_df['crf_weight'])
            mat_temp_df['sh_num'] = self._safe_numeric(mat_temp_df['crf_sitting_height'])
            
            # Drop rows with missing data for maturity
            mat_valid = mat_temp_df.dropna(subset=['h_num', 'w_num', 'sh_num', 'age_calculated'])
            
            for _, row in mat_valid.iterrows():
                h, w, sh, age = row['h_num'], row['w_num'], row['sh_num'], row['age_calculated']
                if h > 0:
                    leg = h - sh
                    if sex_str == 'boys':
                        off = -9.236 + (0.0002708 * leg * sh) - (0.001663 * age * leg) + (0.007216 * age * sh) + (0.02292 * (w / h) * 100)
                    else:
                        off = -9.376 + (0.0001882 * leg * sh) + (0.0022 * age * leg) + (0.005841 * age * sh) - (0.002658 * age * w) + (0.07693 * (w / h) * 100)
                    maturity_history.append({
                        "chron_age": age,
                        "offset": off,
                        "bio_age": age + off,
                        "date": str(row['crf_date']) if pd.notna(row.get('crf_date')) else results['meta'].get('Messdatum', '-')
                    })
        
        results["meta"]["maturity_history"] = maturity_history
        if maturity_history:
            latest = maturity_history[-1]
            results["meta"]["maturity_offset"] = latest["offset"]
            results["meta"]["biological_age"] = latest["bio_age"]
            results["meta"]["latest_mat_data"] = latest
        else:
            results["meta"]["maturity_offset"] = None
            results["meta"]["biological_age"] = None
            results["meta"]["latest_mat_data"] = None

        # --- 6. Metriken extrahieren (Alle: Absolut & Relativ) ---
        full_map = self.metric_map.copy()
        
        # Wir fügen die neu berechneten Spalten hinzu
        full_map["beinstrecker"] = "beinstrecker_combined"       # ABSOLUT
        full_map["pmax_rel"] = "pmax_rel_calculated"             # RELATIV
        full_map["mtp_rel"] = "mtp_rel_calculated"               # RELATIV
        full_map["leg_ext_rel"] = "leg_ext_rel_calculated"       # RELATIV
        full_map["handkraft_rel"] = "handkraft_rel_calculated"   # RELATIV

        for metric_name, col_name in full_map.items():
            val_pre, val_post, diff_pct = "-", "-", None
            history = [] 

            if col_name in p_df.columns:
                # Unterscheidung: selbst berechnete oder originale Spalten
                if col_name in ["beinstrecker_combined", "pmax_rel_calculated", "mtp_rel_calculated", "leg_ext_rel_calculated", "handkraft_rel_calculated"]:
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
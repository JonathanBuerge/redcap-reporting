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
            "gewicht": "crf_weight",
            "koerperfett": "crf_bf",           # Körperfettanteil (%)
            "knochendichte": "crf_bmd",        # Knochendichte (BMD g/cm²)
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
    def check_data_integrity(self, logger):
        all_ids = self.get_all_patient_ids()
        for p_id in all_ids:
            if 'record_id' in self.df.columns:
                p_df = self.df[self.df['record_id'].astype(str) == str(p_id)]
            else:
                p_df = self.df[self.df.iloc[:, 0].astype(str) == str(p_id)]
                
            # Check Sex
            found_sex = False
            for s_col in ['q_sex2', 'q_sex', 'sex', 'Gender']:
                if s_col in p_df.columns:
                    vals = p_df[s_col].dropna()
                    if not vals.empty: found_sex = True
            if not found_sex:
                logger.warning(f"DATENFEHLER: Patient {p_id} hat kein Geschlecht hinterlegt!")
                
            # Check Birthdate (global)
            valid_geb = p_df['crf_geb'].dropna() if 'crf_geb' in p_df.columns else pd.Series(dtype=object)
            if valid_geb.empty:
                logger.warning(f"DATENFEHLER: Patient {p_id} hat kein Geburtsdatum (crf_geb) in der gesamten Historie hinterlegt!")

            # Check Login Fields at MZP1
            mzp1_rows = p_df[p_df.get('redcap_event_name', '') == 'mzp1_arm_1']
            if not mzp1_rows.empty:
                has_crf_id = False
                has_birthdate = False
                
                if 'crf_id' in mzp1_rows.columns and not mzp1_rows['crf_id'].dropna().empty:
                    has_crf_id = True
                    
                for b_col in ['q_birthdate', 'crf_geb']:
                    if b_col in mzp1_rows.columns and not mzp1_rows[b_col].dropna().empty:
                        has_birthdate = True
                        
                if not has_crf_id:
                    logger.warning(f"DATENFEHLER: Patient {p_id} hat beim MZP1 keine 'crf_id' (Zwingendes Login-Feld fehlt)!")
                if not has_birthdate:
                    logger.warning(f"DATENFEHLER: Patient {p_id} hat beim MZP1 kein Geburtsdatum 'q_birthdate' / 'crf_geb' (Zwingendes Login-Feld fehlt)!")
                
            # Check measurement dates for rows that have actual data
            for _, row in p_df.iterrows():
                # Check if height or weight is present (proxy for a real measurement session)
                has_data = pd.notna(row.get('crf_height')) or pd.notna(row.get('crf_weight'))
                if has_data:
                    date_val = str(row.get('crf_date', '')).strip() if pd.notna(row.get('crf_date')) else ''
                    ts_val = str(row.get('crf_timestamp', '')).strip() if pd.notna(row.get('crf_timestamp')) else ''
                    ts_parq = str(row.get('parq_timestamp', '')).strip() if pd.notna(row.get('parq_timestamp')) else ''
                    
                    if not date_val and not ts_val and not ts_parq:
                        event = row.get('redcap_event_name', 'Unbekanntes Event')
                        logger.warning(f"DATENFEHLER: Patient {p_id} hat Messwerte im Event '{event}', aber weder crf_date noch timestamp!")

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
            
            # Finde das erste gültige Geburtsdatum (egal bei welchem Messzeitpunkt)
            valid_geb = p_df['crf_geb'].dropna()
            geb_str = str(valid_geb.iloc[0]) if not valid_geb.empty else ""
            
            geb_date = pd.to_datetime(geb_str, errors='coerce')
            
            if pd.notna(geb_date):
                # Alter berechnen
                p_df['age_calculated'] = (mess_dates - geb_date).dt.days / 365.25

        current_age = p_df['age_calculated'].iloc[-1] if not p_df['age_calculated'].isna().all() else None
        if current_age: current_age = round(current_age, 1)

        # --- Geschlecht ---
        sex_str = 'unknown' 
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

        # --- ID Aufbereitung für den Report ---
        display_id = str(patient_id)
        if 'crf_id' in p_df.columns:
            # Nimm die crf_id vom aktuellsten Eintrag
            potential_crf_id = p_df['crf_id'].dropna().iloc[-1] if not p_df['crf_id'].dropna().empty else ""
            if str(potential_crf_id).strip():
                display_id = str(potential_crf_id).strip()
            else:
                # Fallback: Nur Zahlen aus record_id (z.B. decad_105 -> 105)
                display_id = "".join(filter(str.isdigit, str(patient_id)))
        else:
            # Fallback: Nur Zahlen aus record_id
            display_id = "".join(filter(str.isdigit, str(patient_id)))

        results = {
            "meta": {
                "ID": display_id,
                "Name": "", 
                "Messdatum": last_date,
                "age": current_age,
                "sex": sex_str
            }
        }

        # --- Körperzusammensetzung: Messmethode aus Checkboxen lesen ---
        # crf_bodycomp___1=1 -> DXA, crf_bodycomp___2=1 -> InBody,
        # crf_bodycomp___3=1 -> Other (kein Standard-Report), alle 0 -> keine Messung
        bodycomp_method = None
        for suffix, method_name in [('1', 'dxa'), ('2', 'inbody'), ('3', 'other')]:
            col = f'crf_bodycomp___{suffix}'
            if col in p_df.columns:
                vals = p_df[col].dropna()
                if not vals.empty:
                    try:
                        if int(float(vals.iloc[-1])) == 1:
                            bodycomp_method = method_name
                            break
                    except (ValueError, TypeError):
                        pass
        results["meta"]["bodycomp_method"] = bodycomp_method  # 'dxa', 'inbody', 'other', or None

        # --- 2. Beinstrecker vorbereiten (ABSOLUT) ---
        valid_leg_cols = [c for c in self.leg_cols if c in p_df.columns]
        if valid_leg_cols:
            for c in valid_leg_cols: p_df[c] = self._safe_numeric(p_df[c])
            p_df["beinstrecker_combined"] = p_df[valid_leg_cols].max(axis=1) # <- Absoluter Beinstrecker!
        else:
            p_df["beinstrecker_combined"] = np.nan

        # --- 3. Relative Max Power (crf_cmj_pmax ist bereits W/kg, KEINE Teilung durch Gewicht) ---
        if 'crf_cmj_pmax' in p_df.columns:
            p_df['sprung_rel_calculated'] = self._safe_numeric(p_df['crf_cmj_pmax'])
        else:
            p_df['sprung_rel_calculated'] = np.nan

        # --- 4. Relative Kraftwerte berechnen (Division durch Gewicht) ---
        if 'crf_weight' in p_df.columns:
            weight = self._safe_numeric(p_df['crf_weight'])
            
            # Kreuzheben Relativ
            if 'crf_mtp_lift' in p_df.columns:
                mtp_abs = self._safe_numeric(p_df['crf_mtp_lift'])
                p_df['kreuzheben_rel_calculated'] = mtp_abs / weight
            else:
                p_df['kreuzheben_rel_calculated'] = np.nan
                
            # Beinstrecker Relativ
            p_df['beinstrecker_rel_calculated'] = p_df['beinstrecker_combined'] / weight
            
            # Handkraft Relativ
            if 'crf_handgrip' in p_df.columns:
                hand_abs = self._safe_numeric(p_df['crf_handgrip'])
                p_df['handkraft_rel_calculated'] = hand_abs / weight
            else:
                p_df['handkraft_rel_calculated'] = np.nan
        else:
            p_df['kreuzheben_rel_calculated'] = np.nan
            p_df['beinstrecker_rel_calculated'] = np.nan
            p_df['handkraft_rel_calculated'] = np.nan

        # --- 5. Maturity Offset nach Mirwald (NEU mit Verlauf) ---
        maturity_history = []
        if 'crf_sitting_height' in p_df.columns and 'crf_height' in p_df.columns and 'crf_weight' in p_df.columns:
            mat_temp_df = p_df.copy()
            mat_temp_df['h_num'] = self._safe_numeric(mat_temp_df['crf_height'])
            mat_temp_df['w_num'] = self._safe_numeric(mat_temp_df['crf_weight'])
            mat_temp_df['sh_num'] = self._safe_numeric(mat_temp_df['crf_sitting_height'])
            
            # Korrektur der Sitzhöhe (gemessen auf Hocker von 46 cm Höhe)
            # HINWEIS: Die Mirwald-Schätzung ist für < 10 Jahre unplausibel (Schätzfehler nimmt zu).
            # Die <10-Sonderbehandlung wird hier im Code dennoch beibehalten (numerische Stabilität).
            def _correct_sh(x):
                if pd.isna(x): return x
                return x - 46.0 if x > 10 else x - 0.46
            mat_temp_df['sh_num'] = mat_temp_df['sh_num'].apply(_correct_sh)
            
            # Drop rows with missing data for maturity
            mat_valid = mat_temp_df.dropna(subset=['h_num', 'w_num', 'sh_num', 'age_calculated'])
            
            # Normwerte für das durchschnittliche Alter beim PHV
            ref_phv = 14.0 if sex_str == 'boys' else 12.0
            
            for _, row in mat_valid.iterrows():
                h, w, sh, age = row['h_num'], row['w_num'], row['sh_num'], row['age_calculated']
                if h > 0:
                    leg = h - sh
                    
                    # --- Gleichung 1 (Jungs) / 2 (Mädchen): Ursprüngliche Gleichungen ---
                    if sex_str == 'boys':
                        off_eq12 = -29.769 + (0.0003007 * leg * sh) - (0.01177 * age * leg) + (0.01639 * age * sh) + (0.445 * (leg / h * 100))
                        f_eq12_str = f"-29.769 + (0.0003007*{leg:.1f}*{sh:.1f}) - (0.01177*{age:.1f}*{leg:.1f}) + (0.01639*{age:.1f}*{sh:.1f}) + (0.445*({leg:.1f}/{h:.1f}*100))"
                    else:
                        off_eq12 = -16.364 + (0.0002309 * leg * sh) + (0.006277 * age * sh) + (0.179 * (leg / h * 100)) + (0.0009428 * age * w)
                        f_eq12_str = f"-16.364 + (0.0002309*{leg:.1f}*{sh:.1f}) + (0.006277*{age:.1f}*{sh:.1f}) + (0.179*({leg:.1f}/{h:.1f}*100)) + (0.0009428*{age:.1f}*{w:.1f})"
                    
                    # --- Gleichung 3 (Jungs) / 4 (Mädchen): Kombinierte Gleichungen ---
                    if sex_str == 'boys':
                        off_eq34 = -9.236 + (0.0002708 * leg * sh) - (0.001663 * age * leg) + (0.007216 * age * sh) + (0.02292 * (w / h) * 100)
                        f_eq34_str = f"-9.236 + (0.0002708*{leg:.1f}*{sh:.1f}) - (0.001663*{age:.1f}*{leg:.1f}) + (0.007216*{age:.1f}*{sh:.1f}) + (0.02292*({w:.1f}/{h:.1f})*100)"
                    else:
                        off_eq34 = -9.376 + (0.0001882 * leg * sh) + (0.0022 * age * leg) + (0.005841 * age * sh) - (0.002658 * age * w) + (0.07693 * (w / h) * 100)
                        f_eq34_str = f"-9.376 + (0.0001882*{leg:.1f}*{sh:.1f}) + (0.0022*{age:.1f}*{leg:.1f}) + (0.005841*{age:.1f}*{sh:.1f}) - (0.002658*{age:.1f}*{w:.1f}) + (0.07693*({w:.1f}/{h:.1f})*100)"
                    
                    # Biologische Alter beider Gleichungen
                    bio_age_eq12 = ref_phv + off_eq12
                    bio_age_eq34 = ref_phv + off_eq34
                    
                    maturity_history.append({
                        "chron_age":    age,
                        # Eq 3/4 (Hauptgleichung, rückwärtskompatibel)
                        "offset":       off_eq34,
                        "bio_age":      bio_age_eq34,
                        # Eq 1/2 (Vergleichsgleichung)
                        "off_eq12":     off_eq12,
                        "bio_age_eq12": bio_age_eq12,
                        # Eq 3/4 explizit (zur Klarheit in DEV-Auswertung)
                        "off_eq34":     off_eq34,
                        "bio_age_eq34": bio_age_eq34,
                        # Rohdaten (für DEV-Tabelle)
                        "raw_h":   round(h,  1),
                        "raw_w":   round(w,  1),
                        "raw_sh":  round(sh, 1),
                        "raw_leg": round(leg,1),
                        "date": str(row['crf_date']) if pd.notna(row.get('crf_date')) else results['meta'].get('Messdatum', '-'),
                        "f_eq12_str": f_eq12_str,
                        "f_eq34_str": f_eq34_str
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
        full_map["beinstrecker"]     = "beinstrecker_combined"       # ABSOLUT
        full_map["sprung_rel"]       = "sprung_rel_calculated"        # RELATIV (W/kg)
        full_map["kreuzheben_rel"]   = "kreuzheben_rel_calculated"    # RELATIV
        full_map["beinstrecker_rel"] = "beinstrecker_rel_calculated"  # RELATIV
        full_map["handkraft_rel"]    = "handkraft_rel_calculated"     # RELATIV

        for metric_name, col_name in full_map.items():
            val_pre, val_post, diff_pct = "-", "-", None
            history = [] 

            if col_name in p_df.columns:
                # Unterscheidung: selbst berechnete oder originale Spalten
                computed_cols = [
                    "beinstrecker_combined", "sprung_rel_calculated",
                    "kreuzheben_rel_calculated", "beinstrecker_rel_calculated",
                    "handkraft_rel_calculated"
                ]
                if col_name in computed_cols:
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
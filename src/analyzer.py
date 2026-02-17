import pandas as pd
import numpy as np

class Analyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.metric_map = {
            "handkraft": "crf_handgrip",
            "sprung": "crf_cmj_height",
            "kreuzheben": "crf_mtp_lift",
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
        """
        Versucht Daten robust zu parsen.
        Entfernt dayfirst=True, da deine CSV YYYY-MM-DD hat.
        """
        # errors='coerce' macht ungültige Daten zu NaT (Not a Time)
        return pd.to_datetime(series, errors='coerce')

    def get_all_patient_ids(self):
        if not self.df.empty:
            if 'record_id' in self.df.columns:
                return self.df['record_id'].dropna().unique()
            return self.df.iloc[:, 0].dropna().unique()
        return []

    def get_patient_data(self, patient_id):
        # ID Spalte finden
        if 'record_id' in self.df.columns:
            id_col = 'record_id'
        else:
            id_col = self.df.columns[0]
            
        # Daten filtern
        p_df = self.df[self.df[id_col].astype(str) == str(patient_id)].copy()
        if p_df.empty: return None

        # --- 1. Zeitachse & Alter berechnen (Für ALLE Zeilen) ---
        # Wir berechnen das Alter für jede Zeile, damit wir den Verlauf plotten können
        p_df['age_calculated'] = np.nan
        
        if 'crf_timestamp' in p_df.columns and 'crf_geb' in p_df.columns:
            # Datumsspalten parsen (HIER WAR DER FEHLER)
            mess_dates = self._parse_dates(p_df['crf_timestamp'])
            
            # Geburtsdatum ist meist statisch pro Patient
            geb_str = str(p_df['crf_geb'].iloc[0])
            geb_date = pd.to_datetime(geb_str, errors='coerce')
            
            # Alter in Jahren berechnen
            if pd.notna(geb_date):
                # (Messdatum - Geburtsdatum) / 365.25
                # dt.days gibt die Tage zurück
                p_df['age_calculated'] = (mess_dates - geb_date).dt.days / 365.25

        # Aktuelles Alter (letzter Eintrag) für den Header
        current_age = p_df['age_calculated'].iloc[-1] if not p_df['age_calculated'].isna().all() else None
        if current_age: current_age = round(current_age, 1)

        # Geschlecht bestimmen
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

        # --- 2. Beinstrecker vorbereiten ---
        valid_leg_cols = [c for c in self.leg_cols if c in p_df.columns]
        if valid_leg_cols:
            for c in valid_leg_cols: p_df[c] = self._safe_numeric(p_df[c])
            p_df["beinstrecker_combined"] = p_df[valid_leg_cols].max(axis=1)
        else:
            p_df["beinstrecker_combined"] = np.nan

        # --- 3. Metriken extrahieren (inkl. Historie) ---
        full_map = self.metric_map.copy()
        full_map["beinstrecker"] = "beinstrecker_combined"

        for metric_name, col_name in full_map.items():
            val_pre, val_post, diff_pct = "-", "-", None
            history = [] # Liste von Tupeln: (Alter, Wert)

            if col_name in p_df.columns:
                if col_name != "beinstrecker_combined":
                    series = self._safe_numeric(p_df[col_name])
                else:
                    series = p_df[col_name]
                
                # Wir erstellen einen DataFrame nur mit Alter und Wert, um NaNs sauber zu filtern
                temp_df = pd.DataFrame({
                    'age': p_df['age_calculated'],
                    'val': series
                }).dropna() # Entfernt Zeilen wo Alter ODER Wert fehlt! Fix für "posx finite" Fehler.

                if not temp_df.empty:
                    # Werte für Text-Tabelle (Erster und Letzter)
                    val_pre = temp_df['val'].iloc[0]
                    val_post = temp_df['val'].iloc[-1]
                    
                    if len(temp_df) > 1 and val_pre != 0:
                        diff_pct = ((val_post - val_pre) / val_pre) * 100
                    
                    # Historie für Plots füllen: [(10.5, 25), (11.5, 30)...]
                    # Wir zwingen es zu float, damit JSON serialization klappt
                    history = list(zip(temp_df['age'].astype(float), temp_df['val'].astype(float)))

            results[metric_name] = {
                "pre": val_pre, 
                "post": val_post, 
                "diff": diff_pct,
                "history": history # NEU!
            }
        
        return results
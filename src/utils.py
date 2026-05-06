import os
import pandas as pd

def ensure_patient_dirs(base_dir: str, patient_id: int):
    """Erstellt Ordnerstruktur für einen Patienten"""
    patient_dir = os.path.join(base_dir, f"patient_{patient_id}")
    plots_dir = os.path.join(patient_dir, "plots")

    os.makedirs(plots_dir, exist_ok=True)

    return patient_dir, plots_dir

def load_merged_data(main_csv: str, api_csv: str = None) -> pd.DataFrame:
    """Lädt die Hauptdaten und merge Geschlechts-Infos aus der API-Datei falls vorhanden."""
    if not os.path.exists(main_csv):
        return None
    
    df = pd.read_csv(main_csv, low_memory=False)
    
    if api_csv and os.path.exists(api_csv):
        try:
            api_df = pd.read_csv(api_csv, low_memory=False)
            # Nur record_id und relevante Geschlechts-Spalten nehmen
            sex_cols = ['record_id'] + [c for c in ['q_sex', 'q_sex2'] if c in api_df.columns]
            sex_info = api_df[sex_cols].dropna(subset=[c for c in ['q_sex', 'q_sex2'] if c in api_df.columns], how='all')
            
            # Gruppieren um pro Patient einen Eintrag zu haben
            sex_info = sex_info.groupby('record_id').first().reset_index()
            
            # Mergen
            df = df.merge(sex_info, on='record_id', how='left')
        except Exception as e:
            print(f"⚠️ Warnung beim Laden der Geschlechtsdaten: {e}")
            
    return df

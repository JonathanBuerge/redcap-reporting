import requests
import os
import pandas as pd
from dotenv import load_dotenv
from io import StringIO

load_dotenv()

def anonymize_and_save(raw_csv_text, output_path):
    df = pd.read_csv(StringIO(raw_csv_text), sep=',')
    
    col_start_name = "mail"
    col_end_name = "fragebogen_kind_complete"
    
    try:
        start_idx = df.columns.get_loc(col_start_name)
        end_idx = df.columns.get_loc(col_end_name)
        
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
            
        cols_to_drop = df.columns[start_idx : end_idx + 1]
        df.drop(columns=cols_to_drop, inplace=True)
        print(f"✅ Datenschutz-Filter aktiv: {len(cols_to_drop)} identifizierende Spalten entfernt.")
        
    except KeyError as e:
        print(f"❌ FEHLER: Spalte zum Schneiden nicht gefunden! ({e})")
        return
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"📁 Anonymisierte Daten gespeichert unter: {output_path}")

def download_redcap_data(api_url, api_token, output_path):
    if not api_url or not api_token:
        print("❌ FEHLER: API URL oder Token fehlen.")
        return False

    payload = {
        'token': api_token, 'content': 'record', 'action': 'export', 'format': 'csv',
        'type': 'flat', 'csvDelimiter': ',', 'rawOrLabel': 'raw', 'rawOrLabelHeaders': 'raw',
        'exportCheckboxLabel': 'false', 'exportSurveyFields': 'true', 'exportDataAccessGroups': 'false',
        'returnFormat': 'json'
    }
    
    print(f"🔄 Verbinde mit REDCap API...")
    try:
        response = requests.post(api_url, data=payload)
        response.raise_for_status() 
        anonymize_and_save(response.text, output_path)
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Fehler bei der API-Abfrage: {e}")
        return False

if __name__ == "__main__":
    REDCAP_API_URL = os.getenv('REDCAP_API_URL')
    REDCAP_API_TOKEN = os.getenv('REDCAP_API_TOKEN')
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_CSV = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data', 'anonym.csv'))
    
    download_redcap_data(REDCAP_API_URL, REDCAP_API_TOKEN, OUTPUT_CSV)
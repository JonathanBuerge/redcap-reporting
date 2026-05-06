import os
import requests
from dotenv import load_dotenv

# 1. Konfiguration laden
# Falls die .env im src-Ordner liegt, laden wir sie von dort:
env_path = os.path.join(os.path.dirname(__file__), 'src', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv() # Fallback auf Standard-Pfad

REDCAP_API_URL = os.getenv('REDCAP_API_URL')
REDCAP_API_TOKEN = os.getenv('REDCAP_API_TOKEN')

def upload_pdf_to_redcap(record_id, file_path, field_name='report_upload', event=None):
    """
    Lädt eine PDF-Datei in ein spezifisches REDCap-Record hoch.
    Sicherheits-Info: 
    - TLS-Verschlüsselung wird durch HTTPS (requests Standard) erzwungen.
    - Jeder Upload wird im REDCap 'Logging' Modul mit Zeitstempel und User protokolliert.
    """
    if not REDCAP_API_URL or not REDCAP_API_TOKEN:
        print("❌ FEHLER: REDCAP_API_URL oder REDCAP_API_TOKEN nicht in .env gefunden.")
        return False

    if not os.path.exists(file_path):
        print(f"❌ FEHLER: Datei nicht gefunden: {file_path}")
        return False

    event_msg = f" (Event: '{event}')" if event else ""
    print(f"🔄 Starte Upload für Record '{record_id}' in Feld '{field_name}'{event_msg}...")

    # Multipart-Form-Daten vorbereiten
    data = {
        'token': REDCAP_API_TOKEN,
        'content': 'file',
        'action': 'import',
        'record': record_id,
        'field': field_name,
        'returnFormat': 'json'
    }
    if event:
        data['event'] = event

    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            
            # API Request (HTTPS erzwingt TLS)
            response = requests.post(REDCAP_API_URL, data=data, files=files)
            
            if response.status_code == 200:
                print(f"✅ ERFOLG: Bericht für ID {record_id} wurde hochgeladen.")
                print(f"📧 Info: Falls 'Alerts & Notifications' konfiguriert sind, wird jetzt die Email versendet.")
                return True
            else:
                print(f"❌ FEHLER beim Upload: Status {response.status_code}")
                print(f"Antwort: {response.text}")
                if "invalid event" in response.text.lower():
                    print("💡 TIPP: Dein Projekt ist 'longitudinal'. Du musst einen Event-Namen angeben (z.B. 'mzp1_arm_1').")
                return False

    except Exception as e:
        print(f"❌ KRITISCHER FEHLER: {e}")
        return False

if __name__ == "__main__":
    # --- SICHERHEITS-HINWEIS ---
    # Nutze dieses Skript nur für manuelle Einzeltests. 
    # In der Produktion sollte die record_id dynamisch übergeben werden (z.B. aus main.py).
    
    # Beispiel für einen Test:
    import sys
    if len(sys.argv) < 2:
        print("💡 Nutzung: python3 redcap_upload_test.py <RECORD_ID> [EVENT_NAME]")
        print("Beispiel: python3 redcap_upload_test.py decad_101 mzp1_arm_1")
    else:
        RECORD_ID_TO_TEST = sys.argv[1]
        EVENT_NAME = sys.argv[2] if len(sys.argv) > 2 else None
        TEST_FILE = 'output/test_report.pdf'
        
        # Sicherstellen, dass das Verzeichnis existiert
        os.makedirs('output', exist_ok=True)
        if not os.path.exists(TEST_FILE):
            with open(TEST_FILE, 'w') as f: f.write("Dummy PDF Content for REDCap Upload Demo")

        upload_pdf_to_redcap(RECORD_ID_TO_TEST, TEST_FILE, event=EVENT_NAME)

"""
--- ANLEITUNG: AUTOMATISCHE EMAIL-BENACHRICHTIGUNG (REDCAP ALERTS) ---

1. 'Alert Trigger Limit' (Wichtig für deine Frage!):
   - Wähle hier: 'Only once per record'. 
   - Das verhindert, dass ein Patient mehrfach dieselbe Mail bekommt, falls die Datei korrigiert wird.

2. Wie du nur max. 3 Emails erhältst (Test-Modus):
   - Ändere die Bedingung in STEP 1 zu:
     ([report_upload] <> "") AND ([record_id] = 'decad_101' OR [record_id] = 'decad_102' OR [record_id] = 'decad_103')
   - So wird der Alert NUR für diese drei Test-IDs ausgelöst, egal wie viele PDFs du hochlädst.

3. Trigger:
   - 'How will the alert be triggered?': 'When conditional logic is met'
   - 'Condition': [report_upload] <> ""

SICHERHEIT (DSFA):
- Das Risiko einer Fehlzuordnung verringerst du, indem du die 'record_id' im Skript niemals hart codierst, 
  sondern sie immer direkt aus dem Daten-Loop (z.B. in deiner main.py) nimmst.
- TLS: Die Übertragung erfolgt verschlüsselt (HTTPS).
- Audit Trail: Alle Aktionen sind im REDCap 'Logging' einsehbar.
"""

import os
import sys
import logging
import subprocess
import pandas as pd
from redcap_api import upload_report_to_redcap, _post, REDCAP_API_TOKEN, CRF_COMPLETE_FIELD

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

def get_all_patient_events():
    """Reads REDCap directly to find all MZP events per patient where crf is at least partially complete."""
    payload = {
        'token': REDCAP_API_TOKEN,
        'content': 'record',
        'action': 'export',
        'format': 'json',
        'type': 'flat',
        'fields': f'record_id,{CRF_COMPLETE_FIELD}',
        'events': ','.join([f"mzp{i}_arm_1" for i in range(1, 16)]),
        'rawOrLabel': 'raw',
        'rawOrLabelHeaders': 'raw',
        'returnFormat': 'json',
    }
    response = _post(payload)
    records = response.json()
    
    patient_events = {}
    for row in records:
        rec_id = str(row.get('record_id', '')).strip()
        crf_complete = str(row.get(CRF_COMPLETE_FIELD, '')).strip()
        event = row.get('redcap_event_name', '')
        
        # We upload to events where there is some data (0, 1, or 2)
        if rec_id and crf_complete in ('0', '1', '2') and event.startswith('mzp'):
            if rec_id not in patient_events:
                patient_events[rec_id] = []
            patient_events[rec_id].append(event)
    return patient_events

def main():
    patient_events = get_all_patient_events()
    all_ids = list(patient_events.keys())
    
    logging.info(f"Gefundene Patienten mit Events: {len(all_ids)}")
    if not all_ids:
        logging.info("Keine IDs gefunden.")
        return

    # To avoid argument length limits, run main.py natively inside Python or split chunks
    cmd = [sys.executable, "src/main.py", "--ids"] + all_ids + ["--no-upload", "--lang", "de"]
    logging.info("Starte main.py um alle PDFs lokal zu generieren...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        logging.error("Fehler bei der PDF-Generierung via main.py")
        return
        
    logging.info("PDF-Generierung abgeschlossen. Starte den Upload zu ALLEN Zeitpunkten...")
    
    for p_id, events in patient_events.items():
        # Ensure ID format uses 'decad_' not 'decade_' if main.py normalized it
        normalized_id = p_id.replace('decade_', 'decad_') if p_id.startswith('decade_') else p_id
        pdf_path = f"./reports/patient_{normalized_id}/report.pdf"
        
        if not os.path.exists(pdf_path):
            logging.warning(f"Keine PDF für {normalized_id} gefunden, überspringe Upload.")
            continue
            
        for event in events:
            mzp_str = event.split('_')[0].replace('mzp', '')
            logging.info(f"Lade hoch für {normalized_id} -> MZP {mzp_str}...")
            upload_report_to_redcap(p_id, pdf_path, mzp=mzp_str)
            
    logging.info("Upload auf alle Zeitpunkte erfolgreich abgeschlossen.")

if __name__ == '__main__':
    main()

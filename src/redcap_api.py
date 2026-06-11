"""
redcap_api.py – Vollständige REDCap API-Schnittstelle für DECADE Reporting

Abschnitte:
  1. Konfiguration & HTTP-Hilfsfunktion
  2. Daten-Download & Anonymisierung   (ehem. data_importer.py)
  3. Offene Reports erkennen
  4. PDF-Upload
"""

import os
import logging
import requests
import pandas as pd
from io import StringIO
from dotenv import load_dotenv

# ── Konfiguration ─────────────────────────────────────────────────────────────
_env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(_env_path)

REDCAP_API_URL   = os.getenv('REDCAP_API_URL')
REDCAP_API_TOKEN = os.getenv('REDCAP_API_TOKEN')

# Events in REDCap, die ein CRF-Formular enthalten (MZP1–MZP15)
CRF_EVENTS = [f"mzp{i}_arm_1" for i in range(1, 16)]

UPLOAD_FIELD       = "report_upload"
CRF_COMPLETE_FIELD = "crf_complete"
FEEDBACK_FIELD     = "feedback_complete"  # REDCap-Status des Feedback-Formulars

# Spalten, die beim Anonymisieren entfernt werden (von–bis, inklusiv)
_ANON_COL_START = "mail"
_ANON_COL_END   = "fragebogen_kind_complete"


# ── Interne Hilfsfunktion ─────────────────────────────────────────────────────
def _post(payload: dict) -> requests.Response:
    """Sendet einen POST-Request an die REDCap API."""
    if not REDCAP_API_URL or not REDCAP_API_TOKEN:
        raise EnvironmentError(
            "REDCAP_API_URL oder REDCAP_API_TOKEN fehlen in der .env Datei.\n"
            "Bitte die Datei src/.env öffnen und die Zugangsdaten eintragen."
        )
    response = requests.post(REDCAP_API_URL, data=payload, timeout=60)
    response.raise_for_status()
    return response


# ── 1. Daten-Download & Anonymisierung ───────────────────────────────────────
def _anonymize_and_save(raw_csv_text: str, output_path: str) -> None:
    """Entfernt identifizierende Spalten und speichert die anonymisierten Daten."""
    df = pd.read_csv(StringIO(raw_csv_text), sep=',')
    try:
        start_idx = df.columns.get_loc(_ANON_COL_START)
        end_idx   = df.columns.get_loc(_ANON_COL_END)
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
        cols_to_drop = df.columns[start_idx : end_idx + 1]
        df.drop(columns=cols_to_drop, inplace=True)
        logging.info("Datenschutz-Filter: %d identifizierende Spalten entfernt.", len(cols_to_drop))
    except KeyError as e:
        logging.error("Anonymisierung: Spalte nicht gefunden (%s) – Abbruch.", e)
        return
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    logging.info("Anonymisierte Daten gespeichert: %s", output_path)


def _save_api_metadata(raw_csv_text: str, output_path: str) -> None:
    """Speichert nur die für das Merging notwendigen Metadaten (Geschlecht)."""
    df = pd.read_csv(StringIO(raw_csv_text), sep=',', low_memory=False)
    sex_cols = ['record_id'] + [c for c in ['q_sex', 'q_sex2'] if c in df.columns]
    df_meta = df[sex_cols].copy()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_meta.to_csv(output_path, index=False)
    logging.info("API-Metadaten (Geschlecht) gespeichert: %s", output_path)


def download_and_refresh_data(anonym_path: str, api_path: str) -> bool:
    """
    Lädt alle Daten von REDCap herunter, anonymisiert sie und speichert
    sie als lokale CSV-Dateien, die von main.py weiterverarbeitet werden.

    Args:
        anonym_path: Zielpfad für die anonymisierten Messdaten (anonym.csv)
        api_path:    Zielpfad für die Metadaten (api_data.csv)

    Returns:
        True bei Erfolg, False bei Fehler
    """
    logging.info("REDCap: Starte Daten-Download (alle Records, alle Felder)...")
    payload = {
        'token':                  REDCAP_API_TOKEN,
        'content':                'record',
        'action':                 'export',
        'format':                 'csv',
        'type':                   'flat',
        'csvDelimiter':           ',',
        'rawOrLabel':             'raw',
        'rawOrLabelHeaders':      'raw',
        'exportCheckboxLabel':    'false',
        'exportSurveyFields':     'true',
        'exportDataAccessGroups': 'false',
        'returnFormat':           'json',
    }
    try:
        response = _post(payload)
        raw_text = response.text
    except EnvironmentError as e:
        logging.error("Konfigurationsfehler: %s", e)
        return False
    except requests.exceptions.RequestException as e:
        logging.error("REDCap: Verbindungsfehler beim Daten-Download: %s", e)
        return False

    _save_api_metadata(raw_text, api_path)
    _anonymize_and_save(raw_text, anonym_path)
    logging.info("REDCap: Daten erfolgreich aktualisiert.")
    return True


# ── 2. Offene Reports erkennen ────────────────────────────────────────────────
def get_pending_reports() -> list[str]:
    """
    Gibt eine Liste von Record-IDs zurück, bei denen:
      - das CRF in mindestens einem MZP-Event vollständig ist (crf_complete == 2)
      - das Feld 'report_upload' in diesem Event noch leer ist

    Returns:
        z.B. ['decad_101', 'decad_105']
    """
    logging.info("REDCap: Suche Records mit vollständigem CRF, aber ohne Upload...")
    payload = {
        'token':                  REDCAP_API_TOKEN,
        'content':                'record',
        'action':                 'export',
        'format':                 'json',
        'type':                   'flat',
        'fields':                 f'record_id,{CRF_COMPLETE_FIELD},{UPLOAD_FIELD}',
        'events':                 ','.join(CRF_EVENTS),
        'rawOrLabel':             'raw',
        'rawOrLabelHeaders':      'raw',
        'exportCheckboxLabel':    'false',
        'exportSurveyFields':     'false',
        'exportDataAccessGroups': 'false',
        'returnFormat':           'json',
    }
    try:
        response = _post(payload)
        records  = response.json()
    except EnvironmentError as e:
        logging.error("Konfigurationsfehler: %s", e)
        return []
    except requests.exceptions.RequestException as e:
        logging.error("REDCap: Fehler beim Abruf offener Reports: %s", e)
        return []
    except ValueError:
        logging.error("REDCap: Antwort kein gültiges JSON: %s", response.text[:200])
        return []

    # Da REDCap die Events chronologisch zurückgibt (mzp1, mzp2...),
    # überschreiben wir im Dictionary den Eintrag, bis wir das *letzte* abgeschlossene Event haben.
    latest_completed = {}
    for row in records:
        rec_id       = str(row.get('record_id', '')).strip()
        crf_complete = str(row.get(CRF_COMPLETE_FIELD, '')).strip()
        if rec_id and crf_complete == '2':
            latest_completed[rec_id] = row

    pending_ids = []
    for rec_id, row in latest_completed.items():
        upload_val = str(row.get(UPLOAD_FIELD, '')).strip()
        if upload_val == '':
            pending_ids.append(rec_id)
            logging.info("  → Ausstehend: %s (Letztes Event: %s)",
                         rec_id, row.get('redcap_event_name', '?'))

    logging.info("REDCap: %d Record(s) mit ausstehenden Reports.", len(pending_ids))
    return pending_ids


def _get_latest_crf_event(record_id: str) -> str | None:
    """Gibt den neuesten MZP-Event zurück, in dem das CRF vollständig ist."""
    payload = {
        'token':             REDCAP_API_TOKEN,
        'content':           'record',
        'action':            'export',
        'format':            'json',
        'type':              'flat',
        'records':           record_id,
        'fields':            f'record_id,{CRF_COMPLETE_FIELD}',
        'events':            ','.join(CRF_EVENTS),
        'rawOrLabel':        'raw',
        'rawOrLabelHeaders': 'raw',
        'returnFormat':      'json',
    }
    try:
        rows = _post(payload).json()
    except Exception as e:
        logging.error("REDCap: Fehler beim Event-Abruf für %s: %s", record_id, e)
        return None

    latest_event = None
    for row in rows:
        if str(row.get(CRF_COMPLETE_FIELD, '')).strip() == '2':
            latest_event = row.get('redcap_event_name')
    return latest_event


# ── 3. PDF-Upload ─────────────────────────────────────────────────────────────
def upload_report_to_redcap(record_id: str, pdf_path: str, mzp: str = None) -> bool:
    """
    Lädt ein PDF in das korrekte REDCap-Event des Patienten hoch.

    Args:
        record_id: REDCap Record-ID (z.B. 'decad_101')
        pdf_path:  Lokaler Pfad zur fertigen PDF-Datei
        mzp:       Optional. Überschreibt die automatische Event-Suche (z.B. '3' für mzp3_arm_1)

    Returns:
        True bei Erfolg, False bei Fehler
    """
    if not os.path.exists(pdf_path):
        logging.error("Upload abgebrochen – Datei nicht gefunden: %s", pdf_path)
        return False

    if mzp:
        event = f"mzp{mzp}_arm_1"
        logging.info("Manueller Upload-Event gesetzt: %s (Ignoriere crf_complete Status)", event)
    else:
        event = _get_latest_crf_event(record_id)
        if not event:
            logging.error("Upload abgebrochen – Kein vollständiges CRF-Event für %s.", record_id)
            return False

    logging.info("REDCap Upload: %s → Event '%s', Feld '%s'", record_id, event, UPLOAD_FIELD)
    data = {
        'token':        REDCAP_API_TOKEN,
        'content':      'file',
        'action':       'import',
        'record':       record_id,
        'field':        UPLOAD_FIELD,
        'event':        event,
        'returnFormat': 'json',
    }
    try:
        with open(pdf_path, 'rb') as f:
            files    = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            response = requests.post(REDCAP_API_URL, data=data, files=files, timeout=120)
        if response.status_code == 200:
            logging.info("✅ Upload erfolgreich: %s", record_id)
            # Nach erfolgreichem Upload: Feedback-Status setzen (wenn crf_geb+crf_id vorhanden)
            _set_feedback_in_progress(record_id, event)
            return True
        else:
            logging.error("❌ Upload fehlgeschlagen %s: HTTP %s – %s",
                          record_id, response.status_code, response.text[:200])
            if "invalid event" in response.text.lower():
                logging.error("   💡 TIPP: Event '%s' ungültig → REDCap → Project Setup → Events.", event)
            return False
    except requests.exceptions.RequestException as e:
        logging.error("❌ Verbindungsfehler beim Upload für %s: %s", record_id, e)
        return False

# ── 4. Feedback-Formular auf "Gestartet" setzen ──────────────────────────────
def _set_feedback_in_progress(record_id: str, event: str) -> None:
    """
    Setzt den Status des Formulars 'Feedback' auf '1' (Unvollständig/Gestartet)
    im angegebenen Event – aber nur, wenn 'crf_geb' UND 'crf_id' für diesen
    Record ausgefüllt sind.

    Wird automatisch nach einem erfolgreichen PDF-Upload aufgerufen.
    """
    # Prüfen ob q_probandenid und q_birthdate beim mzp1_arm_1 vollständig sind
    logging.info("REDCap: Prüfe q_probandenid / q_birthdate für %s (Event: mzp1_arm_1)...", record_id)
    check_payload = {
        'token':             REDCAP_API_TOKEN,
        'content':           'record',
        'action':            'export',
        'format':            'json',
        'type':              'flat',
        'records':           record_id,
        'fields':            'record_id,q_probandenid,q_birthdate',
        'events':            'mzp1_arm_1',
        'rawOrLabel':        'raw',
        'rawOrLabelHeaders': 'raw',
        'returnFormat':      'json',
    }
    try:
        rows = _post(check_payload).json()
    except Exception as e:
        logging.error("Feedback-Check: Fehler beim Abruf für %s: %s", record_id, e)
        return

    if not rows:
        logging.warning("Feedback-Check: Keine Daten für %s in mzp1_arm_1 gefunden.", record_id)
        return

    row           = rows[0]
    q_birthdate   = str(row.get('q_birthdate', '')).strip()
    q_probandenid = str(row.get('q_probandenid',  '')).strip()

    if not q_birthdate or not q_probandenid:
        logging.info(
            "Feedback-Status nicht gesetzt: q_birthdate='%s', q_probandenid='%s' – eines davon leer.",
            q_birthdate, q_probandenid
        )
        return

    # Beide Felder sind ausgefüllt → feedback_complete auf '1' setzen
    logging.info("REDCap: Setze '%s'=1 für %s (Event: %s)...", FEEDBACK_FIELD, record_id, event)
    import_payload = {
        'token':        REDCAP_API_TOKEN,
        'content':      'record',
        'action':       'import',
        'format':       'json',
        'type':         'flat',
        'returnFormat': 'json',
        'data':         f'[{{"record_id":"{record_id}","redcap_event_name":"{event}","{FEEDBACK_FIELD}":"1"}}]',
    }
    try:
        response = _post(import_payload)
        logging.info("✅ Feedback-Status auf '1' gesetzt: %s (Event: %s)", record_id, event)
    except Exception as e:
        logging.error("❌ Fehler beim Setzen des Feedback-Status für %s: %s", record_id, e)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s | %(levelname)s | %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir   = os.path.abspath(os.path.join(script_dir, '..', 'data'))

    success = download_and_refresh_data(
        anonym_path=os.path.join(data_dir, 'anonym.csv'),
        api_path   =os.path.join(data_dir, 'api_data.csv'),
    )
    sys.exit(0 if success else 1)

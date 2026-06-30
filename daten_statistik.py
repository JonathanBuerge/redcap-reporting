"""
clean_for_reimport.py
=====================
Bereinigungsskript für einen REDCap-Re-Import.

Ablauf
------
1. Basisschutz  – 'record_id' und 'redcap_event_name' bleiben immer erhalten.
2. Vollständige Zeilen filtern – Probanden, bei denen alle relevanten
   Messparameter vollständig ausgefüllt sind, werden entfernt.
3. Vollständige Spalten filtern – Spalten, die über die verbleibenden
   Probanden zu 100 % ausgefüllt sind, werden entfernt und geprinted.
4. Spalten-Sortierung (Placeholder) – DEVICE_GROUPS definiert die spätere
   Gerätegruppierung.  Der Schritt wird derzeit übersprungen (APPLY_SORTING=False).

Ausgabe: data/fehlende_daten.csv  (Original bleibt unverändert)
"""

import os
import pandas as pd  # noqa: F401  (openpyxl wird als Backend bei xlsx benötigt)
import openpyxl  # noqa: F401  (expliziter Import sichert die Abhängigkeit)

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

INPUT_FILE = os.path.join("data", "anonym.csv")
OUTPUT_FILE = os.path.join("data", "fehlende_daten.csv")

# Pflicht-Spalten, die niemals entfernt oder gefiltert werden dürfen
BASE_COLUMNS = ["record_id", "redcap_event_name"]

# Gerätegruppierung (Platzhalter – wird erst später befüllt)
DEVICE_GROUPS: dict[str, list[str]] = {
    "Körperbau": ["crf_height", "crf_weight"],
    "Kraft": ["crf_handgrip"],
    # Weitere Gruppen hier ergänzen, z. B.:
    # "Sprung": ["crf_cmj_height", "crf_cmj_pmax"],
    # "Isokinetik": ["crf_flex_60", "crf_ex_60"],
}

# Auf True setzen, sobald DEVICE_GROUPS vollständig befüllt ist
APPLY_SORTING: bool = False


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def load_data(filepath: str) -> pd.DataFrame:
    """Liest die CSV ein und gibt eine Kopie zurück (Original wird nie verändert)."""
    print(f"[1/4] Lade Daten: {filepath}")
    df = pd.read_csv(filepath, dtype=str, low_memory=False)
    print(f"      → {df.shape[0]} Zeilen, {df.shape[1]} Spalten geladen.")
    return df.copy()


def get_measurement_columns(df: pd.DataFrame) -> list[str]:
    """Gibt alle Spalten zurück, die keine Pflicht-Spalten sind."""
    return [c for c in df.columns if c not in BASE_COLUMNS]


def filter_complete_rows(df: pd.DataFrame, measure_cols: list[str]) -> pd.DataFrame:
    """
    Entfernt Zeilen, bei denen *alle* Messspalten ausgefüllt sind
    (d. h. kein einziger NaN-Wert in den relevanten Spalten).
    """
    print("[2/4] Filtere vollständig ausgefüllte Probanden-Zeilen …")
    before = len(df)

    # Eine Zeile gilt als «vollständig», wenn kein NaN in den Messspalten auftritt
    all_filled_mask = df[measure_cols].notna().all(axis=1)
    df_filtered = df[~all_filled_mask].copy()

    removed = before - len(df_filtered)
    print(f"      → {removed} Zeile(n) entfernt (vollständig ausgefüllt).")
    print(f"      → {len(df_filtered)} Zeile(n) verbleiben.")
    return df_filtered


def filter_fully_filled_columns(
    df: pd.DataFrame, measure_cols: list[str]
) -> pd.DataFrame:
    """
    Entfernt Spalten, die über alle verbleibenden Zeilen zu 100 % ausgefüllt sind.
    Pflicht-Spalten werden nie entfernt.
    """
    print("[3/4] Filtere zu 100 % ausgefüllte Mess-Spalten …")
    fully_filled: list[str] = []

    for col in measure_cols:
        if df[col].notna().all():
            fully_filled.append(col)

    if fully_filled:
        print(f"      → {len(fully_filled)} Spalte(n) zu 100 % ausgefüllt und entfernt:")
        for col in fully_filled:
            print(f"         • {col}")
        df = df.drop(columns=fully_filled)
    else:
        print("      → Keine Spalte zu 100 % ausgefüllt. Nichts entfernt.")

    return df


def apply_device_group_sorting(
    df: pd.DataFrame, groups: dict[str, list[str]]
) -> pd.DataFrame:
    """
    Ordnet die verbleibenden Spalten nach DEVICE_GROUPS.
    Spalten, die im Dictionary nicht vorkommen, werden am Ende angehängt.
    Pflicht-Spalten stehen immer am Anfang.

    Wird derzeit übersprungen (APPLY_SORTING=False).
    """
    print("[4/4] Sortiere Spalten nach Gerätegruppen …")

    ordered: list[str] = list(BASE_COLUMNS)
    seen: set[str] = set(BASE_COLUMNS)

    for _device, cols in groups.items():
        for col in cols:
            if col in df.columns and col not in seen:
                ordered.append(col)
                seen.add(col)

    # Alle übrigen Spalten (nicht im Dictionary) am Ende anhängen
    remainder = [c for c in df.columns if c not in seen]
    ordered.extend(remainder)

    # Nur Spalten übernehmen, die tatsächlich im DataFrame existieren
    ordered = [c for c in ordered if c in df.columns]
    return df[ordered]


def save_data(df: pd.DataFrame, filepath: str) -> None:
    """Speichert den bereinigten DataFrame als CSV."""
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"\n✅ Datei gespeichert: {filepath}")
    print(f"   → {df.shape[0]} Zeilen, {df.shape[1]} Spalten.")


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("REDCap Re-Import – Datenbereinigung")
    print("=" * 60)

    # 1. Daten laden (Kopie, Original bleibt unangetastet)
    df = load_data(INPUT_FILE)

    # Statistik über ausgefüllte Felder berechnen und ausgeben
    # 1. Gesamtanzahl nicht-leerer Felder in anonym.csv
    cleaned_df = df.astype(str).apply(lambda x: x.str.strip())
    is_empty_mask = cleaned_df.isin(['nan', 'None', 'NaN', '']) | df.isna()
    total_non_empty = (~is_empty_mask).sum().sum()

    # 2. API-Daten mergen für detaillierte Geschlechts-Feldbelegung (falls vorhanden)
    df_for_stats = df.copy()
    api_file = os.path.join("data", "api_data.csv")
    if os.path.exists(api_file):
        try:
            api_df = pd.read_csv(api_file, dtype=str, low_memory=False)
            target_cols = [c for c in ['q_sex', 'q_sex2', 'q_birthdate', 'q_probandenid'] if c in api_df.columns]
            meta_info = api_df[['record_id'] + target_cols].dropna(subset=target_cols, how='all')
            meta_info = meta_info.groupby('record_id').first().reset_index()
            df_for_stats = df_for_stats.merge(meta_info, on='record_id', how='left')
        except Exception:
            pass

    cleaned_df_stats = df_for_stats.astype(str).apply(lambda x: x.str.strip())
    is_empty_mask_stats = cleaned_df_stats.isin(['nan', 'None', 'NaN', '']) | df_for_stats.isna()

    # 3. Essentielle und Messwert-Spalten definieren
    ESSENTIAL_COLUMNS = [
        "record_id", "redcap_event_name", "crf_id", "crf_geb", "crf_date",
        "crf_timestamp"
    ]
    # Relevante Geschlechts-, Geburtsdatum- und Probanden-ID-Spalten hinzufügen
    for c in ["q_sex", "q_sex2", "sex", "Gender", "q_birthdate", "q_probandenid"]:
        if c in df_for_stats.columns:
            ESSENTIAL_COLUMNS.append(c)

    MEASUREMENT_COLUMNS = [
        "crf_height", "crf_weight", "crf_sitting_height", "crf_handgrip",
        "crf_cmj_height", "crf_cmj_pmax", "crf_mtp_lift", 
        "crf_isom_max1", "crf_isom_max2", "crf_isom_max3",
        "crf_vo2max", "crf_pmax", "crf_bf", "crf_bmd",
        "crf_bodycomp___1", "crf_bodycomp___2", "crf_bodycomp___3"
    ]

    total_rows = df.shape[0]
    stats_lines = []

    stats_lines.append("=" * 60)
    stats_lines.append("Detaillierte Feldbelegung (Spalten-Statistik)")
    stats_lines.append("=" * 60)

    stats_lines.append("\n🔑 ESSENTIELLE METADATEN & LOGIN-FELDER:")
    for col in ESSENTIAL_COLUMNS:
        if col in df_for_stats.columns:
            filled = (~is_empty_mask_stats[col]).sum()
            pct = (filled / total_rows) * 100
            stats_lines.append(f"   • {col:<22}: {filled:>3} von {total_rows:>3} eingetragen ({pct:.1f}%)")
            
            # Spezialfall: crf_timestamp or crf_date direkt nach crf_timestamp ausgeben
            if col == "crf_timestamp" and "crf_date" in df_for_stats.columns:
                filled_either = (~is_empty_mask_stats["crf_timestamp"] | ~is_empty_mask_stats["crf_date"]).sum()
                pct_either = (filled_either / total_rows) * 100
                stats_lines.append(f"   • {'crf_timestamp or crf_date':<22}: {filled_either:>3} von {total_rows:>3} eingetragen ({pct_either:.1f}%)")
        else:
            stats_lines.append(f"   • {col:<22}: [Nicht vorhanden in CSV]")

    stats_lines.append("\n🏋️ MESSWERTE & TESTPARAMETER:")
    for col in MEASUREMENT_COLUMNS:
        if col in df_for_stats.columns:
            filled = (~is_empty_mask_stats[col]).sum()
            pct = (filled / total_rows) * 100
            stats_lines.append(f"   • {col:<22}: {filled:>3} von {total_rows:>3} eingetragen ({pct:.1f}%)")
        else:
            stats_lines.append(f"   • {col:<22}: [Nicht vorhanden in CSV]")

    stats_lines.append("\n" + "=" * 60)

    # 4. Zusammenfassung berechnen (nur auf Original df.columns, um Verfälschung zu vermeiden)
    REPORT_COLUMNS = [
        "record_id", "redcap_event_name", "crf_id", "crf_geb", "crf_date",
        "crf_timestamp", "crf_height", "crf_weight",
        "crf_sitting_height", "crf_handgrip", "crf_cmj_height", "crf_cmj_pmax",
        "crf_mtp_lift", "crf_isom_max1", "crf_isom_max2", "crf_isom_max3",
        "crf_vo2max", "crf_pmax", "crf_bf", "crf_bmd",
        "crf_bodycomp___1", "crf_bodycomp___2", "crf_bodycomp___3"
    ]
    existing_report_cols = [c for c in REPORT_COLUMNS if c in df.columns]
    report_non_empty = (~is_empty_mask[existing_report_cols]).sum().sum()

    stats_lines.append(f"\n📊 ZUSAMMENFASSUNG DATENSTATISTIK (für {INPUT_FILE}):")
    stats_lines.append(f"   • Nicht-leere Felder (gesamt): {total_non_empty}")
    stats_lines.append(f"     Erklärung: Anzahl aller ausgefüllten Zellen über alle {df.shape[1]} Spalten und {df.shape[0]} Zeilen.")
    stats_lines.append(f"   • Nicht-leere Felder (reportrelevant): {report_non_empty}")
    stats_lines.append(f"     Erklärung: Anzahl ausgefüllter Zellen in den {len(existing_report_cols)} reportrelevanten Spalten.")
    stats_lines.append("-" * 60)

    # In Konsole ausgeben
    for line in stats_lines:
        print(line)

    # In Datei data/daten_statistik.txt schreiben
    stats_file = os.path.join("data", "daten_statistik.txt")
    with open(stats_file, "w", encoding="utf-8") as f:
        f.write("\n".join(stats_lines))
    print(f"\n📝 Details wurden in '{stats_file}' gespeichert.")

    # 2. Messspalten bestimmen (ohne Pflicht-Spalten)
    measure_cols = get_measurement_columns(df)

    # 3. Vollständig ausgefüllte Zeilen entfernen
    df = filter_complete_rows(df, measure_cols)

    # Messspalten nach dem Zeilen-Filter aktualisieren (Spalten noch gleich)
    measure_cols = get_measurement_columns(df)

    # 4. Zu 100 % ausgefüllte Spalten entfernen
    df = filter_fully_filled_columns(df, measure_cols)

    # 5. Spalten-Sortierung (Placeholder – derzeit deaktiviert)
    if APPLY_SORTING:
        df = apply_device_group_sorting(df, DEVICE_GROUPS)
        print("      → Spalten neu sortiert.")
    else:
        print(
            "[4/4] Spalten-Sortierung übersprungen "
            "(APPLY_SORTING=False – DEVICE_GROUPS noch unvollständig)."
        )

    # 6. Ergebnis speichern
    save_data(df, OUTPUT_FILE)
    print("=" * 60)


if __name__ == "__main__":
    main()

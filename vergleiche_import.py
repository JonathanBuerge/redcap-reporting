#!/usr/bin/env python3
import csv
import os

def normalize_val(s):
    """
    Normalizes a string for comparison.
    Removes all whitespace (including unicode spaces), converts to lowercase, and standardizes numeric representation.
    """
    if not s:
        return ""
    s = s.lower()
    # Remove ticks/apostrophes and comma/dot conversions
    s = s.replace("'", "").replace("`", "").replace("´", "").replace("ˋ", "")
    s = s.replace(",", ".")
    # Remove all whitespace characters (spaces, tabs, newlines, non-breaking spaces, etc.)
    return "".join(s.split())

def clean_old_value(val_old):
    """
    Strips REDCap comparison markers from the old value:
    - Leading minus signs on numeric overwrites (e.g., '-151')
    - Surrounding parentheses on text overwrites (e.g., '(comment )')
    """
    val = val_old.strip()
    if val.startswith('-'):
        # Keep numeric minus if followed by digit/dot
        # (REDCap prefixes deleted values with a minus, e.g., -151.
        # But if the value was already negative, it could be --1.5 or -1.5)
        # We strip the first character if it's the REDCap comparison minus.
        val = val[1:]
    
    if val.startswith('(') and val.endswith(')'):
        val = val[1:-1]
        
    return val.strip()

def analyze_comparison(new_val, old_val):
    """
    Compares new and old values.
    Returns:
        ('identical', cleaned_old) if they are identical
        ('format_change', cleaned_old) if it is just a format/formatting difference (e.g., 10 -> 10.0, spacing)
        ('content_change', cleaned_old) if the content is truly different
    """
    cleaned_old = clean_old_value(old_val)
    
    # If they are exactly the same
    if new_val == cleaned_old:
        return "identical", cleaned_old
        
    # Compare normalized strings
    norm_new = normalize_val(new_val)
    norm_old = normalize_val(cleaned_old)
    if norm_new == norm_old:
        return "format_change", cleaned_old
        
    # Compare as floats if numeric
    try:
        f_new = float(norm_new)
        f_old = float(norm_old)
        if f_new == f_old:
            return "format_change", cleaned_old
    except ValueError:
        pass
        
    return "content_change", cleaned_old

def main():
    csv_path = os.path.join("data", "Vergleich_bei_Import.csv")
    if not os.path.exists(csv_path):
        print(f"❌ Fehler: Datei '{csv_path}' nicht gefunden.")
        return

    print("=" * 70)
    print("REDCap Import-Vergleich: Analyse von Überschreibungen")
    print("=" * 70)

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader)
        rows = list(reader)

    # Pair rows: R_new (even), R_exist (odd)
    pairs = []
    for i in range(0, len(rows), 2):
        if i + 1 < len(rows):
            pairs.append((rows[i], rows[i+1]))

    content_changes = []
    format_changes = []

    for pair_idx, (new_row, exist_row) in enumerate(pairs):
        record_id = new_row[0]
        event_name = new_row[1]
        
        # Skip rows that are empty or invalid
        if not record_id or record_id == "(existierender Datensatz)":
            continue
            
        for col_idx in range(2, len(header)):
            new_val = new_row[col_idx]
            old_val_raw = exist_row[col_idx]
            
            if old_val_raw:
                col_name = header[col_idx]
                change_type, cleaned_old = analyze_comparison(new_val, old_val_raw)
                
                info = {
                    "record_id": record_id,
                    "event_name": event_name,
                    "column": col_name,
                    "new_val": new_val,
                    "old_val": cleaned_old,
                    "old_val_raw": old_val_raw,
                    "new_row_num": 2 * pair_idx + 2,
                    "old_row_num": 2 * pair_idx + 3
                }
                
                if change_type == "content_change":
                    content_changes.append(info)
                elif change_type == "format_change":
                    format_changes.append(info)

    # ANSI escape sequences for formatting
    RED = "\033[91m"
    GREEN = "\033[92m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    # 1. Output Content Changes
    print(f"\n⚠️  {BOLD}INHALTLICHE ÄNDERUNGEN ({len(content_changes)}):{RESET}")
    print("Diese Werte wurden überschrieben und weisen inhaltliche Unterschiede auf:")
    print("-" * 80)
    for c in content_changes:
        print(f"📍 {BOLD}Zeile {c['new_row_num']}/{c['old_row_num']}{RESET} | Patient: {c['record_id']} | Event: {c['event_name']} | Spalte: {c['column']}")
        print(f"   • Alter Wert:  {RED}{repr(c['old_val'])}{RESET}")
        print(f"   • Neuer Wert:  {GREEN}{repr(c['new_val'])}{RESET}")
        print()

    # 2. Output Format/Formatting Changes
    print(f"\nℹ️  {BOLD}FORMAT- & SCHREIBWEISEN-ÄNDERUNGEN ({len(format_changes)}):{RESET}")
    print("Diese Werte wurden überschrieben, sind aber inhaltlich identisch (z.B. 10 -> 10.0 oder Leerzeichen):")
    print("-" * 80)
    for c in format_changes:
        print(f"📍 {BOLD}Zeile {c['new_row_num']}/{c['old_row_num']}{RESET} | Patient: {c['record_id']} | Event: {c['event_name']} | Spalte: {c['column']}")
        print(f"   • Schreibweise alt : {RED}{repr(c['old_val'])}{RESET}")
        print(f"   • Schreibweise neu : {GREEN}{repr(c['new_val'])}{RESET}")
        print()

    print("=" * 80)
    print("Analyse abgeschlossen.")
    print("=" * 80)

if __name__ == "__main__":
    main()

import os

def ensure_patient_dirs(base_dir: str, patient_id: int):
    """Erstellt Ordnerstruktur für einen Patienten"""
    patient_dir = os.path.join(base_dir, f"patient_{patient_id}")
    plots_dir = os.path.join(patient_dir, "plots")

    os.makedirs(plots_dir, exist_ok=True)

    return patient_dir, plots_dir

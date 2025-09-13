import pandas as pd

class DataLoader:
    def __init__(self, filepath: str, measure_cols: list[str]):
        self.filepath = filepath
        self.measure_cols = measure_cols

    def load_csv(self) -> pd.DataFrame:
        """CSV einlesen und Spalten in numerische Werte konvertieren"""
        df = pd.read_csv(self.filepath)

        # Nur relevante Spalten behalten
        df_measures = df[self.measure_cols].copy()

        # Spalten nach numeric casten (NaN falls nicht möglich)
        for col in self.measure_cols:
            df_measures[col] = pd.to_numeric(df_measures[col], errors="coerce")

        return df_measures

    def load_patient(self, df: pd.DataFrame, patient_index: int) -> pd.Series:
        """Extrahiert Patientendaten anhand Index"""
        return df.iloc[patient_index]

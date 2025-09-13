import pandas as pd

class Analyzer:
    def __init__(self, df: pd.DataFrame, measure_cols: list[str]):
        self.df = df
        self.measure_cols = measure_cols

    def compute_statistics(self) -> pd.DataFrame:
        """Berechnet Statistiken (mean, std, median, min, max)"""
        stats = self.df.describe().T  # enthält count, mean, std, min, 25%, 50%, 75%, max
        stats["median"] = self.df.median(skipna=True)
        return stats

    def get_patient_values(self, patient_index: int) -> pd.Series:
        """Liefert Werte für einen Patienten"""
        return self.df.iloc[patient_index]

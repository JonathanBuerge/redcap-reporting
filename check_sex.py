import pandas as pd
from src.utils import load_merged_data

df = load_merged_data('./data/anonym.csv', './data/api_data.csv')
if df is None:
    print("Could not load data.")
    exit()

missing = 0
total = 0
missing_ids = []

if 'record_id' in df.columns:
    ids = df['record_id'].dropna().unique()
else:
    ids = df.iloc[:, 0].dropna().unique()

for p_id in ids:
    total += 1
    p_df = df[df['record_id'].astype(str) == str(p_id)]
    
    found_sex_val_analyzer = None
    for s_col in ['q_sex2', 'q_sex', 'sex', 'Gender']:
        if s_col in p_df.columns:
            vals = p_df[s_col].dropna()
            if not vals.empty: 
                found_sex_val_analyzer = vals.iloc[-1]
            
    if found_sex_val_analyzer is None:
        missing += 1
        missing_ids.append(p_id)

print(f"Total patients: {total}")
print(f"Missing sex info: {missing}")
print(f"Missing IDs: {missing_ids}")

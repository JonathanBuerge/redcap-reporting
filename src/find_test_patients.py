from analyzer import Analyzer
from utils import load_merged_data

DATA_FILE = "./data/anonym.csv"
API_FILE = "./data/api_data.csv"

df = load_merged_data(DATA_FILE, API_FILE)
analyzer = Analyzer(df)

patients = analyzer.get_all_patient_ids()

dxa_boys = []
dxa_girls = []
inbody_boys = []
inbody_girls = []

for p in patients:
    data = analyzer.get_patient_data(p)
    if data:
        meta = data.get("meta", {})
        sex = meta.get("sex")
        method = meta.get("bodycomp_method")
        mzp_count = len(meta.get("maturity_history", []))
        
        entry = {"id": p, "mzp_count": mzp_count}
        if method == "dxa":
            if sex == "boys": dxa_boys.append(entry)
            elif sex == "girls": dxa_girls.append(entry)
        elif method == "inbody":
            if sex == "boys": inbody_boys.append(entry)
            elif sex == "girls": inbody_girls.append(entry)

def sort_and_get_top(lst):
    return sorted(lst, key=lambda x: x["mzp_count"], reverse=True)[:3]

print("DXA Boys:", sort_and_get_top(dxa_boys))
print("DXA Girls:", sort_and_get_top(dxa_girls))
print("InBody Boys:", sort_and_get_top(inbody_boys))
print("InBody Girls:", sort_and_get_top(inbody_girls))

data_104 = analyzer.get_patient_data("decad_104")
if data_104:
    print("104:", data_104.get("meta", {}).get("sex"), data_104.get("meta", {}).get("bodycomp_method"), len(data_104.get("meta", {}).get("maturity_history", [])))

data_105 = analyzer.get_patient_data("decad_105")
if data_105:
    print("105:", data_105.get("meta", {}).get("sex"), data_105.get("meta", {}).get("bodycomp_method"), len(data_105.get("meta", {}).get("maturity_history", [])))


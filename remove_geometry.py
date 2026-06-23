

import csv
import sys 

import pandas as pd

fname_csv = "s:/GitLab/ERP_dashboard/data/indicatoren/data_kaarten_dashboard.csv"
fname_csv_v2 = "s:/GitLab/ERP_dashboard/data/indicatoren/data_kaarten_dashboard_v2.csv"

csv.field_size_limit(sys.maxsize)
df = pd.read_csv(fname_csv, sep=None, engine="python")

df = df.drop(columns=["geometry", "Shape_Leng", "Shape_Area"], errors="ignore") # Verwijder eventuele bestaande kolom "geometry"

# df.to_csv(fname_csv_v2, index=False, quoting=csv.QUOTE_NONNUMERIC)
df.to_csv(fname_csv_v2, index=False)

print("Saved to", fname_csv_v2)
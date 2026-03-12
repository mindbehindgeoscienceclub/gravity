import pandas as pd
import numpy as np

#instal "pip install openpyxl" pada terminan atau diawal program

df = pd.read_excel(r"C:\Users\VIVOBOOK\Documents\MBG\115230031_Data G-OBS.xlsx", usecols="E") #kasih alamat file excelnya yh, usecols buat hanya baca kolom E

df.iloc[:,0] = pd.to_numeric(df.iloc[:,0], errors="coerce")

counter_reading = np.array([1800, 1700, 1600])
value_in_mGal = np.array([1906.96, 1801.03, 1695.11])
factor_for_interval = np.array([1.0593, 1.05929, 1.05925])

skala_bacaan = df.iloc[:,0].to_numpy().reshape(-1,1)
skala_bacaan = skala_bacaan[(skala_bacaan >= 1700) & (skala_bacaan <= 1800)] #biar ga 1 kolom dibaca ama dia
skala_bacaan = skala_bacaan.reshape(-1,1)
print("Nilai Skala Bacaan\n", skala_bacaan)

def konversi (value_in_mGal, skala_bacaan, counter_reading, factor_for_interval):
    return counter_reading + (skala_bacaan - value_in_mGal) * factor_for_interval

konversi_skala_bacaan = []

for s in skala_bacaan:

    s = s[0]

    if s >= 1800:
        g = value_in_mGal[0] + (s - counter_reading[0]) * factor_for_interval[0]

    elif s >= 1700:
        g = value_in_mGal[1] + (s - counter_reading[1]) * factor_for_interval[1]

    else:
        g = value_in_mGal[2] + (s - counter_reading[2]) * factor_for_interval[2]

    konversi_skala_bacaan.append(g)

print("Hasil konversi mGal:")
for h in konversi_skala_bacaan:
    print([h])
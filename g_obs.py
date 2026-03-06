import pandas as pd

# input data (g_avg dan koreksi_drift) dari file CSV
file_csv = "input.csv"

# nilai gravitasi absolut base station (mGal)
g_absolute = float(input("Masukkan nilai G-absolut base station (mGal): \nJogja : 978198.417 mGal \n"))

df = pd.read_csv(file_csv)
g_avg = df["g_avg"]
koreksi_drift = df["koreksi_drift"]



# perhitungan

# 1. G-terkoreksi drift
df["g_terkoreksi_drift"] = g_avg - koreksi_drift

# 2. delta G terhadap base station (baris pertama)
base_value = df["g_terkoreksi_drift"].iloc[0]
df["delta_g"] = df["g_terkoreksi_drift"] - base_value

# 3. g observasi
df["g_obs"] = g_absolute + df["delta_g"]

# ===============================
# OUTPUT
# ===============================

print("\nHasil Perhitungan:")
print(df)

# simpan hasil
df.to_csv("g_obs.csv", index=False)

print("\nFile hasil disimpan sebagai: g_obs.csv")
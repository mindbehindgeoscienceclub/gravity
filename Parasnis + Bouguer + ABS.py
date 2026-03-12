import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress


# 1. Baca Data File 
nama_file = r'C:\Users\LOQ\Downloads\Excel Gravv.xlsx'

df = pd.read_excel(nama_file, sheet_name='Sheet2')

df_clean = df.dropna(subset=['FAA', 'Z']).copy()
df_clean['Z'] = pd.to_numeric(df_clean['Z'], errors='coerce')
df_clean['FAA'] = pd.to_numeric(df_clean['FAA'], errors='coerce')
df_clean = df_clean.dropna(subset=['FAA', 'Z'])


# 2. METODE Parasnis
# Sumbu X = 0.04193 * Z (elevasi)
# Sumbu Y = FAA
df_clean['Sumbu_X'] = 0.04193 * df_clean['Z']
df_clean['Sumbu_Y'] = df_clean['FAA']

# Regresi Linear untuk Parasnis
slope, intercept, r_value, p_value, std_err = linregress(df_clean['Sumbu_X'], df_clean['Sumbu_Y'])
rho_estimasi = slope 

print(f"=== HASIL METODE PARASNIS ===")
print(f"Densitas Estimasi (rho) : {rho_estimasi:.3f} g/cm3")
print(f"Nilai R-squared         : {r_value**2:.4f}\n")

# 3. ABS (Anomali Bouguer Sederhana)
df_clean['Koreksi_Bouguer'] = 0.04193 * rho_estimasi * df_clean['Z']

# ABS = FAA - Koreksi Bouguer
df_clean['ABS_mGal'] = df_clean['FAA'] - df_clean['Koreksi_Bouguer']

df_clean[['Titik', 'Z', 'FAA', 'Koreksi_Bouguer', 'ABS_mGal']].to_csv('Hasil_Parasnis_dan_ABS.csv', index=False)
print("Data perhitungan telah disimpan di 'Hasil_Parasnis_dan_ABS.csv'")

# 4. MVisualisasi Grafik
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# GRAFIK 1: Plot Parasnis
ax1.scatter(df_clean['Sumbu_X'], df_clean['Sumbu_Y'], color='blue', alpha=0.6, label='Data Observasi')
# Regresi Linear
garis_regresi = intercept + slope * df_clean['Sumbu_X']
ax1.plot(df_clean['Sumbu_X'], garis_regresi, color='red', linewidth=2, label=f'Regresi ($\\rho$ = {rho_estimasi:.3f} g/cm³)')

ax1.set_title('Grafik Metode Parasnis', fontsize=12)
ax1.set_xlabel('0.04193 × Elevasi (Z)', fontsize=10)
ax1.set_ylabel('Free Air Anomaly / FAA (mGal)', fontsize=10)
ax1.legend()
ax1.grid(True, linestyle='--', alpha=0.7)

# GRAFIK 2: Profil ABS
ax2.plot(df_clean['Titik'], df_clean['ABS_mGal'], marker='o', color='green', markersize=3, linewidth=1)

ax2.set_title(f'Profil Anomali Bouguer Sederhana (ABS)', fontsize=12)
ax2.set_xlabel('Titik (Stasiun)', fontsize=10)
ax2.set_ylabel('ABS (mGal)', fontsize=10)
ax2.tick_params(axis='x', rotation=90, labelsize=7)

# Limit 20 Xlabel
ax2.xaxis.set_major_locator(plt.MaxNLocator(20)) 
ax2.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.show()
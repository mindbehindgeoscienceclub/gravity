import pandas as pd
from google.colab import files

# 1.Definisi fungsi (koreksi drift)
def koreksi_drift(I, P):

    I_awal = I.iloc[0]
    I_akhir = I.iloc[-1]

    P_awal = P.iloc[0]
    P_akhir = P.iloc[-1]

    drift = []
    g_corr = []

    for i in range(len(I)):

        if (I_akhir - I_awal) == 0:
            drift_i = 0
        else:
            drift_i = ((I.iloc[i] - I_awal) / (I_akhir - I_awal)) * (P_akhir - P_awal)

        g_corr_i = P.iloc[i] - drift_i

        drift.append(drift_i)
        g_corr.append(g_corr_i)

    hasil = pd.DataFrame({
        "Koreksi Drift": drift,
        "G Terkoreksi Drift": g_corr
    })

    return hasil

# 2.Upload file excel
uploaded = files.upload()
file_name = list(uploaded.keys())[0]

# 3. BACA EXCEL
df = pd.read_excel(file_name)

# 4. PILIH KOLOM
print("DAFTAR KOLOM:")
for i, col in enumerate(df.columns):
    print(i, col)

col_I = int(input("KOLOM WAKTU BERAPA: "))
col_P = int(input("KOLOM GRAVITASI BERAPA: "))


# 5. AMBIL DATA
raw_I = df.iloc[:, col_I].astype(str).str.strip()
raw_P = df.iloc[:, col_P]

# 6. PARSING DATA
# waktu
#I = pd.to_datetime(raw_I, errors='coerce')
#I = I.fillna(pd.to_datetime(raw_I, format='%H:%M:%S', errors='coerce'))

try:
    I = pd.to_datetime(raw_I, format='%H:%M:%S')
except:
    I = pd.to_datetime(raw_I, errors='coerce')

# gravitasi
P = pd.to_numeric(raw_P, errors='coerce')

# 7. BERSIHKAN DATA
data = pd.DataFrame({"I": I, "P": P}).dropna().reset_index(drop=True)

# 8. GABUNG TIAP 3 DATA
data = data.groupby(data.index // 3).mean().reset_index(drop=True)

# 9. UBAH WAKTU KE DETIK
data["I"] = (data["I"] - data["I"].iloc[0]).dt.total_seconds()

I = data["I"]
P = data["P"]

print (I)
print (P)


# 10. HITUNG DRIFT
hasil = koreksi_drift(I, P)

# 11. OUTPUT
print("\nHASIL KOREKSI DRIFT:")
print(hasil)
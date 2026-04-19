import numpy as np
import pandas as pd

def hitung_koreksi(data, rho=2.67):

    # desimal di absolutkan
    data["desimal"] = abs(data["Latitude"])

    # koreksi lintang
    lat_rad= np.radians(data["desimal"])
    data["koreksi_lintang"] = 978031.7 * (1 + 0.0053024 * (np.sin(lat_rad)**2) +
        0.0000059 * (np.sin(2*lat_rad)**2))

    # FAC
    data["FAC"] = -0.3086 * data["Z"]

    # koreksi teoritis
    data["koreksi_teoritis"] = data["koreksi_lintang"] + data["FAC"]

    # Free Air Anomaly
    data["FAA"] = data["G Obs"] - data["koreksi_lintang"] - data["FAC"]

    # Bouguer correction
    data["koreksi_bouguer"] = 0.04193 * rho * data["Z"]

    # ABS
    data["ABS"] = (data["G Obs"]- data["koreksi_lintang"]- data["FAC"] - data["koreksi_bouguer"])

    return data

data = pd.read_csv("D:\DATA MBG PYTHON\GRAVITASI\input koreksi.csv")

print("Data Awal:")
print(data)

data = hitung_koreksi(data)

print("\nHasil Perhitungan:")
print(data[[
    "desimal",
    "koreksi_lintang",
    "FAC",
    "koreksi_teoritis",
    "FAA",
    "koreksi_bouguer",
    "ABS"
]])
# SIMPAN KE EXCEL
data.to_excel("hasil_koreksi_gravitasi.xlsx", index=False)
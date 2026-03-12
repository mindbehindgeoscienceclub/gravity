import numpy as np
import pandas as pd

data = pd.read_csv("/content/drive/MyDrive/input koreksi.csv")  

# Menampilkan data awal
print("Data Awal:")
print(data)

# Desimal
data["desimal"] = data["Latitude"].abs()

#Koreksi Lintang
lat_rad = np.radians(data["desimal"])
data["koreksi_lintang"] = 978031.7 * (1 + 0.0053024 * (np.sin(lat_rad)**2) + 0.0000059 * (np.sin(2*lat_rad)**2))

#FAC
data["FAC"] = (-0.3086) * data["Z"]

#Koreksi Teoritis
data["koreksi_teoritis"] = data["koreksi_lintang"] + data["FAC"]

# Hasil Akhir Koreksi
print("\nHasil Perhitungan:")
print(data[["desimal","koreksi_lintang", "FAC", "koreksi_teoritis"]])

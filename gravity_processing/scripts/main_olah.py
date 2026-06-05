"""
Script utama pengolahan data gravitasi.
Berinteraksi langsung dengan pengguna untuk:
  - Memilih file input
  - Memasukkan parameter instrumen (counter, value, factor)
  - Memasukkan tanggal pengukuran & informasi base station
  - Menjalankan seluruh pipeline pengolahan
  - Menyimpan hasil dan menampilkan grafik

Struktur folder:
    gravity_processing/
    ├── data/
    │   └── data_pengukuran_gravitasi.xlsx (input)
    └── scripts/
        ├── pengolahan_data_gravity.py
        └── main_olah.py  ← file ini
"""

import sys
import os

# Pastikan folder scripts ada di path Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

from pengolahan_data_gravity import (
    konversi_skala_bacaan,
    koreksi_pasut,
    koreksi_tinggi_alat,
    rata_rata_bacaan,
    koreksi_drift,
    hitung_g_obs,
    koreksi_lintang,
    koreksi_udara_bebas,
    hitung_faa,
    koreksi_bouguer,
    hitung_abs,
    metode_parasnis,
    hitung_abl,
    koreksi_medan_harmonica,
    pipeline_lengkap,
)


# HELPER: INPUT DENGAN NILAI DEFAULT
#========================================================================

def input_default(prompt: str, default):
    """Meminta input pengguna; jika kosong, kembalikan nilai default."""
    val = input(f"{prompt} [{default}]: ").strip()
    return val if val else str(default)


def input_float(prompt: str, default: float) -> float:
    while True:
        try:
            return float(input_default(prompt, default))
        except ValueError:
            print("  ✗ Masukkan angka desimal yang valid.")


def input_int(prompt: str, default: int) -> int:
    while True:
        try:
            return int(input_default(prompt, default))
        except ValueError:
            print("  ✗ Masukkan bilangan bulat yang valid.")


#========================================================================
# FUNGSI VISUALISASI
#========================================================================

def tampilkan_grafik(df_hasil: pd.DataFrame,
                     hasil_parasnis: dict,
                     nama_output_gambar: str):
    """Membuat 4 panel grafik ringkasan hasil pengolahan."""

    titik = df_hasil["Nama Titik"].values
    x_idx = np.arange(len(titik))

    fig = plt.figure(figsize=(18, 12))
    fig.suptitle("Hasil Pengolahan Data Gravitasi", fontsize=14, fontweight="bold")
    gs  = gridspec.GridSpec(2, 2, hspace=0.42, wspace=0.32)

    # Panel 1: Metode Parasnis
    ax1 = fig.add_subplot(gs[0, 0])
    xp  = hasil_parasnis["x_parasnis"]
    yp  = hasil_parasnis["y_parasnis"]
    rho = hasil_parasnis["rho_estimasi"]
    r2  = hasil_parasnis["r_squared"]
    ax1.scatter(xp, yp, color="steelblue", alpha=0.7, zorder=3, label="Data")
    ax1.plot(xp, hasil_parasnis["garis_regresi"], color="red", lw=2,
             label=f"Regresi  ρ = {rho:.3f} g/cm³\nR² = {r2:.4f}")
    ax1.set_title("Metode Parasnis", fontsize=11)
    ax1.set_xlabel("0.04193 × Z (elevasi)", fontsize=9)
    ax1.set_ylabel("FAA (mGal)", fontsize=9)
    ax1.legend(fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Panel 2: G Obs
    ax2 = fig.add_subplot(gs[0, 1])
    if "G_obs" in df_hasil.columns:
        ax2.plot(x_idx, df_hasil["G_obs"].values, "o-", color="darkorange",
                 markersize=4, lw=1.2)
        ax2.set_title("Profil G Observasi", fontsize=11)
        ax2.set_xlabel("Stasiun", fontsize=9)
        ax2.set_ylabel("G Obs (mGal)", fontsize=9)
        ax2.set_xticks(x_idx)
        ax2.set_xticklabels(titik, rotation=75, fontsize=7)
        ax2.grid(True, linestyle="--", alpha=0.5)

    # Panel 3: FAA
    ax3 = fig.add_subplot(gs[1, 0])
    if "FAA" in df_hasil.columns:
        ax3.plot(x_idx, df_hasil["FAA"].values, "s-", color="mediumseagreen",
                 markersize=4, lw=1.2)
        ax3.axhline(0, color="black", lw=0.8, linestyle=":")
        ax3.set_title("Free Air Anomaly (FAA)", fontsize=11)
        ax3.set_xlabel("Stasiun", fontsize=9)
        ax3.set_ylabel("FAA (mGal)", fontsize=9)
        ax3.set_xticks(x_idx)
        ax3.set_xticklabels(titik, rotation=75, fontsize=7)
        ax3.grid(True, linestyle="--", alpha=0.5)

    # Panel 4: ABS dan ABL
    ax4 = fig.add_subplot(gs[1, 1])
    if "ABS" in df_hasil.columns:
        ax4.plot(x_idx, df_hasil["ABS"].values, "o-", color="royalblue",
                 markersize=4, lw=1.2, label=f"ABS (ρ={2.67})")
    if "ABS_parasnis" in df_hasil.columns:
        ax4.plot(x_idx, df_hasil["ABS_parasnis"].values, "^--", color="purple",
                 markersize=4, lw=1.0, label=f"ABS Parasnis (ρ={rho:.3f})")
    if "ABL" in df_hasil.columns and not df_hasil["ABL"].isna().all():
        ax4.plot(x_idx, df_hasil["ABL"].values, "D-", color="firebrick",
                 markersize=4, lw=1.2, label="ABL")
    ax4.axhline(0, color="black", lw=0.8, linestyle=":")
    ax4.set_title("Anomali Bouguer", fontsize=11)
    ax4.set_xlabel("Stasiun", fontsize=9)
    ax4.set_ylabel("Anomali (mGal)", fontsize=9)
    ax4.set_xticks(x_idx)
    ax4.set_xticklabels(titik, rotation=75, fontsize=7)
    ax4.legend(fontsize=8)
    ax4.grid(True, linestyle="--", alpha=0.5)

    plt.savefig(nama_output_gambar, dpi=150, bbox_inches="tight")
    print(f"\n  ✓ Grafik disimpan: {nama_output_gambar}")
    plt.show()


#========================================================================
# FUNGSI VISUALISASI PETA
#========================================================================

def tampilkan_peta(df_hasil,
                   kolom_nilai,
                   nama_label,
                   nama_output_gambar,
                   col_lon="Longitude",
                   col_lat="Latitude"):
    """
    Membuat peta sebaran anomali gravitasi (scatter map + interpolasi kontur).

    Parameters
    ----------
    df_hasil           : DataFrame hasil pengolahan
    kolom_nilai        : kolom anomali ('ABS', 'ABS_parasnis', atau 'ABL')
    nama_label         : label colorbar / judul peta
    nama_output_gambar : path simpan gambar (.png)
    col_lon            : nama kolom Longitude
    col_lat            : nama kolom Latitude
    """
    from scipy.interpolate import griddata

    # Cek ketersediaan koordinat
    if col_lon not in df_hasil.columns or col_lat not in df_hasil.columns:
        print(f"  \u26a0 Kolom koordinat '{col_lon}' / '{col_lat}' tidak ditemukan.")
        print("    Peta membutuhkan kolom Longitude dan Latitude pada data input.")
        print("    Lewati pembuatan peta.")
        return

    df_peta = df_hasil[[col_lon, col_lat, kolom_nilai, "Nama Titik"]].dropna()
    if df_peta.empty:
        print(f"  \u26a0 Tidak ada data valid untuk '{kolom_nilai}'. Peta dilewati.")
        return

    lon = df_peta[col_lon].astype(float).values
    lat = df_peta[col_lat].astype(float).values
    val = df_peta[kolom_nilai].astype(float).values

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle(f"Peta {nama_label}", fontsize=13, fontweight="bold")

    # ---- Panel kiri: scatter titik ----
    ax1 = axes[0]
    sc = ax1.scatter(lon, lat, c=val, cmap="RdYlBu_r", s=80,
                     edgecolors="k", linewidths=0.5, zorder=3)
    cb = plt.colorbar(sc, ax=ax1, shrink=0.85)
    cb.set_label(f"{nama_label} (mGal)", fontsize=9)
    for _, row in df_peta.iterrows():
        ax1.annotate(row["Nama Titik"],
                     xy=(row[col_lon], row[col_lat]),
                     xytext=(3, 3), textcoords="offset points",
                     fontsize=7, color="black")
    ax1.set_title("Sebaran Titik Pengukuran", fontsize=10)
    ax1.set_xlabel("Longitude", fontsize=9)
    ax1.set_ylabel("Latitude", fontsize=9)
    ax1.grid(True, linestyle="--", alpha=0.4)

    # ---- Panel kanan: interpolasi kontur ----
    ax2 = axes[1]
    if len(df_peta) >= 4:
        lon_grid = np.linspace(lon.min(), lon.max(), 150)
        lat_grid = np.linspace(lat.min(), lat.max(), 150)
        LON, LAT = np.meshgrid(lon_grid, lat_grid)
        VAL_interp = griddata((lon, lat), val, (LON, LAT), method="cubic")

        cf = ax2.contourf(LON, LAT, VAL_interp, levels=15, cmap="RdYlBu_r", alpha=0.85)
        ax2.contour(LON, LAT, VAL_interp, levels=15, colors="k",
                    linewidths=0.4, alpha=0.5)
        cb2 = plt.colorbar(cf, ax=ax2, shrink=0.85)
        cb2.set_label(f"{nama_label} (mGal)", fontsize=9)
        ax2.scatter(lon, lat, c="white", s=30, edgecolors="k",
                    linewidths=0.6, zorder=4)
        for _, row in df_peta.iterrows():
            ax2.annotate(row["Nama Titik"],
                         xy=(row[col_lon], row[col_lat]),
                         xytext=(3, 3), textcoords="offset points",
                         fontsize=7, color="white")
        ax2.set_title("Peta Kontur Interpolasi (Cubic)", fontsize=10)
    else:
        ax2.text(0.5, 0.5,
                 "Data terlalu sedikit\nuntuk interpolasi\n(butuh minimal 4 titik)",
                 ha="center", va="center", transform=ax2.transAxes, fontsize=11)
        ax2.set_title("Peta Kontur (tidak tersedia)", fontsize=10)

    ax2.set_xlabel("Longitude", fontsize=9)
    ax2.set_ylabel("Latitude", fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig(nama_output_gambar, dpi=150, bbox_inches="tight")
    print(f"  \u2713 Peta disimpan: {nama_output_gambar}")
    plt.show()


#========================================================================
# FUNGSI UTAMA
#========================================================================

def main():
    print("=" * 65)
    print("     PENGOLAHAN DATA GRAVITASI – BACAAN ALAT ke ABL")
    print("=" * 65)

    #(A) File input 
    print("\n[1] FILE INPUT")
    default_path = str(Path(__file__).parent.parent / "data" /
                        "data_pengukuran_gravitasi.xlsx")
    file_input = input_default("  Path file data pengukuran (.xlsx)", default_path)

    if not os.path.isfile(file_input):
        print(f"  ✗ File tidak ditemukan: {file_input}")
        sys.exit(1)

    # Baca preview kolom
    df_raw = pd.read_excel(file_input)
    print(f"\n  ✓ File berhasil dibaca: {len(df_raw)} baris")
    print("  Kolom yang ditemukan:")
    for i, c in enumerate(df_raw.columns):
        print(f"    [{i}] {c}")

    # (B) Mapping kolom 
    print("\n[2] MAPPING KOLOM")
    print("  (Tekan Enter untuk menggunakan nama kolom default)")

    col_titik   = input_default("  Nama kolom 'Nama Titik'", "Nama Titik")
    col_waktu   = input_default("  Nama kolom waktu desimal", "Jam (GMT+7)")
    col_skala   = input_default("  Nama kolom skala bacaan", "Skala Bacaan")
    col_ta      = input_default("  Nama kolom tinggi alat (cm)", "TA (cm)")
    col_elevasi = input_default("  Nama kolom elevasi (m)", "Elev (m)")
    col_lat     = input_default("  Nama kolom latitude (kosongkan jika tidak ada)", "")
    col_tc      = input_default("  Nama kolom terrain correction (kosongkan jika tidak ada)", "")

    # Rename ke nama standar
    rename_map = {}
    for std, usr in [("Nama Titik", col_titik), ("Jam (GMT+7)", col_waktu),
                     ("Skala Bacaan", col_skala), ("TA (cm)", col_ta),
                     ("Elev (m)", col_elevasi)]:
        if usr and usr != std and usr in df_raw.columns:
            rename_map[usr] = std

    if col_lat and col_lat in df_raw.columns and col_lat != "Latitude":
        rename_map[col_lat] = "Latitude"
    if col_tc and col_tc in df_raw.columns and col_tc != "terrain_correction_mGal":
        rename_map[col_tc] = "terrain_correction_mGal"

    df_raw = df_raw.rename(columns=rename_map)

    # (C) Parameter instrumen 
    print("\n[3] PARAMETER INSTRUMEN (Counter / Value / Factor)")
    print("  Masukkan jumlah interval konversi (biasanya 3):")
    n_interval = input_int("  Jumlah interval", 3)

    counter_reading    = []
    value_in_mGal      = []
    factor_for_interval= []

    for i in range(n_interval):
        print(f"\n  -- Interval ke-{i+1} --")
        defaults_cr  = [1800, 1700, 1600]
        defaults_vim = [1906.96, 1801.03, 1695.11]
        defaults_ffi = [1.05930, 1.05929, 1.05925]
        cr  = input_float(f"    Counter reading [{i+1}]",
                          defaults_cr[i] if i < 3 else 0)
        vim = input_float(f"    Value in mGal  [{i+1}]",
                          defaults_vim[i] if i < 3 else 0)
        ffi = input_float(f"    Factor for interval [{i+1}]",
                          defaults_ffi[i] if i < 3 else 1)
        counter_reading.append(cr)
        value_in_mGal.append(vim)
        factor_for_interval.append(ffi)

    #(D) Informasi base station 
    print("\n[4] INFORMASI BASE STATION")
    print("  Contoh G absolut:")
    print("    Jogja (FKH UGM)  : 978198.417 mGal")
    print("    Jakarta (BMKG)   : 978083.000 mGal")
    g_absolut_base = input_float("  Nilai G absolut base station (mGal)", 978198.417)

    lat_base = input_float("  Latitude base station (decimal, negatif = S)", -7.782706)
    lon_base = input_float("  Longitude base station (decimal)", 110.480931)

    # (E) Tanggal pengukuran 
    print("\n[5] TANGGAL PENGUKURAN")
    tanggal = input_default("  Tanggal pengukuran (YYYY-MM-DD)", "2023-05-15")
    # Validasi format
    try:
        from datetime import datetime
        datetime.strptime(tanggal, "%Y-%m-%d")
    except ValueError:
        print("  ✗ Format tanggal salah. Gunakan YYYY-MM-DD.")
        sys.exit(1)

    # (F) Densitas rho 
    print("\n[6] DENSITAS BATUAN")
    rho = input_float("  Nilai densitas ρ untuk koreksi Bouguer (g/cm³)", 2.67)

    # (G) Pilih penggunaan model pasut 
    print("\n[7] KOREKSI PASUT")
    print("  [1] Hitung otomatis dengan model analitik (Longman)")
    print("  [2] Masukkan nilai pasut dari GravTC / Etide (kolom tersedia di file)")
    pilih_pasut = input_default("  Pilihan", "1")

    gunakan_pasut_model = True
    if pilih_pasut == "2":
        col_pasut = input_default("  Nama kolom pasut di file", "Pasut (mGal)")
        if col_pasut in df_raw.columns:
            df_raw["pasut_mGal_eksternal"] = pd.to_numeric(df_raw[col_pasut], errors="coerce").fillna(0)
            gunakan_pasut_model = False
            print("  ✓ Akan menggunakan nilai pasut dari file.")
        else:
            print(f"  ⚠ Kolom '{col_pasut}' tidak ditemukan. Menggunakan model otomatis.")

    # (H) Koreksi Medan Otomatis (Terrain Correction)
    print("\n[8] KOREKSI MEDAN (TERRAIN CORRECTION)")
    print("  [1] Otomatis dari DEM GeoTIFF (harmonica – disarankan)")
    print("  [2] Gunakan kolom TC dari file data")
    print("  [3] Lewati (ABL tidak dihitung)")
    pilih_tc = input_default("  Pilihan", "3")

    path_dem     = None
    col_easting  = "X"
    col_northing = "Y"
    densitas_tc  = 2670.0
    coarsen_tc   = 10

    if pilih_tc == "1":
        path_dem = input_default("  Path file DEM GeoTIFF (.tif)", "dem.tif")
        if not os.path.isfile(path_dem):
            print(f"  \u26a0 File DEM tidak ditemukan: {path_dem}")
            print("    TC otomatis dinonaktifkan. ABL tidak akan dihitung.")
            path_dem = None
        else:
            col_easting  = input_default("  Nama kolom Easting (X, UTM meter)", "X")
            col_northing = input_default("  Nama kolom Northing (Y, UTM meter)", "Y")
            densitas_tc  = input_float("  Densitas batuan untuk TC (kg/m\u00b3)", 2670.0)
            coarsen_tc   = input_int("  Faktor downsampling DEM (1=penuh, 10=cepat)", 10)
            # Pastikan kolom easting/northing tersedia di df_raw
            if col_easting not in df_raw.columns or col_northing not in df_raw.columns:
                print(f"  \u26a0 Kolom '{col_easting}' / '{col_northing}' tidak ada di file.")
                print("    Tambahkan koordinat UTM pada file input, lalu ulangi.")
                path_dem = None

    elif pilih_tc == "2":
        col_tc_file = input_default("  Nama kolom TC di file", "terrain_correction_mGal")
        if col_tc_file in df_raw.columns:
            if col_tc_file != "terrain_correction_mGal":
                df_raw = df_raw.rename(columns={col_tc_file: "terrain_correction_mGal"})
            print("  \u2713 Akan menggunakan TC dari kolom file.")
        else:
            print(f"  \u26a0 Kolom '{col_tc_file}' tidak ditemukan. TC dilewati.")

    # (I) Jalankan pipeline 
    print("\n" + "=" * 65)
    print("  Menjalankan pipeline pengolahan...")
    print("=" * 65)

    # Tambahkan latitude dari file jika ada, atau gunakan lat_base
    if "Latitude" not in df_raw.columns:
        df_raw["Latitude"] = lat_base

    try:
        df_hasil, hasil_parasnis = pipeline_lengkap(
            df_raw=df_raw,
            counter_reading=counter_reading,
            value_in_mGal=value_in_mGal,
            factor_for_interval=factor_for_interval,
            g_absolut_base=g_absolut_base,
            tanggal=tanggal,
            latitude_base=lat_base,
            longitude_base=lon_base,
            rho=rho,
            gunakan_pasut_model=gunakan_pasut_model,
            path_dem=path_dem,
            col_easting=col_easting,
            col_northing=col_northing,
            densitas_tc=densitas_tc,
            coarsen_tc=coarsen_tc,
        )
    except Exception as e:
        print(f"\n  ✗ Error saat pengolahan: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # (I) Cetak hasil ringkasan 
    print("\n" + "=" * 65)
    print("  HASIL PENGOLAHAN")
    print("=" * 65)

    kolom_tampil = ["Nama Titik", "Elev (m)", "G_obs", "FAA",
                    "koreksi_bouguer", "ABS", "ABS_parasnis"]
    if "ABL" in df_hasil.columns and not df_hasil["ABL"].isna().all():
        kolom_tampil.append("ABL")

    kolom_tampil = [c for c in kolom_tampil if c in df_hasil.columns]
    print(df_hasil[kolom_tampil].to_string(index=False, float_format="{:.4f}".format))

    print(f"\n  === HASIL METODE PARASNIS ===")
    print(f"  Densitas estimasi (ρ) : {hasil_parasnis['rho_estimasi']:.3f} g/cm³")
    print(f"  Intercept             : {hasil_parasnis['intercept']:.4f}")
    print(f"  R²                    : {hasil_parasnis['r_squared']:.4f}")

    # (J) Simpan output
    print("\n[8] SIMPAN OUTPUT")
    output_dir = str(Path(file_input).parent)
    default_out = os.path.join(output_dir, "hasil_pengolahan_gravitasi.xlsx")
    file_output = input_default("  Path file output (.xlsx)", default_out)

    # Kolom output lengkap yang relevan
    kolom_output = [
        "Nama Titik", "Jam (GMT+7)", "waktu_detik",
        "Skala Bacaan", "konversi_skala",
        "pasut_mGal", "G_terkoreksi_pasut",
        "TA (cm)", "koreksi_TA", "G_terkoreksi_TA",
        "koreksi_drift", "G_terkoreksi_drift",
        "delta_G", "G_obs",
        "Elev (m)", "G_lintang", "FAC", "FAA",
        "koreksi_bouguer", "ABS",
        "BC_parasnis", "ABS_parasnis",
    ]
    if "terrain_correction_mGal" in df_hasil.columns:
        kolom_output.append("terrain_correction_mGal")
    if "ABL" in df_hasil.columns:
        kolom_output.append("ABL")

    kolom_output = [c for c in kolom_output if c in df_hasil.columns]

    try:
        df_hasil[kolom_output].to_excel(file_output, index=False)
        print(f"  ✓ Hasil disimpan: {file_output}")
    except Exception as e:
        print(f"  ✗ Gagal menyimpan: {e}")

    # (K) Visualisasi profil 
    print("\n[9] VISUALISASI PROFIL")
    buat_grafik = input_default("  Tampilkan & simpan grafik profil? (y/n)", "y").lower()
    if buat_grafik == "y":
        gambar_path = file_output.replace(".xlsx", "_grafik.png")
        tampilkan_grafik(df_hasil, hasil_parasnis, gambar_path)

    # (L) Peta anomali
    print("\n[10] PETA ANOMALI GRAVITASI")
    print("  Peta membutuhkan kolom Latitude & Longitude di data input.")
    print("  Pilih peta yang ingin ditampilkan:")
    print("  [1] Peta ABS (Anomali Bouguer Sederhana, rho=2.67)")
    print("  [2] Peta ABS Parasnis (rho estimasi)")
    has_abl = "ABL" in df_hasil.columns and not df_hasil["ABL"].isna().all()
    if has_abl:
        print("  [3] Peta ABL (Anomali Bouguer Lengkap)")
        print("  [4] Peta ABS dan ABL (keduanya)")
        print("  [5] Lewati")
    else:
        print("  [3] Lewati  (ABL tidak tersedia – jalankan TC terlebih dahulu)")

    pilih_peta = input_default("  Pilihan", "5" if not has_abl else "4")

    # Pastikan kolom koordinat tersedia
    col_lon_peta = "Longitude"
    col_lat_peta = "Latitude"
    if col_lon_peta not in df_hasil.columns:
        col_lon_peta = input_default(
            "  Nama kolom Longitude di hasil", "Longitude").strip() or "Longitude"
    if col_lat_peta not in df_hasil.columns:
        col_lat_peta = input_default(
            "  Nama kolom Latitude di hasil", "Latitude").strip() or "Latitude"

    def _buat_peta(kolom, label, suffix):
        path_peta = file_output.replace(".xlsx", f"_{suffix}.png")
        tampilkan_peta(df_hasil, kolom, label, path_peta, col_lon_peta, col_lat_peta)

    if pilih_peta == "1":
        _buat_peta("ABS", "Anomali Bouguer Sederhana (ABS)", "peta_abs")
    elif pilih_peta == "2":
        _buat_peta("ABS_parasnis", "ABS Parasnis", "peta_abs_parasnis")
    elif pilih_peta == "3" and has_abl:
        _buat_peta("ABL", "Anomali Bouguer Lengkap (ABL)", "peta_abl")
    elif pilih_peta == "4" and has_abl:
        _buat_peta("ABS", "Anomali Bouguer Sederhana (ABS)", "peta_abs")
        _buat_peta("ABL", "Anomali Bouguer Lengkap (ABL)", "peta_abl")
    else:
        print("  Pembuatan peta dilewati.")

    print("\n" + "=" * 65)
    print("  Pengolahan selesai.")
    print("=" * 65)


# ========================================================================
# ENTRY POINT
# ========================================================================

if __name__ == "__main__":
    main()

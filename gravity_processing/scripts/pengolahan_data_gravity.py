"""
Modul berisi semua fungsi pengolahan data gravitasi:
  1. konversi_skala_bacaan   : Skala bacaan - mGal
  2. koreksi_pasut           : Koreksi efek pasang surut (model Longman 1959)
  3. koreksi_tinggi_alat     : Koreksi tinggi alat (TA)
  4. rata_rata_bacaan        : Rata-rata 3 bacaan per titik
  5. koreksi_drift           : Koreksi drift instrumen (linear interpolasi)
  6. hitung_g_obs            : Delta-G - G absolut (G Obs)
  7. koreksi_lintang         : Gravitasi Normal 
  8. koreksi_udara_bebas     : Free Air Correction (FAC)
  9. hitung_faa              : Free Air Anomaly
 10. koreksi_bouguer         : Koreksi Bouguer Sederhana
 11. hitung_abs              : Anomali Bouguer Sederhana (ABS)
 12. metode_parasnis         : Estimasi densitas batuan via regresi Parasnis
 13. hitung_abl              : Anomali Bouguer Lengkap (ABL) = ABS - TC
 14. pipeline_lengkap        : Menjalankan seluruh tahap sekaligus

Catatan:
  - Koreksi pasut menggunakan model sederhana berbasis harmonik.
    Untuk hasil presisi tinggi, gunakan software GravTC / Etide.
  - Koreksi medan (TC) dihitung secara eksternal (harmonica/prism_gravity)
    dan cukup dimasukkan sebagai kolom 'terrain_correction_mGal' pada DataFrame.
"""

import numpy as np
import pandas as pd
from scipy.stats import linregress
import math


# ================================================================================
# 1. KONVERSI SKALA BACAAN - mGal
# =================================================================================

def konversi_skala_bacaan(skala: np.ndarray,
                          counter_reading: np.ndarray,
                          value_in_mGal: np.ndarray,
                          factor_for_interval: np.ndarray) -> np.ndarray:
    skala = np.asarray(skala, dtype=float)
    hasil = np.full_like(skala, np.nan)

    # Urutkan dari counter terbesar ke terkecil
    order = np.argsort(counter_reading)[::-1]
    cr_sorted  = np.asarray(counter_reading)[order]
    vim_sorted = np.asarray(value_in_mGal)[order]
    ffi_sorted = np.asarray(factor_for_interval)[order]

    for idx, s in enumerate(skala):
        for i, cr in enumerate(cr_sorted):
            if s >= cr:
                hasil[idx] = vim_sorted[i] + (s - cr_sorted[i]) * ffi_sorted[i]
                break
        else:
            # Gunakan interval terkecil jika di bawah semua counter
            hasil[idx] = vim_sorted[-1] + (s - cr_sorted[-1]) * ffi_sorted[-1]

    return hasil


# ================================================================================
# 2. KOREKSI PASUT (MODEL LONGMAN 1959 – DISEDERHANAKAN)
# ================================================================================  

def _julian_day(year: int, month: int, day: int,
                hour: float = 0.0) -> float:
    """Konversi tanggal ke Julian Day Number (UT)."""
    if month <= 2:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + hour / 24.0 + B - 1524.5


def koreksi_pasut(waktu_desimal: np.ndarray,
                  latitude: float,
                  longitude: float,
                  tanggal: str) -> np.ndarray:
    from datetime import datetime

    dt  = datetime.strptime(tanggal, "%Y-%m-%d")
    doy = dt.timetuple().tm_yday  # day of year

    lat_r  = math.radians(latitude)
    lon_r  = math.radians(longitude)

    waktu_desimal = np.asarray(waktu_desimal, dtype=float)
    pasut = np.zeros_like(waktu_desimal)

    for i, t in enumerate(waktu_desimal):
        # Waktu dalam jam UT (GMT)
        hour_ut = t * 24.0

        # Julian date
        jd = _julian_day(dt.year, dt.month, dt.day, hour_ut)

        # T = Julian centuries since J2000.0
        T = (jd - 2451545.0) / 36525.0

        # Argumen lunar/solar (rad) 
        # Mean longitude of Moon (deg)
        L_moon = (218.3165 + 481267.8813 * T) % 360.0
        # Mean anomaly of Moon
        M_moon = math.radians((134.9634 + 477198.8676 * T) % 360.0)
        # Mean anomaly of Sun
        M_sun  = math.radians((357.5291 + 35999.0503 * T) % 360.0)
        # Mean elongation Moon-Sun
        D      = math.radians((297.8502 + 445267.1115 * T) % 360.0)
        # Argument of latitude of Moon
        F      = math.radians((93.2721 + 483202.0175 * T) % 360.0)
        # GMST at 0h (rad)
        theta0 = math.radians((100.4606 + 36000.7700 * T) % 360.0)

        # Hour angle of Moon (approx)
        tau_m  = theta0 + lon_r - math.radians(L_moon) + (hour_ut / 24.0) * 2 * math.pi

        # Konstanta gravitasi & ukuran (CGS)
        G   = 6.674e-8        # gravitasi Newton
        M_m = 7.342e25        # massa Bulan (g)
        M_s = 1.989e33        # massa Matahari (g)
        r_m = 3.844e10        # jarak rata-rata Bumi-Bulan (cm)
        r_s = 1.496e13        # jarak rata-rata Bumi-Matahari (cm)
        R   = 6.371e8         # jari-jari Bumi (cm)

        # Koreksi jarak bulan (anomali)
        r_m_eff = r_m * (1 - 0.0549 * math.cos(M_moon))
        r_s_eff = r_s * (1 - 0.0167 * math.cos(M_sun))

        # Deklinasi Bulan (approx)
        i_m = math.radians(23.45)  # inklinasi ekliptika
        sin_d_m = math.sin(i_m) * math.sin(F)
        d_m = math.asin(sin_d_m)

        sin_d_s = math.sin(i_m) * math.sin(math.radians((280.46 + 0.9856 * doy) % 360.0))
        d_s = math.asin(sin_d_s)

        # Faktor amplitude
        A_m = G * M_m * R / r_m_eff**3  
        A_s = G * M_s * R / r_s_eff**3

        # Pasut komponen utama (Darwin M2, S2, O1, K1, N2, P1)
        # Persamaan Longman compact form:
        p1 = (3 * math.sin(lat_r)**2 - 1) / 2
        p2 = math.sin(2 * lat_r)
        p3 = math.cos(lat_r)**2

        g_m = A_m * 1e3 * (
            p1 * (3 * math.sin(d_m)**2 - 1)
            + p2 * math.sin(2 * d_m) * math.cos(tau_m)
            + p3 * math.cos(d_m)**2 * math.cos(2 * tau_m)
        )
        # Solar term (rasio ~0.46)
        g_s = 0.4612 * A_s * 1e3 * (
            p1 * (3 * math.sin(d_s)**2 - 1)
            + p2 * math.sin(2 * d_s) * math.cos(tau_m * 0.9973)
            + p3 * math.cos(d_s)**2 * math.cos(2 * tau_m * 0.9973)
        )

        pasut[i] = g_m + g_s

    return pasut


# ================================================================================
# 3. KOREKSI TINGGI ALAT (TA)
# ================================================================================

def koreksi_tinggi_alat(ta_cm: np.ndarray) -> np.ndarray:
    ta_cm = np.asarray(ta_cm, dtype=float)
    return -0.3086 * (ta_cm / 100.0)

# ================================================================================
# 4. RATA-RATA 3 BACAAN PER TITIK (setelah koreksi pasut & TA)
# ================================================================================

def rata_rata_bacaan(df: pd.DataFrame,
                     kolom_g_terkoreksi: str = "G_terkoreksi_TA",
                     kolom_waktu: str = "waktu_desimal",
                     kolom_titik: str = "Nama Titik") -> pd.DataFrame:
    df = df.copy().reset_index(drop=True)

    # Isi Nama Titik yang kosong dengan forward-fill
    df[kolom_titik] = df[kolom_titik].replace("", np.nan).ffill()

    # Buat label grup per urutan kemunculan (BASE awal & Base akhir tetap dipisah)
    grup_id = (df[kolom_titik] != df[kolom_titik].shift()).cumsum()
    df["_grup_id"] = grup_id

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    str_cols     = [c for c in df.columns
                    if c not in numeric_cols and c not in ["_grup_id", kolom_titik]]

    agg_dict = {c: "mean" for c in numeric_cols if c != "_grup_id"}
    agg_dict.update({c: "first" for c in str_cols})
    agg_dict[kolom_titik] = "first"

    df_avg = df.groupby("_grup_id", sort=True).agg(agg_dict).reset_index(drop=True)
    return df_avg


# ================================================================================
# 5. KOREKSI DRIFT
# ================================================================================

def koreksi_drift(waktu_detik: pd.Series,
                  g_bacaan: pd.Series) -> pd.DataFrame:

    t = waktu_detik.reset_index(drop=True)
    g = g_bacaan.reset_index(drop=True)

    t_awal, t_akhir = t.iloc[0], t.iloc[-1]
    g_awal, g_akhir = g.iloc[0], g.iloc[-1]

    dt = t_akhir - t_awal
    dg = g_akhir - g_awal

    if dt == 0:
        drift = pd.Series(np.zeros(len(t)))
    else:
        drift = ((t - t_awal) / dt) * dg

    g_corr = g - drift

    return pd.DataFrame({
        "koreksi_drift": drift.values,
        "G_terkoreksi_drift": g_corr.values
    })


# ================================================================================
# 6. G OBS
# ================================================================================

def hitung_g_obs(g_terkoreksi_drift: pd.Series,
                 g_absolut_base: float) -> pd.DataFrame:
    g = g_terkoreksi_drift.reset_index(drop=True)
    base_val = g.iloc[0]
    delta_g  = g - base_val
    g_obs    = g_absolut_base + delta_g

    return pd.DataFrame({
        "delta_G": delta_g.values,
        "G_obs":   g_obs.values
    })


# ================================================================================
# 7. KOREKSI LINTANG (Gravitasi Normal – GRS67)
# ================================================================================

def koreksi_lintang(latitude: np.ndarray) -> np.ndarray:
    lat_r = np.radians(np.abs(np.asarray(latitude, dtype=float)))
    return 978031.7 * (1.0 + 0.0053024 * np.sin(lat_r)**2
                           - 0.0000059 * np.sin(2 * lat_r)**2)


# ================================================================================
# 8. FREE AIR CORRECTION (FAC)
# ================================================================================

def koreksi_udara_bebas(elevasi_m: np.ndarray) -> np.ndarray:
    return -0.3086 * np.asarray(elevasi_m, dtype=float)


# ================================================================================
# 9. FREE AIR ANOMALY (FAA)
# ================================================================================

def hitung_faa(g_obs: np.ndarray,
               g_lintang: np.ndarray,
               fac: np.ndarray) -> np.ndarray:
    return (np.asarray(g_obs)    - np.asarray(g_lintang)
            - np.asarray(fac))


# ================================================================================
# 10. KOREKSI BOUGUER
# ================================================================================

def koreksi_bouguer(elevasi_m: np.ndarray,
                    rho: float = 2.67) -> np.ndarray:
    return 0.04193 * rho * np.asarray(elevasi_m, dtype=float)


# ================================================================================
# 11. ANOMALI BOUGUER SEDERHANA (ABS)
# ================================================================================

def hitung_abs(faa: np.ndarray,
               bc: np.ndarray) -> np.ndarray:
    return np.asarray(faa) - np.asarray(bc)


# ================================================================================
# 12. METODE PARASNIS 
# ================================================================================

def metode_parasnis(faa: np.ndarray,
                    elevasi_m: np.ndarray) -> dict:
    faa = np.asarray(faa, dtype=float)
    z   = np.asarray(elevasi_m, dtype=float)

    mask = ~(np.isnan(faa) | np.isnan(z))
    x = 0.04193 * z[mask]
    y = faa[mask]

    slope, intercept, r_value, _, _ = linregress(x, y)

    return {
        "rho_estimasi":  slope,
        "intercept":     intercept,
        "r_squared":     r_value**2,
        "x_parasnis":    x,
        "y_parasnis":    y,
        "garis_regresi": intercept + slope * x,
    }


# ================================================================================
# 13. ANOMALI BOUGUER LENGKAP (ABL)
# ================================================================================

def hitung_abl(abs_mgal: np.ndarray,
               terrain_correction: np.ndarray) -> np.ndarray:
    return np.asarray(abs_mgal) - np.asarray(terrain_correction)


# ================================================================================
# 14. KOREKSI MEDAN OTOMATIS (Harmonica – Prism Gravity)
# ================================================================================

def koreksi_medan_harmonica(
    easting: np.ndarray,
    northing: np.ndarray,
    elevasi_m: np.ndarray,
    path_dem: str,
    densitas: float = 2670.0,
    padding_m: float = 20000.0,
    coarsen_factor: int = 10,
) -> np.ndarray:
    try:
        import rioxarray
        import harmonica as hm
        import verde as vd
    except ImportError as e:
        raise ImportError(
            "Paket tambahan diperlukan untuk koreksi medan otomatis.\n"
            "Jalankan: pip install harmonica verde rioxarray\n"
            f"Detail error: {e}"
        )

    easting  = np.asarray(easting,  dtype=float)
    northing = np.asarray(northing, dtype=float)
    elevasi_m = np.asarray(elevasi_m, dtype=float)

    print(f"  → Memuat DEM dari: {path_dem}")
    dem = (
        rioxarray.open_rasterio(path_dem, masked=True)
        .squeeze()
        .rename({"x": "easting", "y": "northing"})
    )

    # Crop DEM sesuai region pengukuran + padding
    region = vd.get_region((easting, northing))
    region = vd.pad_region(region, pad=padding_m)

    dem_crop = dem.sel(
        easting =slice(region[0], region[1]),
        northing=slice(region[3], region[2]),
    )

    if dem_crop.size == 0:
        raise ValueError(
            "DEM setelah crop tidak mengandung data. "
            "Pastikan DEM mencakup area pengukuran dan berada dalam sistem koordinat yang sama."
        )

    # Downsampling DEM untuk efisiensi komputasi
    dem_ds = dem_crop.coarsen(
        easting =coarsen_factor,
        northing=coarsen_factor,
        boundary="trim",
    ).mean()

    # Hitung dimensi prisma
    dx = float(abs(dem_ds.easting [1] - dem_ds.easting [0]))
    dy = float(abs(dem_ds.northing[1] - dem_ds.northing[0]))

    E, N = np.meshgrid(dem_ds.easting.values, dem_ds.northing.values)
    top    = dem_ds.values.ravel()
    bottom = np.zeros_like(top)

    # Hilangkan prisma dengan top ≤ 0 (laut / nodata)
    valid  = np.isfinite(top) & (top > 0)
    prisms = np.column_stack([
        (E.ravel()[valid] - dx / 2),
        (E.ravel()[valid] + dx / 2),
        (N.ravel()[valid] - dy / 2),
        (N.ravel()[valid] + dy / 2),
        bottom[valid],
        top   [valid],
    ])
    densities = np.full(prisms.shape[0], densitas)

    print(f"  → Menghitung gaya tarik dari {prisms.shape[0]:,} prisma...")

    # Hitung gravitasi (m/s²) → konversi ke mGal (× 1e5)
    tc_si = hm.prism_gravity(
        coordinates=(easting, northing, elevasi_m),
        prisms=prisms,
        density=densities,
        field="g_z",
    )
    tc_mGal = tc_si * 1e5

    print(f"  → Selesai. TC rata-rata = {tc_mGal.mean():.4f} mGal")
    return tc_mGal


# ================================================================================
# 15. PIPELINE LENGKAP
# ================================================================================

def pipeline_lengkap(df_raw: pd.DataFrame,
                     counter_reading: list,
                     value_in_mGal: list,
                     factor_for_interval: list,
                     g_absolut_base: float,
                     tanggal: str,
                     latitude_base: float,
                     longitude_base: float,
                     rho: float = 2.67,
                     gunakan_pasut_model: bool = True,
                     path_dem: str = None,
                     col_easting: str = "X",
                     col_northing: str = "Y",
                     densitas_tc: float = 2670.0,
                     padding_tc: float = 20000.0,
                     coarsen_tc: int = 10):
    import datetime as _dt
    df = df_raw.copy()

    # Konversi kolom waktu ke hari desimal
    # Tangani format datetime.time (dari pandas read_excel) atau string HH:MM:SS
    def _to_day_decimal(val):
        if pd.isna(val):
            return np.nan
        if isinstance(val, _dt.time):
            return (val.hour * 3600 + val.minute * 60 + val.second) / 86400.0
        if isinstance(val, (_dt.datetime, pd.Timestamp)):
            return (val.hour * 3600 + val.minute * 60 + val.second) / 86400.0
        try:
            # Coba parse string HH:MM:SS
            t = _dt.datetime.strptime(str(val).strip(), "%H:%M:%S").time()
            return (t.hour * 3600 + t.minute * 60 + t.second) / 86400.0
        except Exception:
            pass
        try:
            return float(val)  # sudah desimal
        except Exception:
            return np.nan

    df["Jam (GMT+7)"] = df["Jam (GMT+7)"].apply(_to_day_decimal)

    # Isi nilai kosong (3 baris per titik) — SEBELUM konversi numerik
    # Urutan penting: ffill dulu agar Elev (m) & TA (cm) terisi di 3 baris
    for col in ["Nama Titik", "TA (cm)", "Elev (m)"]:
        if col in df.columns:
            df[col] = df[col].replace("", np.nan).ffill()

    # Pastikan numerik
    df["Skala Bacaan"] = pd.to_numeric(df["Skala Bacaan"], errors="coerce")
    df["TA (cm)"]      = pd.to_numeric(df["TA (cm)"],      errors="coerce")
    df["Elev (m)"]     = pd.to_numeric(df["Elev (m)"],     errors="coerce")

    # Step 1: Konversi skala bacaan
    df["konversi_skala"] = konversi_skala_bacaan(
        df["Skala Bacaan"].values,
        np.asarray(counter_reading),
        np.asarray(value_in_mGal),
        np.asarray(factor_for_interval)
    )

    # Step 2: Koreksi pasut
    if gunakan_pasut_model:
        df["pasut_mGal"] = koreksi_pasut(
            df["Jam (GMT+7)"].values, latitude_base, longitude_base, tanggal
        )
    else:
        df["pasut_mGal"] = 0.0

    df["G_terkoreksi_pasut"] = df["konversi_skala"] - df["pasut_mGal"]

    #  Step 3: Koreksi tinggi alat 
    df["koreksi_TA"] = koreksi_tinggi_alat(df["TA (cm)"].values)
    df["G_terkoreksi_TA"] = df["G_terkoreksi_pasut"] + df["koreksi_TA"]

    #  Step 4: Rata-rata 3 bacaan 
    df_avg = rata_rata_bacaan(df, kolom_g_terkoreksi="G_terkoreksi_TA")

    #  Step 5: Konversi waktu ke detik
    t0 = df_avg["Jam (GMT+7)"].iloc[0]
    df_avg["waktu_detik"] = (df_avg["Jam (GMT+7)"] - t0) * 86400.0

    # Step 6: Koreksi drift
    drift_df = koreksi_drift(df_avg["waktu_detik"], df_avg["G_terkoreksi_TA"])
    df_avg = pd.concat([df_avg.reset_index(drop=True), drift_df], axis=1)

    # Step 7: G Obs
    gobs_df = hitung_g_obs(df_avg["G_terkoreksi_drift"], g_absolut_base)
    df_avg  = pd.concat([df_avg, gobs_df], axis=1)

    # Step 8: Koreksi lintang 
    if "Latitude" in df_avg.columns:
        lat = pd.to_numeric(df_avg["Latitude"], errors="coerce").fillna(latitude_base)
    else:
        lat = np.full(len(df_avg), latitude_base)

    df_avg["G_lintang"] = koreksi_lintang(lat)

    # Step 9: FAC 
    df_avg["FAC"] = koreksi_udara_bebas(df_avg["Elev (m)"].values)

    # Step 10: FAA
    df_avg["FAA"] = hitung_faa(
        df_avg["G_obs"].values,
        df_avg["G_lintang"].values,
        df_avg["FAC"].values
    )

    # Step 11: Koreksi Bouguer & ABS
    df_avg["koreksi_bouguer"] = koreksi_bouguer(df_avg["Elev (m)"].values, rho)
    df_avg["ABS"] = hitung_abs(df_avg["FAA"].values, df_avg["koreksi_bouguer"].values)

    # Step 12: Parasnis 
    hasil_parasnis = metode_parasnis(df_avg["FAA"].values, df_avg["Elev (m)"].values)
    rho_parasnis   = hasil_parasnis["rho_estimasi"]
    df_avg["BC_parasnis"]  = koreksi_bouguer(df_avg["Elev (m)"].values, rho_parasnis)
    df_avg["ABS_parasnis"] = hitung_abs(df_avg["FAA"].values, df_avg["BC_parasnis"].values)

    # Step 13: Koreksi Medan (TC) & ABL
    # Prioritas: (1) TC otomatis via harmonica (DEM), (2) TC dari kolom df, (3) NaN

    if path_dem is not None:
        # --- TC otomatis ---
        print("\n  [TC OTOMATIS – harmonica]")
        if col_easting not in df_avg.columns or col_northing not in df_avg.columns:
            raise ValueError(
                f"Kolom koordinat '{col_easting}' dan/atau '{col_northing}' "
                f"tidak ditemukan di DataFrame. Tambahkan koordinat UTM pada data input."
            )
        tc_auto = koreksi_medan_harmonica(
            easting   = pd.to_numeric(df_avg[col_easting],  errors="coerce").values,
            northing  = pd.to_numeric(df_avg[col_northing], errors="coerce").values,
            elevasi_m = df_avg["Elev (m)"].values,
            path_dem  = path_dem,
            densitas  = densitas_tc,
            padding_m = padding_tc,
            coarsen_factor = coarsen_tc,
        )
        df_avg["terrain_correction_mGal"] = tc_auto
        df_avg["ABL"] = hitung_abl(df_avg["ABS"].values, tc_auto)

    elif "terrain_correction_mGal" in df_avg.columns:
        # --- TC dari kolom file ---
        df_avg["terrain_correction_mGal"] = pd.to_numeric(
            df_avg["terrain_correction_mGal"], errors="coerce"
        ).fillna(0)
        df_avg["ABL"] = hitung_abl(df_avg["ABS"].values,
                                   df_avg["terrain_correction_mGal"].values)
    else:
        # --- Tidak ada TC ---
        df_avg["terrain_correction_mGal"] = np.nan
        df_avg["ABL"] = np.nan

    return df_avg, hasil_parasnis

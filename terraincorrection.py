import pandas as pd
import rioxarray
import harmonica as hm
import verde as vd
import numpy as np


df = pd.read_excel("data_koordinat.xlsx")

dem = (
    rioxarray.open_rasterio("dem.tif")
    .squeeze()
    .rename({"x": "easting", "y": "northing"})
)


region = vd.get_region((df["X"], df["Y"]))
region = vd.pad_region(region, pad=20000)

dem_crop = dem.sel(
    easting=slice(region[0], region[1]),
    northing=slice(region[3], region[2]),
)

dem_final = dem_crop.coarsen(
    easting=10,
    northing=10,
    boundary="trim"
).mean()


dx = float(abs(dem_final.easting[1] - dem_final.easting[0]))
dy = float(abs(dem_final.northing[1] - dem_final.northing[0]))

E, N = np.meshgrid(dem_final.easting, dem_final.northing)

west = (E - dx / 2).ravel()
east = (E + dx / 2).ravel()
south = (N - dy / 2).ravel()
north = (N + dy / 2).ravel()

bottom = np.zeros_like(west)
top = dem_final.values.ravel()

prisms = np.vstack([
    west,
    east,
    south,
    north,
    bottom,
    top
]).T


print(f"Menghitung tarikan dari {prisms.shape[0]} prisma...")

densities = np.full(prisms.shape[0], 2670.0)

tc_values = hm.prism_gravity(
    coordinates=(df["X"], df["Y"], df["Z"]),
    prisms=prisms,
    density=densities,
    field="g_z"
)


df["terrain_correction_mGal"] = tc_values

print("\n" + "=" * 50)
print(df[["X", "Y", "Z", "terrain_correction_mGal"]].to_string(index=False))
print("=" * 50)
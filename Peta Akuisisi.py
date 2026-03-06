import folium
import pandas as pd
from pyproj import Transformer
import webbrowser

file_path = r"C:/Users/LOQ/OneDrive/Documents/Data SP.csv"  
data = pd.read_csv(file_path)

data = data.loc[:, ~data.columns.duplicated()]
kolom = ['X', 'Y', 'Z', 'Koreksi']
data = data[kolom].apply(pd.to_numeric, errors='coerce').dropna()

print(f"Jumlah data valid: {len(data)} titik")

transformer = Transformer.from_crs("EPSG:32749", "EPSG:4326", always_xy=True)
data['lon'], data['lat'] = transformer.transform(data['X'].values, data['Y'].values)

center_lat = data['lat'].mean()
center_lon = data['lon'].mean()

map_indonesia = folium.Map(location=[center_lat, center_lon], zoom_start=16)

judul_html = '''
<div style="position: fixed;
            top: 10px; left: 50px; width: 350px; height: 50px;
            background-color: white; z-index: 9999; padding: 10px;
            box-shadow: 0px 0px 5px rgba(0,0,0,0.5);">
    <h3 style="margin: 0;">Peta Titik Akuisisi Self Potential (SP)</h3>
</div>
'''
map_indonesia.get_root().html.add_child(folium.Element(judul_html))

for i, row in data.iterrows():
    popup_html = f"""
    <b>Titik {i+1}</b><br>
    X: {row['X']:.2f} m<br>
    Y: {row['Y']:.2f} m<br>
    Z (Elevasi): {row['Z']:.2f} m<br>
    Koreksi SP: {row['Koreksi']:.2f} mV
    """
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=5,
        color='black',
        fill=True,
        fill_color='red',
        fill_opacity=0.8,
        popup=popup_html,
        tooltip=f"Titik {i+1}"
    ).add_to(map_indonesia)

map_indonesia.save("peta_well.html")
webbrowser.open("peta_well.html")

print("✅ Peta berhasil dibuat dan dibuka di browser (peta_well.html)")

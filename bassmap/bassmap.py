"""Main module."""


import csv
import folium
import branca
import random
import leafmap
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

locations = {}

def get_location_name():
    """Input name and either generate random point or input coordinates to shapefile and display on map"""
    while True:
        name = input("Enter location name (or 'q' to finish): ")
        
        if name == 'q':
            break

        generate_random = input("Generate random point? (y/n): ")
        if generate_random.lower() == "y":

            lat = random.uniform(-90, 90)
            lon = random.uniform(-180, 180)
            locations[name] = {'lat': lat, 'lon': lon}
            print(f"The location {name} is located at ({lat}, {lon}).\n")
        else:
            lat = input("Enter latitude: ")
            lon = input("Enter longitude: ")

            try:
                lat = float(lat)
                lon = float(lon)

                if lat < -90 or lat > 90:
                    raise ValueError("Latitude must be between -90 and 90 degrees")
                if lon < -180 or lon > 180:
                    raise ValueError("Longitude must be between -180 and 180 degrees")

                locations[name] = {'lat': lat, 'lon': lon}

                print(f"The location {name} is located at ({lat}, {lon}).\n")

            except ValueError as e:
                print(f"Invalid input: {e}")

    with open('locations.csv', mode='w', newline='') as csv_file:
        fieldnames = ['name', 'lat', 'lon']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        writer.writeheader()
        for name, coords in locations.items():
            writer.writerow({'name': name, 'lat': coords['lat'], 'lon': coords['lon']})
    df = pd.read_csv('locations.csv')

    geometry = [Point(xy) for xy in zip(df['lon'], df['lat'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry)
    gdf.to_file('locations.shp', driver='ESRI Shapefile')

    colors = {}
    for i, name in enumerate(gdf['name']):
        colors[name] = f"#{i+1:02x}0000"

    style = {'fillOpacity': 0.7, 'weight': 1, 'color': 'black'}
    m = leafmap.Map(center=[0, 0], zoom=2)
    in_shp = 'locations.shp'
    m.add_shp(in_shp, layer_name="points", style=style)
    m.add_legend(legend_title="Locations", legend_dict=colors)
    
    from IPython.display import display
    display(m)
"""Main module."""

import requests
import zipfile
import io
import json
import geopandas as gpd
import ipyleaflet
import random

from ipyleaflet import Map
from ipyleaflet import TileLayer, basemaps, GeoJSON, LayersControl, ImageOverlay
import rasterio
import rasterio.plot
from rasterio.plot import show
import numpy as np
import matplotlib.pyplot as plt
import base64
import folium
import xyzservices.providers as xyz
from ipyleaflet import display
import ipywidgets as widgets
from ipyleaflet import WidgetControl

class Mapomatic(Map):
    
    def __init__(self, center=[20,0], **kwargs) -> None:
        if "scroll_wheel_zoom" not in kwargs:
            kwargs["scroll_wheel_zoom"] = True
        
        super().__init__(center = center, **kwargs)
    
    def add_marker(self, marker):
        self.markers.append(marker)
        self.add_layer(marker)

    def add_image(self, url, position, size, opacity=1.0, layer_name=None):
        image = ImageOverlay(
            url=url,
            bounds=[position, (position[0] + size[0], position[1] + size[1])],
            opacity=opacity,
            name=layer_name
        )
        self.add_layer(image)
    
    def add_raster(self, url, name='Raster', fit_bounds=True, **kwargs):
        """Adds a raster layer to the map.
        Args:
            url (str): The URL of the raster layer.
            name (str, optional): The name of the raster layer. Defaults to 'Raster'.
            fit_bounds (bool, optional): Whether to fit the map bounds to the raster layer. Defaults to True.
        """
        import httpx

        titiler_endpoint = "https://titiler.xyz"

        r = httpx.get(
            f"{titiler_endpoint}/cog/info",
            params = {
                "url": url,
            }
        ).json()

        bounds = r["bounds"]

        r = httpx.get(
            f"{titiler_endpoint}/cog/tilejson.json",
            params = {
                "url": url,
            }
        ).json()

        tile = r["tiles"][0]

        self.add_tile_layer(url=tile, name=name, **kwargs)

        if fit_bounds:
            bbox = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]
            self.fit_bounds(bbox)
    def add_tile_layer(self, url, name, attribution = "", **kwargs):
        """Adds a tile layer to the map.
        
        Args:
            url (str): The URL of the tile layer.
            name (str): The name of the tile layer
            attribution (str, optional): The attribution of the tile layer. Defaults to **
            """
        tile_layer = ipyleaflet.TileLayer(
            url = url,
            name = name,
            attribution = attribution,
            **kwargs
        )
        self.add_layer(tile_layer)
    
    def add_layers_control(self, position="topright", **kwargs):
        """Adds a layers control to the map.
        
        Args:
            kwargs: Keyword arguments to pass to the layers control
        """
        layers_control = ipyleaflet.LayersControl(position = position, **kwargs)
        self.add_control(layers_control)

    def add_fullscreen_control(self, position="topleft"):
        """Adds a fullscreen control to the map.
        
        Args:
            kwargs: Keyward arguments to pass to the layers control.
        """
        fullscreen_control = ipyleaflet.FullScreenControl(position=position)
        self.add_control(fullscreen_control)
    
    def add_basemap(self, basemap_name, url_template):
        """
        Adds a basemap to the map using a URL template.
        
        Parameters:
        basemap_name (str): The name of the basemap to add.
        url_template (str): The URL template to use for the new basemap layer. Must be 
            a valid XYZ tile service.
        """
        # Remove the default OpenStreetMap basemap layer, if present
        if len(self.layers) > 1:
            self.remove_layer(self.layers[0])
        
        # Add the new basemap layer
        new_layer = TileLayer(url=url_template, attribution=basemap_name)
        self.add_layer(new_layer)
    
    def add_shp(self, shp_path):
        """
        Adds a shapefile to the map. 
        
        Parameters:
        shp_path (str): The file path or HTTP URL to the shapefile in a zip file.
        """
        # If the path is an HTTP URL, download and unzip the shapefile
        if shp_path.startswith('http'):
            response = requests.get(shp_path)
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                zip_ref.extractall()
            shp_path = shp_path.split('/')[-1].split('.')[0] + '.shp'
        
        # Read the shapefile using GeoPandas
        gdf = gpd.read_file(shp_path)
        
        # Convert the GeoDataFrame to a GeoJSON object
        geojson = GeoJSON(data=gdf.__geo_interface__)
        
        # Add the GeoJSON layer to the map
        self.add_layer(geojson)
        
        # Add a layer control to the map
        control = LayersControl(position='topright')
        self.add_control(control)
    
    def add_geojson(self, geojson_path):
        """
        Adds a GeoJSON file to the map. 
        
        Parameters:
        geojson_path (str or dict): The file path or dictionary object containing GeoJSON data.
        """
        # If the path is an HTTP URL, download the GeoJSON file
        if isinstance(geojson_path, str) and geojson_path.startswith('http'):
            response = requests.get(geojson_path)
            geojson_data = response.json()
        # Otherwise, assume it's a file path or a dictionary object
        else:
            with open(geojson_path) as f:
                geojson_data = json.load(f)
        
        # Create a GeoJSON layer and add it to the map
        geojson = GeoJSON(data=geojson_data)
        self.add_layer(geojson)
        
        # Add a layer control to the map
        control = LayersControl(position='topright')
        self.add_control(control)

    def add_vector(self, vector_data):
        """
        Adds a vector data to the map. The vector data can be in any GeoPandas-supported
        format, such as GeoJSON, shapefile, GeoDataFrame, etc.
        
        Parameters:
        vector_data (str or dict or GeoDataFrame): The vector data to add to the map. 
            Can be a file path or URL to the vector data, a dictionary object containing 
            GeoJSON data, or a GeoDataFrame.
        """
        # If the vector data is a file path or URL, read it using GeoPandas
        if isinstance(vector_data, str):
            try:
                gdf = gpd.read_file(vector_data)
            except ValueError:
                gdf = gpd.read_file(vector_data, encoding='utf-8')
        # If the vector data is a dictionary object, create a GeoDataFrame
        elif isinstance(vector_data, dict):
            gdf = gpd.GeoDataFrame.from_features(vector_data['features'])
        # If the vector data is already a GeoDataFrame, use it directly
        elif isinstance(vector_data, gpd.GeoDataFrame):
            gdf = vector_data
        else:
            raise ValueError('Invalid vector data format. Must be a file path or URL, a dictionary object containing GeoJSON data, or a GeoDataFrame.')
        
        # Convert the GeoDataFrame to a GeoJSON object
        geojson = GeoJSON(data=gdf.__geo_interface__)
        
        # Add the GeoJSON layer to the map
        self.add_layer(geojson)
        
        # Add a layer control to the map
        control = LayersControl(position='topright')
        self.add_control(control)

    def select_basemap(self, **kwargs):
        """
        Adds a basemap selector to the map instance.

        Parameters:
            self: bassmap Mapomatic: map instance called by user
        
        Returns:
            bassmap Mapomatic: displays drop down menu when called to the Mapomatic class
        """

        output_widget = widgets.Output(layout = {'border': '1px solid green'})
        output_widget.clear_output()
        basemap_ctrl = WidgetControl(widget = output_widget, position='topright')
        self.add_control(basemap_ctrl)

        dropdown = widgets.Dropdown(
            options = ["OpenStreetMap", "ESRI Imagery", "OpenTopoMap", "NatGeo World Map", "Light Canvas"], 
            value = None,
            description = 'basemap',
            )

        close_button = widgets.ToggleButton(
            value = True,
            tooltip = "Toggle basemap selector",
            icon = "fa-times",
            button_style = "primary",
        )
        close_button

        widget_menu = widgets.VBox([close_button, dropdown])


        with output_widget:
            display(widget_menu)

        def change_basemap(select):
            if select["new"] == "OpenStreetMap":
                self.add_basemap(basemap= "OpenStreetMap")
            
            if select["new"] == "ESRI Imagery":
                self.add_basemap(basemap= "Esri.WorldImagery")
            
            if select["new"] == "OpenTopoMap":
                self.add_basemap(basemap= "OpenTopoMap")

            if select["new"] == "NatGeo World Map":
                self.add_basemap(basemap= "Esri.NatGeoWorldMap")

            if select["new"] == "Light Canvas":
                self.add_basemap(basemap= "CartoDB.Positron")
        
        dropdown.observe(change_basemap, "value")

        def close_basemap(select):
    
            if select["new"] == True:
                output_widget.clear_output()
                with output_widget:
                    display(widget_menu)

            else:
                output_widget.clear_output()
                with output_widget:
                    display(close_button)
        
        close_button.observe(close_basemap, "value")

locations = {}

def generate_input_points():
    """Input name and either generate random point or input coordinates to shapefile and display on map.

    Args:
        name (): Name of the location.
        lat (int, optional): The latitude value
        lon (int, optional): The longitude value
        generate_random (int, optional): Whether to generate random coordinates or use custom
    Raises:
        ValueError: Latitude must be between -90 and 90 degrees
        ValueError: Longitude must be between -180 and 180 degrees
    """

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
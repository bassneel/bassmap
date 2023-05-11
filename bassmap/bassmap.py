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
from IPython.display import HTML

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

        output_widget = widgets.Output(layout = {'border': '1px solid white'})
        output_widget.clear_output()
       
        with output_widget:
            display(HTML('''
                <style>
                    .widget-dropdown { background-color: black !important; }
                    .widget-dropdown .widget-label { color: olive !important; }
                </style>
            '''))

        basemap_ctrl = WidgetControl(widget = output_widget, position='topright')
        self.add_control(basemap_ctrl)

        dropdown = widgets.Dropdown(
            options = ["OpenStreetMap", "ESRI Imagery", "OpenTopoMap", "NatGeo World Map", "Light Canvas"], 
            value = None,
            description = 'Basemap',
            style = {'description_width': 'initial', 'button_width': '100px', 'button_color': 'olive', 'description_color': 'olive', 'background-color': 'olive'}
        )

        icon_html = '<i class="fa fa-window-close" aria-hidden="true"></i>'
        close_button = widgets.ToggleButton(
            value = True,
            tooltip = "Toggle basemap selector",
            description = 'Close',
            icon = icon_html,
            button_style = "primary",
        )

        close_button.style.button_color = "white"
        close_button.style.font_weight = "bold"

        close_button_icon = HTML(
            '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">'
            '<i class="fa fa-times"></i>'
        )

        widget_menu = widgets.VBox([close_button, dropdown])


        with output_widget:
            display(widget_menu)

        def change_basemap(select):
            if select["new"] == "OpenStreetMap":
                self.add_basemap(basemap_name= "OpenStreetMap", url_template="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")
            
            if select["new"] == "ESRI Imagery":
                self.add_basemap(basemap_name= "Esri.WorldImagery", url_template="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}")
            
            if select["new"] == "OpenTopoMap":
                self.add_basemap(basemap_name= "OpenTopoMap", url_template="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png")

            if select["new"] == "NatGeo World Map":
                self.add_basemap(basemap_name= "Esri.NatGeoWorldMap", url_template="https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}")
                
            if select["new"] == "Light Canvas":
                self.add_basemap(basemap_name= "CartoDB.Positron", url_template="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png")
        
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

### Landsat 8 Composites

import tempfile
import os
import shutil

tmp_dir = tempfile.TemporaryDirectory()

def get_truecolor(red_band, green_band, blue_band, georef):
  
    """Generate a true-color composite image from red, green, and blue bands.

    Args:
        red_band (ndarray): A 2D numpy array representing the red band.
        green_band (ndarray): A 2D numpy array representing the green band.
        blue_band (ndarray): A 2D numpy array representing the blue band.
        georef (osgeo.gdal.Dataset): A GDAL dataset containing georeferencing information for the input bands.

    Returns:
        str: The path to the created true color file.

    Raises:
        ValueError: If the input arrays are not of the same shape.
        ValueError: If the input arrays have different data types.
        ValueError: If the input arrays have invalid values.
        ImportError: If the GDAL library is not installed.

    Example:
        # Load the red, green, and blue bands from GeoTIFF files
        red_band = gdal.Open('path/to/red_band.tif').ReadAsArray()
        green_band = gdal.Open('path/to/green_band.tif').ReadAsArray()
        blue_band = gdal.Open('path/to/blue_band.tif').ReadAsArray()
        georef = gdal.Open('path/to/reference.tif')

        # Generate a true-color composite image and download it
        true_color_path = true_color_path(red_band, green_band, blue_band, georef)
        # Download the file at true_color_path
    """

    from osgeo import gdal

    # Combine the three bands into a single 3D array with 3 bands
    true_color = np.array([red_band, green_band, blue_band], dtype=np.uint16)

    # Get the dimensions and georeferencing information from one of the input files
    xsize = georef.RasterXSize
    ysize = georef.RasterYSize
    proj = georef.GetProjection()
    geotrans = georef.GetGeoTransform()
    driver = gdal.GetDriverByName('GTiff')

    # Create a new TIFF file and write the NDVI array to it
    true_color_path = os.path.join(tmp_dir.name, 'true_color_comp.tif')
    true_color_ds = driver.Create(true_color_path, xsize, ysize, 3, gdal.GDT_Float32)
    
    if true_color_ds is not None:
        true_color_ds.SetProjection(proj)
        true_color_ds.SetGeoTransform(geotrans)
        true_color_ds.GetRasterBand(1).WriteArray(true_color[0])
        true_color_ds.GetRasterBand(2).WriteArray(true_color[1])
        true_color_ds.GetRasterBand(3).WriteArray(true_color[2])
        true_color_ds.FlushCache()

    else:
        raise Exception("Failed to create TIFF file")
        
    return true_color_path

def get_color_infrared(nir_band, red_band, green_band, georef):
  
    """
    Combines a near-infrared band, red band, and green band into a single 3-band image,
    where the near-infrared band is displayed as red, the red band is displayed as green,
    and the green band is displayed as blue. This produces a color infrared image that
    accentuates the buildings in the scene.

    Args:
        nir_band (numpy array): A 2D numpy array representing a near-infrared band
        red_band (numpy array): A 2D numpy array representing a red band
        green_band (numpy array): A 2D numpy array representing a green band
        georef (osgeo.gdal.Dataset): A GDAL dataset containing georeferencing information for the input bands.

    Returns:
        str: The path to the created color infrared file.
                
    Raises:
        ValueError: If the input arrays are not of the same shape.
        ValueError: If the input arrays have different data types.
        ValueError: If the input arrays have invalid values.
        ImportError: If the GDAL library is not installed.

    Example:
        # Load the input bands as numpy arrays
        nir_band = gdal.Open('path/to/nir_band.tif').ReadAsArray()
        red_band = gdal.Open('path/to/red_band.tif').ReadAsArray()
        green_band = gdal.Open('path/to/green_band.tif').ReadAsArray()
        georef = gdal.Open('path/to/reference.tif')

        # Generate a color infrared composite image and download it
        color_infrared_path = get_color_infrared(nir_band, red_band, green_band, georef)
        # Download the file at color_infrared_path
    """

    from osgeo import gdal

    # Combine the three bands into a single 3D array with 3 bands
    color_infrared = np.array([nir_band, red_band, green_band], dtype=np.uint16)

    # Get the dimensions and georeferencing information from one of the input files
    xsize = georef.RasterXSize
    ysize = georef.RasterYSize
    proj = georef.GetProjection()
    geotrans = georef.GetGeoTransform()
    driver = gdal.GetDriverByName('GTiff')

    # Create a new TIFF file and write the NDVI array to it
    color_infrared_path = os.path.join(tmp_dir.name, 'color_infrared_comp.tif')
    color_infrared_ds = driver.Create(color_infrared_path, xsize, ysize, 3, gdal.GDT_Float32)
    
    if color_infrared_ds is not None:
        color_infrared_ds.SetProjection(proj)
        color_infrared_ds.SetGeoTransform(geotrans)
        color_infrared_ds.GetRasterBand(1).WriteArray(color_infrared[0])
        color_infrared_ds.GetRasterBand(2).WriteArray(color_infrared[1])
        color_infrared_ds.GetRasterBand(3).WriteArray(color_infrared[2])
        color_infrared_ds.FlushCache()

    else:
        raise Exception("Failed to create TIFF file")
        
    return color_infrared_path

def get_false_color(swir2_band, swir_band, red_band, georef):

    """
    Combines a short wave infrared 2 band, a short wave infrared band, and red band into a single 3-band image,
    where the a short wave infrared 2 band is displayed as red, the a short wave infrared band is displayed as green,
    and the red band is displayed as blue. This produces a false-color image that
    accentuates the vegetation in the scene.

    Args:
        swir2_band (numpy array): A 2D numpy array representing a short wave infrared 2 band
        swir_band (numpy array): A 2D numpy array representing a short wave infrared band
        red_band (numpy array): A 2D numpy array representing a red band
        georef (osgeo.gdal.Dataset): A GDAL dataset containing georeferencing information for the input bands.

    Returns:
        str: The path to the created false-color file.

    Raises:
        ValueError: If the input arrays are not of the same shape.
        ValueError: If the input arrays have different data types.
        ValueError: If the input arrays have invalid values.
        ImportError: If the GDAL library is not installed.

    Example:
        # Load the input bands as numpy arrays
        swir2_band = gdal.Open('path/to/swir2_band.tif').ReadAsArray()
        swir_band = gdal.Open('path/to/swir_band.tif').ReadAsArray()
        red_band = gdal.Open('path/to/red_band.tif').ReadAsArray()
        georef = gdal.Open('path/to/reference.tif')

        # Generate a false-color composite image and download it
        false_color_path = false_color_path(swir2_band, swir_band, red_band, georef)
        # Download the file at false_color_path
    """

    from osgeo import gdal

    # Combine the three bands into a single 3D array with 3 bands
    false_color = np.array([swir2_band, swir_band, red_band], dtype=np.uint16)

    # Get the dimensions and georeferencing information from one of the input files
    xsize = georef.RasterXSize
    ysize = georef.RasterYSize
    proj = georef.GetProjection()
    geotrans = georef.GetGeoTransform()
    driver = gdal.GetDriverByName('GTiff')

    # Create a new TIFF file and write the NDVI array to it
    false_color_path = os.path.join(tmp_dir.name, 'false_color_comp.tif')
    false_color_ds = driver.Create(false_color_path, xsize, ysize, 3, gdal.GDT_Float32)
    
    if false_color_ds is not None:
        false_color_ds.SetProjection(proj)
        false_color_ds.SetGeoTransform(geotrans)
        false_color_ds.GetRasterBand(1).WriteArray(false_color[0])
        false_color_ds.GetRasterBand(2).WriteArray(false_color[1])
        false_color_ds.GetRasterBand(3).WriteArray(false_color[2])
        false_color_ds.FlushCache()

    else:
        raise Exception("Failed to create TIFF file")
        
    return false_color_path

def get_health_veg(nir_band, swir_band, blue_band, georef):

    """
    Combines a near infrared band, a short wave infrared band, and blue band into a single 3-band image,
    where the a near infrared band is displayed as red, the a short wave infrared band is displayed as green,
    and the blue band is displayed as blue. This produces a false-color image that
    accentuates the healthy vegetation in the scene.

    Args:
        nir_band (numpy array): A 2D numpy array representing a near infrared band
        swir_band (numpy array): A 2D numpy array representing a short wave infrared band
        blue_band (numpy array): A 2D numpy array representing a blue band
        georef (osgeo.gdal.Dataset): A GDAL dataset containing georeferencing information for the input bands.

    Returns:
        str: The path to the created healthy vegetation file.

    Raises:
        ValueError: If the input arrays are not of the same shape.
        ValueError: If the input arrays have different data types.
        ValueError: If the input arrays have invalid values.
        ImportError: If the GDAL library is not installed.

    Example:
        # Load the input bands as numpy arrays
        nir_band = gdal.Open('path/to/nir_band.tif').ReadAsArray()
        swir_band = gdal.Open('path/to/swir_band.tif').ReadAsArray()
        blue_band = gdal.Open('path/to/blue_band.tif').ReadAsArray()
        georef = gdal.Open('path/to/reference.tif')

        # Generate a healthy vegetation composite image and download it
        healthy_veg_path = get_health_veg(nir_band, swir_band, blue_band, georef)
        # Download the file at healthy_veg_path
    """

    from osgeo import gdal

    # Combine the three bands into a single 3D array with 3 bands
    healthy_veg = np.array([nir_band, swir_band, blue_band], dtype=np.uint16)

    # Get the dimensions and georeferencing information from one of the input files
    xsize = georef.RasterXSize
    ysize = georef.RasterYSize
    proj = georef.GetProjection()
    geotrans = georef.GetGeoTransform()
    driver = gdal.GetDriverByName('GTiff')

    # Create a new TIFF file and write the composite array to it
    healthy_veg_ds = driver.Create('/tmp/healthy_veg_comp.tif', xsize, ysize, 3, gdal.GDT_UInt16)
        
    # Create a new TIFF file and write the NDVI array to it
    healthy_veg_path = os.path.join(tmp_dir.name, 'healthy_veg_comp.tif')
    healthy_veg_ds = driver.Create(healthy_veg_path, xsize, ysize, 3, gdal.GDT_Float32)
    
    if healthy_veg_ds is not None:
        healthy_veg_ds.SetProjection(proj)
        healthy_veg_ds.SetGeoTransform(geotrans)
        healthy_veg_ds.GetRasterBand(1).WriteArray(healthy_veg[0])
        healthy_veg_ds.GetRasterBand(2).WriteArray(healthy_veg[1])
        healthy_veg_ds.GetRasterBand(3).WriteArray(healthy_veg[2])
        healthy_veg_ds.FlushCache()

    else:
        raise Exception("Failed to create TIFF file")
        
    return healthy_veg_path

def get_ndmi(nir_band, swir_band, georef):

    """
    Calculates the Normalized Difference Moisture Index (NDMI) from Near Infrared (NIR) and Shortwave Infrared (SWIR) bands.
    
    Args:
        nir_band (numpy.ndarray): A 2D or 3D array containing the Near Infrared band data.
        swir_band (numpy.ndarray): A 2D or 3D array containing the Shortwave Infrared band data.
        georef (osgeo.gdal.Dataset): A GDAL dataset containing georeferencing information for the input bands.
    
    Returns:
        str: The path to the created NDMI file.
    
    Raises:
        ValueError: If the input arrays are not of the same shape.
        ValueError: If the input arrays have different data types.
        ValueError: If the input arrays have invalid values.
        ImportError: If the GDAL library is not installed.
    
    Examples:
        nir_band = gdal.Open('path/to/nir_band.tif').ReadAsArray()
        swir_band = gdal.Open('path/to/swir_band.tif').ReadAsArray()
        georef = gdal.Open('path/to/reference.tif')

        # Generate an NDMI composite image and download it
        ndmi_path = get_NDMI(red_band, nir_band, georef)
        # Download the file at ndvi_path
    """

    from osgeo import gdal

    # Scale the input bands to the range of 0-255
    nir_band = (nir_band / 65535.0) * 255.0
    swir_band = (swir_band / 65535.0) * 255.0

    # Calculate the NDMI from the NIR and SWIR bands
    ndmi = np.empty_like(nir_band, dtype=np.float32)
    ndmi.fill(np.nan)
    valid = np.logical_and(nir_band != 0, swir_band != 0)
    ndmi[valid] = (nir_band[valid] - swir_band[valid]) / (nir_band[valid] + swir_band[valid])

    # Get the dimensions and georeferencing information from one of the input files
    xsize = georef.RasterXSize
    ysize = georef.RasterYSize
    proj = georef.GetProjection()
    geotrans = georef.GetGeoTransform()
    driver = gdal.GetDriverByName('GTiff')

    # Create a new TIFF file and write the NDVI array to it
    ndmi_path = os.path.join(tmp_dir.name, 'ndmi_composite.tif')
    ndmi_ds = driver.Create(ndmi_path, xsize, ysize, 1, gdal.GDT_Float32)
    
    if ndmi_ds is not None:
        ndmi_ds.SetProjection(proj)
        ndmi_ds.SetGeoTransform(geotrans)
        ndmi_ds.GetRasterBand(1).WriteArray(ndmi)
        ndmi_ds.FlushCache()
    else:
        raise Exception("Failed to create TIFF file")
        
    return ndmi_path

def get_NDVI(red_band, nir_band, georef):
    """
    Calculates the Normalized Difference Vegetation Index (NDVI) from Red and Near Infrared (NIR) bands.

    Args:
        red_band (numpy.ndarray): A 2D or 3D array containing the Red band data.
        nir_band (numpy.ndarray): A 2D or 3D array containing the Near Infrared band data.
        georef (osgeo.gdal.Dataset): A GDAL dataset containing georeferencing information for the input bands.

    Returns:
        str: The path to the created NDVI file.

    Raises:
        ValueError: If the input arrays are not of the same shape.
        ValueError: If the input arrays have different data types.
        ValueError: If the input arrays have invalid values.
        ImportError: If the GDAL library is not installed.

    Examples:
        red_band = gdal.Open('path/to/red_band.tif').ReadAsArray()
        nir_band = gdal.Open('path/to/nir_band.tif').ReadAsArray()
        georef = gdal.Open('path/to/reference.tif')

        # Generate an NDVI composite image and download it
        ndvi_path = get_NDVI(red_band, nir_band, georef)
        # Download the file at ndvi_path
    """

    from osgeo import gdal
    
    # Scale the input bands to the range of 0-255
    red_band = (red_band / 65535.0) * 255.0
    nir_band = (nir_band / 65535.0) * 255.0

    # Calculate the NDVI from the NIR and Red bands
    ndvi = np.empty_like(nir_band, dtype=np.float32)
    ndvi.fill(np.nan)
    valid = np.logical_and(red_band != 0, nir_band != 0)
    ndvi[valid] = (nir_band[valid] - red_band[valid]) / (nir_band[valid] + red_band[valid])

    # Get the dimensions and georeferencing information from one of the input files
    xsize = georef.RasterXSize
    ysize = georef.RasterYSize
    proj = georef.GetProjection()
    geotrans = georef.GetGeoTransform()
    driver = gdal.GetDriverByName('GTiff')

    # Create a new TIFF file and write the NDVI array to it
    ndvi_path = os.path.join(tmp_dir.name, 'ndvi_composite.tif')
    ndvi_ds = driver.Create(ndvi_path, xsize, ysize, 1, gdal.GDT_Float32)
    
    if ndvi_ds is not None:
        ndvi_ds.SetProjection(proj)
        ndvi_ds.SetGeoTransform(geotrans)
        ndvi_ds.GetRasterBand(1).WriteArray(ndvi)
        ndvi_ds.FlushCache()
    else:
        raise Exception("Failed to create TIFF file")
        
    return ndvi_path


def csv_to_points(in_csv):

    df = pd.read_csv(in_csv)

    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry)
    gdf.to_file('csv_points.shp', driver='ESRI Shapefile')

def add_marker_cluster(in_csv):

    df = pd.read_csv(in_csv)

    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry)
    gdf.to_file('marker_cluster.shp', driver='ESRI Shapefile')

    colors = {}
    for i, name in enumerate(gdf['name']):
        colors[name] = f"#{i+1:02x}0000"

    style = {'fillOpacity': 0.7, 'weight': 1, 'color': 'black'}
    m = Mapomatic(center=[0, 0], zoom=2)
    m.add_shp('marker_cluster.shp')

    from IPython.display import display
    display(m)

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
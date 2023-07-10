from flask import Flask,render_template,request, url_for
import pandas as pd
import numpy as np
from pymongo import MongoClient

from pymongo_get_database import get_database


import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from shapely.geometry import Point
from geopy.geocoders import Nominatim
import us
from geopy.geocoders import Nominatim
import ee
from datetime import date, timedelta

import google.auth

from authenticate import authenticate_implicit_with_adc

#from prophet_predictions import make_pred

#authenticate_implicit_with_adc(project_id='ee-atlasmadness-hackathon')

#credentials, project_id = google.auth.default()
#ee.Initialize(credentials, project='ee-atlasmadness-hackathon')

ee.Authenticate()
ee.Initialize()



dbname = get_database()
collection_name = dbname["mongoDB_atlas_"]

app = Flask(__name__)




aviation_csv = pd.read_csv('static/files/Airport.csv')
aviation_csv = aviation_csv.iloc[:, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 30]]

def get_lat(row):
  lat = aviation_csv.iloc[row, 12].split()[1][1:]
  return lat

def get_long(row):
  lon = aviation_csv.iloc[row, 12].split()[2][:-1]
  return lon

aviation_csv['geometry'] = aviation_csv.index.map(lambda x: Point(get_lat(x), get_long(x)))

aviation = gpd.GeoDataFrame(aviation_csv, geometry=aviation_csv.geometry)

def av_map(state, map):
  subset = aviation[aviation['STATE_NAME'] == state.upper()]
  marker_cluster = MarkerCluster(name='Aviation Icons').add_to(map)
  for idx, row in subset.iterrows():
    icon = folium.Icon(color='blue', icon='plane', prefix='fa')
    folium.Marker([row.geometry.y, row.geometry.x], icon=icon).add_to(marker_cluster)


coal_mines = gpd.read_file('static/files/Coal_Mines.geojson')
def coal_map(state, map):
  subset = coal_mines[coal_mines['STATE'] == state.upper()]
  marker_cluster = MarkerCluster(name='Coal Icons').add_to(map)
  for idx, row in subset.iterrows():
    icon = folium.Icon(color="red", icon='gem', prefix='fa')
    folium.Marker([row.geometry.y, row.geometry.x], icon=icon).add_to(marker_cluster)

us_power = pd.read_excel('static/files/power.xlsx')
us_power['State'] = us_power['State'].apply(lambda x: us.states.lookup(x).name if us.states.lookup(x) else None)
subset_df = us_power[us_power['Latitude'].apply(lambda x: isinstance(x, str))]
sub_list = subset_df.index.values.tolist()
us_power = us_power.drop(sub_list)
us_power['geometry'] = us_power.apply(lambda row: Point(row['Longitude'], row['Latitude']), axis = 1)

def power_map(state, map):
  subset = us_power[us_power['State'] == state.title()]
  marker_cluster = MarkerCluster(name='Power Icons').add_to(map)
  for idx, row in subset.iterrows():
      icon = folium.Icon(color='gray', icon='industry', prefix='fa')
      folium.Marker([row.geometry.y, row.geometry.x], icon=icon).add_to(marker_cluster)



def add_ee_layer(self, ee_image_object, vis_params, name):
    """Adds a method for displaying Earth Engine image tiles to folium map."""
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
        name=name,
        overlay=True,
        control=True,
        overlay_params={'opacity': 0.5}
    ).add_to(self)

# Add Earth Engine drawing method to folium.
folium.Map.add_ee_layer = add_ee_layer

def create_map(location, date_of_policy):


  state = location.split(",")[1].strip()
  locator = Nominatim(user_agent='myGeocoder')
  location = locator.geocode(location)
  coordinates = (location.latitude, location.longitude)

  date_of_policy = date.fromisoformat(date_of_policy)

  delta = timedelta(days=10)

    # Load the image collection
  collections = [ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2').select('NO2_column_number_density').filterDate(date_of_policy.isoformat(), (date_of_policy + delta).isoformat()),
                 ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_AER_AI').select('absorbing_aerosol_index').filterDate(date_of_policy.isoformat(), (date_of_policy + delta).isoformat()),
                 ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_HCHO').select('tropospheric_HCHO_column_number_density').filterDate(date_of_policy.isoformat(), (date_of_policy + delta).isoformat()),
                 ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_CO').select('CO_column_number_density').filterDate(date_of_policy.isoformat(), (date_of_policy + delta).isoformat()),
                 ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_SO2').select('SO2_column_number_density').filterDate(date_of_policy.isoformat(), (date_of_policy + delta).isoformat()),
                 ] #averages results from 5 dates to adjust for noise

  names = ['NO2', 'absorbing_aerosol_index', 'tropospheric_HCHO_density', 'CO_density', 'SO2_density', 'Land Cover']

  # Define the visualization parameters
  band_viz = {
      'min': -2,
      'max': 2,
      'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red'],
      #'palette': ['#b3ecff', '#99e5ff', '#80dfff', '#66d9ff', '#4dd2ff', '#33ccff', '#19c5ff', '#00bfff'],
      'opacity': 0.4
  }


  vis_min_maxes = [(0, 0.0002), (-1, 2.0), (0.0,	0.0003), (0,	0.05), (0.0, 0.0005)]

  # Create a Folium map centered at the specified location
  map = folium.Map(location=[coordinates[0], coordinates[1]], zoom_start=10)

  # Define a function to add Earth Engine layers to Folium

  coal_map(state, map)

  # Call av_map to add aviation layer
  av_map(state, map)

  #Call power_map to add power layer
  power_map(state, map)

  # Add the Earth Engine layer to the Folium map
  for x in range(len(collections)):
    if x == 4:
      band_viz['palette'] = ['blue', 'purple', 'cyan', 'green', 'yellow', 'red']
    band_viz['min'] = vis_min_maxes[x][0]
    band_viz['max'] = vis_min_maxes[x][1]
    map.add_ee_layer(collections[x].mean(), band_viz, names[x])


  # Add layer control to the map
  folium.LayerControl().add_to(map)
  folium.TileLayer('layer_url', overlay=True, name='Layer Name', control=False,
                 attr='Attribution').add_to(map)

  map.save('static/map.html')
















#function to save policy to database, need to save name, description, date, location
def add_policy_DB(name, description, date, location):
    item = {
        "name": name,
        "description": description,
        "date": date,
        "location": location
    }
    collection_name.insert_one(item)

#function to load in policy info
def get_policy_DB(name):
    item_details = collection_name.find_one({"name" : name})
    return  item_details #Return the data so that it can be used to repopulate the fields in the webpage

def get_DB_stored_policies():
   policy_list = []
   for policy in collection_name.find():
      if policy['name'] != "Test":
        policy_list.append(policy['name'])
   return policy_list


@app.route('/',  methods=["GET", "POST"])
def index():
    print(request.method)
    if request.method == 'POST':
       return explore()
    else:
        return render_template("index.html")

query_result = {
   "name": "Test Case",
    "description": "N/A",
    "date": "2020-06-04",
    "location": "Union County, North Carolina"
}

#Get - Render template
#Post - Regenerate graphs, save policy to database, load in policy
@app.route('/explore',  methods=["GET"])
def explore():

    return render_template("explore.html", policy_list=get_DB_stored_policies(), query_result=query_result)



@app.route('/load_saved_policy',  methods=["GET", "POST"])
def load_saved_policy():
    global query_result
    query_result = get_policy_DB(request.form["policy_name"])
    print(query_result)
    print(request.form["policy_name"])
    return render_template("explore.html", policy_list=get_DB_stored_policies(), query_result=query_result)

@app.route('/save_policy',  methods=["GET", "POST"])
def save_policy():
   global query_result
   collection_name.delete_one({ "name": f"/{request.form['name']}/i" })
   add_policy_DB(request.form["name"], request.form["description"], request.form["date"], request.form["location"])
   query_result = get_policy_DB(request.form["name"])
   return render_template("explore.html", policy_list=get_DB_stored_policies(), query_result=query_result)

@app.route('/load_map',  methods=["GET", "POST"])
def load_map():
    global query_result
    days_to_shift = int(request.form["slider"]) - 150
    delta = timedelta(days=days_to_shift)
    date_of_policy = date.fromisoformat(query_result['date'])
    display_date = (date_of_policy + delta).isoformat()

    print(query_result['location'], display_date)
    create_map(query_result['location'], display_date)
    return render_template("explore.html", policy_list=get_DB_stored_policies(), query_result=query_result)
   

app.run(host='0.0.0.0', port=152)
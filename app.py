import streamlit as st
import folium
import pandas as pd
import json
import numpy as np
from folium.features import GeoJsonTooltip
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# --- Page setup ---
st.set_page_config(page_title="International Schools", page_icon="🌍")
st.title("International Schools and Foreign Children in Denmark")

# --- Load data ---
with open("kommuner.geojson", "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

# Load school data
grundskoler_df = pd.read_csv("schools.csv")  # Your existing elementary schools
gymnasier_df = pd.read_csv("international_high_schools.csv")  # New high schools file

# Standardize kommune names in school datasets
def standardize_school_kommune(row):
    """Standardize kommune names in school data"""
    kommune = row['Kommune']
    if kommune == 'Copenhagen':
        return 'København'
    elif kommune == 'Ikast':
        return 'Ikast'
    return kommune

grundskoler_df['StandardKommune'] = grundskoler_df.apply(standardize_school_kommune, axis=1)
gymnasier_df['StandardKommune'] = gymnasier_df.apply(standardize_school_kommune, axis=1)

# Load the cleaned data
children_df = pd.read_csv("children.csv", encoding="cp1252")

# Create standardized kommune names mapping
kommune_mapping = {
    'Copenhagen': 'København',
    'København': 'København',
    'Høje-Taastrup': 'Taastrup',
    'Lyngby-Taarbæk': 'Lyngby',
    'Dragør': 'Dragør',
    'Tårnby': 'Tårnby',
    'Brøndby': 'Brøndby',
    'Ishøj': 'Ishøj',
    'Rødovre': 'Rødovre',
    'Vallensbæk': 'Vallensbæk',
    'Allerød': 'Allerød',
    'Fredensborg': 'Fredensborg',
    'Furesø': 'Furesø',
    'Halsnæs': 'Halsnæs',
    'Helsingør': 'Helsingør',
    'Hillerød': 'Hillerød',
    'Hørsholm': 'Hørsholm',
    'Christiansø': 'Christiansø',
    'Køge': 'Køge',
    'Solrød': 'Solrød',
    'Guldborgsund': 'Guldborgsund',
    'Holbæk': 'Holbæk',
    'Næstved': 'Næstved',
    'Ringsted': 'Ringsted',
    'Sorø': 'Sorø',
    'Ærø': 'Ærø',
    'Fanø': 'Fanø',
    'Sønderborg': 'Sønderborg',
    'Tønder': 'Tønder',
    'Aabenraa': 'Aabenraa',
    'Samsø': 'Samsø',
    'Ringkøbing-Skjern': 'Ringkøbing-Skjern',
    'Brønderslev': 'Brønderslev',
    'Hjørring': 'Hjørring',
    'Læsø': 'Læsø',
    'Morsø': 'Morsø'
}

# Apply mapping to standardize names (removed since data is already clean)

# --- View selection ---
view_option = st.selectbox(
    "Select data view:",
    ["Foreign Children (School Age 6-16)", "Foreign Children (High School Age 16-19)"]
)

# --- School toggles ---
col1, col2 = st.columns(2)
with col1:
    show_grundskoler = st.checkbox("Show International Grundskoler", value=True)
with col2:
    show_gymnasier = st.checkbox("Show International Gymnasier", value=True)

# --- Choose data based on selection ---
if view_option == "Foreign Children (School Age 6-16)":
    # Use school age data from children.csv
    data_df = children_df[['Kommune', 'School age']].rename(columns={'School age': 'Count'})
    data_column = "ForeignChildrenCount"
    legend_title = "Foreign Children (School Age)"
    bin_edges = [300, 1000, 2000, 3500, 5500, 7600]
    bin_colors = ["#ffffcc", "#FFEA00", "#fd8d3c", "#b22222", "#680085"]
else:
    # Use high school data from children.csv
    data_df = children_df[['Kommune', 'High school age']].rename(columns={'High school age': 'Count'})
    data_column = "InternationalStudentsCount"
    legend_title = "Foreign Children (High School Age)"
    # Different thresholds for high school students
    bin_edges = [300, 500, 800, 1200, 1500, 1817]
    bin_colors = ["#e0f2fe", "#81d4fa", "#29b6f6", "#1976d2", "#0d47a1"]


# --- Add data to GeoJSON features with name matching ---
def normalize_kommune_name(name):
    """Normalize kommune names for matching"""
    # Remove common prefixes/suffixes and normalize
    normalized = name.strip()
    
    # Handle common variations
    variations = {
        'Copenhagen': 'København',
        'København': 'København',
        'Høje-Taastrup': 'Taastrup',
        'Lyngby-Taarbæk': 'Lyngby',
        'Lyngby-Taarbæk': 'Lyngby',
        'Ikast-Brande': 'Ikast',
        'Faaborg-Midtfyn': 'Faaborg',
        'Ringkøbing-Skjern': 'Ringkøbing'
    }
    
    return variations.get(normalized, normalized)

# Create lookup dictionary with normalized names
data_lookup = {}
for _, row in data_df.iterrows():
    normalized_name = normalize_kommune_name(row['Kommune'])
    data_lookup[normalized_name] = row['Count']

# Add data to GeoJSON features
for feature in geojson_data['features']:
    kommune_name = feature['properties']['KOMNAVN']
    normalized_geojson_name = normalize_kommune_name(kommune_name)
    
    # Try exact match first, then try variations
    count = data_lookup.get(normalized_geojson_name, 0)
    if count == 0:
        # Try some common alternative lookups
        alternatives = [
            kommune_name,
            kommune_name.replace('ø', 'oe').replace('å', 'aa').replace('æ', 'ae'),
            kommune_name.split(' ')[0],  # Try first word only
        ]
        for alt in alternatives:
            count = data_lookup.get(alt, 0)
            if count > 0:
                break
    
    feature['properties'][data_column] = count

bin_labels = [f"{bin_edges[i]}–{bin_edges[i+1]-1}" for i in range(len(bin_edges)-1)]

def get_fill_color(count):
    for i, threshold in enumerate(bin_edges[1:]):
        if count < threshold:
            return bin_colors[i]
    return bin_colors[-1]

def style_function(feature):
    count = feature["properties"].get(data_column, 0)
    if count < 300:
        return {
            "fillOpacity": 0.4,
            "weight": 0.3,
            "color": "grey",
            "fillColor": "#eeeeee"
        }
    return {
        "fillOpacity": 0.8,
        "weight": 0.3,
        "color": "black",
        "fillColor": get_fill_color(count)
    }

tooltip = GeoJsonTooltip(
    fields=["KOMNAVN", data_column],
    aliases=["Kommune:", f"{legend_title}:"],
    localize=True
)

# --- Map creation ---
m = folium.Map(location=[55.9, 10.6], zoom_start=7, tiles="CartoDB Positron")

folium.GeoJson(
    geojson_data,
    name=f"{legend_title} Heatmap",
    style_function=style_function,
    tooltip=tooltip
).add_to(m)

# --- Custom cluster styling ---
cluster_js_grundskoler = """
function(cluster) {
    return new L.DivIcon({
        html: '<div style="background: #4CAF50; color: white; font-weight: bold; font-size: 12px; border-radius: 50%; width: 25px; height: 25px; text-align: center; line-height: 25px;">' + cluster.getChildCount() + '</div>',
        className: 'grundskole-cluster',
        iconSize: new L.Point(25, 25)
    });
}
"""

cluster_js_gymnasier = """
function(cluster) {
    return new L.DivIcon({
        html: '<div style="background: #2196F3; color: white; font-weight: bold; font-size: 12px; border-radius: 50%; width: 25px; height: 25px; text-align: center; line-height: 25px;">' + cluster.getChildCount() + '</div>',
        className: 'gymnasi-cluster',
        iconSize: new L.Point(25, 25)
    });
}
"""

# --- Add Grundskoler ---
if show_grundskoler:
    marker_cluster_grundskoler = MarkerCluster(
        name="International Grundskoler",
        icon_create_function=cluster_js_grundskoler
    ).add_to(m)

    for _, row in grundskoler_df.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            icon=folium.DivIcon(html=f"""
                <div style="font-size:12px; color:white; font-weight:bold; text-align:center; 
                     background:#4CAF50; border-radius:50%; width:20px; height:20px; line-height:20px;">
                    G
                </div>"""),
            popup=f"<b>{row['School Name']}</b><br>Type: Grundskole<br>Kommune: {row['Kommune']}"
        ).add_to(marker_cluster_grundskoler)

# --- Add Gymnasier ---
if show_gymnasier:
    marker_cluster_gymnasier = MarkerCluster(
        name="International Gymnasier",
        icon_create_function=cluster_js_gymnasier
    ).add_to(m)

    # Default coordinates for Danish kommuner (approximations)
    kommune_coords = {
        'København': [55.6761, 12.5683],
        'Rudersdal': [55.8, 12.5],  # Birkerød area
        'Esbjerg': [55.467, 8.452],
        'Norddjurs': [56.42, 10.77],  # Grenaa area
        'Gentofte': [55.7308, 12.5493],  # Hellerup area
        'Holbæk': [55.7167, 11.7167],
        'Ikast': [56.1333, 9.1667],
        'Kolding': [55.4904, 9.4721],
        'Nordfyn': [55.45, 10.3],  # Søndersø area
        'Nyborg': [55.3167, 10.7833],
        'Næstved': [55.2297, 11.7611],
        'Struer': [56.4833, 8.6],
        'Sønderborg': [54.9089, 9.7921],
        'Aarhus': [56.1629, 10.2039],  # Tilst area
        'Viborg': [56.4533, 9.4017],
        'Aalborg': [57.0488, 9.9217],
        'Aabenraa': [55.0467, 9.4189],
        'Frederiksberg': [55.6803, 12.5344]
    }

    for _, row in gymnasier_df.iterrows():
        # Get coordinates from mapping or use defaults
        coords = kommune_coords.get(row['StandardKommune'], [55.6761, 12.5683])
        
        # Different icons for different program types
        if "IB" in row["Program"]:
            icon_letter = "IB"
            bg_color = "#2196F3"
        elif "DFB" in row["Program"]:
            icon_letter = "F"
            bg_color = "#FF5722"
        elif "DIAP" in row["Program"]:
            icon_letter = "D"
            bg_color = "#FF9800"
        elif "EB" in row["Program"]:
            icon_letter = "E"
            bg_color = "#9C27B0"
        else:
            icon_letter = "H"
            bg_color = "#607D8B"
        
        folium.Marker(
            location=coords,
            icon=folium.DivIcon(html=f"""
                <div style="font-size:10px; color:white; font-weight:bold; text-align:center; 
                     background:{bg_color}; border-radius:50%; width:20px; height:20px; line-height:20px;">
                    {icon_letter}
                </div>"""),
            popup=f"<b>{row['School Name']}</b><br>Type: {row['Type']} Gymnasium<br>Program: {row['Program']}<br>Language: {row['Language']}<br>Kommune: {row['Kommune']}"
        ).add_to(marker_cluster_gymnasier)

# --- External legend below ---
st.markdown(f"#### Legend: {legend_title} (300+ only)")
for label, color in zip(bin_labels, bin_colors):
    st.markdown(
        f"<div style='display: flex; align-items: center;'>"
        f"<div style='width: 20px; height: 12px; background-color: {color}; margin-right: 8px;'></div>"
        f"{label}</div>", unsafe_allow_html=True
    )

# --- School type legend ---
st.markdown("#### School Types")
if show_grundskoler:
    st.markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='width: 20px; height: 20px; background-color: #4CAF50; border-radius: 50%; color: white; text-align: center; line-height: 20px; font-size: 12px; font-weight: bold; margin-right: 8px;'>G</div>"
        "International Grundskoler</div>", unsafe_allow_html=True
    )

if show_gymnasier:
    st.markdown("**International Gymnasier:**")
    st.markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='width: 20px; height: 20px; background-color: #2196F3; border-radius: 50%; color: white; text-align: center; line-height: 20px; font-size: 10px; font-weight: bold; margin-right: 8px;'>IB</div>"
        "International Baccalaureate</div>", unsafe_allow_html=True
    )
    st.markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='width: 20px; height: 20px; background-color: #FF5722; border-radius: 50%; color: white; text-align: center; line-height: 20px; font-size: 12px; font-weight: bold; margin-right: 8px;'>F</div>"
        "French Baccalaureate (DFB)</div>", unsafe_allow_html=True
    )
    st.markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='width: 20px; height: 20px; background-color: #FF9800; border-radius: 50%; color: white; text-align: center; line-height: 20px; font-size: 12px; font-weight: bold; margin-right: 8px;'>D</div>"
        "German Diploma (DIAP)</div>", unsafe_allow_html=True
    )
    st.markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='width: 20px; height: 20px; background-color: #9C27B0; border-radius: 50%; color: white; text-align: center; line-height: 20px; font-size: 12px; font-weight: bold; margin-right: 8px;'>E</div>"
        "European Baccalaureate (EB)</div>", unsafe_allow_html=True
    )

# --- Display map ---
st_folium(m, width=1000, height=600)
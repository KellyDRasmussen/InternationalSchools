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

schools_df = pd.read_csv("schools.csv")

bin_edges = [ 300, 1000, 2000, 3500, 5500, 8500]
bin_labels = [f"{bin_edges[i]}–{bin_edges[i+1]-1}" for i in range(len(bin_edges)-1)]
bin_colors = ["#ffffcc", "#FFEA00", "#fd8d3c", "#b22222", "#680085"]


def get_fill_color(count):
    for i, threshold in enumerate(bin_edges[1:]):
        if count < threshold:
            return bin_colors[i]
    return bin_colors[-1]


def style_function(feature):
    count = feature["properties"].get("ForeignChildrenCount", 0)
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
    fields=["KOMNAVN", "ForeignChildrenCount"],
    aliases=["Kommune:", "Foreign Children:"],
    localize=True
)

# --- Map creation ---
m = folium.Map(location=[55.9, 10.6], zoom_start=7, tiles="CartoDB Positron")

folium.GeoJson(
    geojson_data,
    name="Foreign Children Heatmap",
    style_function=style_function,
    tooltip=tooltip
).add_to(m)

# --- Custom cluster styling (no blob) ---
cluster_js = """
function(cluster) {
    return new L.DivIcon({
        html: '<div style="background: none; color: #333; font-weight: bold; font-size: 13px;">' + cluster.getChildCount() + '</div>',
        className: 'transparent-cluster',
        iconSize: new L.Point(30, 30)
    });
}
"""

# --- School marker toggle ---
show_schools = True

if show_schools:
    marker_cluster = MarkerCluster(
        name="Schools",
        icon_create_function=cluster_js
    ).add_to(m)

    for _, row in schools_df.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            icon=folium.DivIcon(html=f"""
                <div style="font-size:13px; color:#333; font-weight:bold; text-align:center;">
                    1
                </div>"""),
            popup=row["School Name"]
        ).add_to(marker_cluster)

# --- External legend below ---
st.markdown("#### Legend: Foreign Children (300+ only)")
for label, color in zip(bin_labels, bin_colors):
    st.markdown(
        f"<div style='display: flex; align-items: center;'>"
        f"<div style='width: 20px; height: 12px; background-color: {color}; margin-right: 8px;'></div>"
        f"{label}</div>", unsafe_allow_html=True
    )

# --- Display map ---
st_folium(m, width=1000, height=600)

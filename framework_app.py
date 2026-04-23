import numpy as np
import pandas as pd
import geopandas as gpd

import plotly.express as px
import streamlit as st

##########################################
#######Het definieren van de functies####
#########################################
# Dictionaries
legend_labels = {
    "d_energiequote": "Afname in procentpunt",
    "d_%": "Afname in procentpunt"
}

title_labels = {
    "d_energiequote": "Afname energiequote van huishoudens met energiearmoede",
    "d_%": "Afname aandeel huishoudens met energiearmoede met een energiequote van meer dan acht procent"
}

def get_gemeentegrenzen(): #Deze functie laad de grenzen van de gemeentes in voor onze ruimtelijke kaart
 
    gdf = gpd.read_file("data/wijkenbuurten_2023_v3.gpkg", layer="gemeenten") #Het inladen van de 2023 gemeentegrenzenkaart van het CBS
    gdf = gdf.to_crs(epsg=4326) # Converteren naar WGS84 voor de kaart

    # Filter columns
    gdf = gdf.filter(['gemeentenaam','geometry']) #Het bestand bevat alle CBS data van elke gemeente, dat is niet nodig

    return gdf


def get_output(): #Deze functie laad de indicatoren per gemeente

    output = pd.read_csv('data/data_kaarten_dashboard_red.csv', index_col = 0) #Het inladen van jouw data
    output = output.rename(columns={
        "GM_NAAM.x": "gemeentenaam",
        "Gemiddelde.verandering.energiequote..absoluut.": "d_energiequote",
        "Verandering.percentage.boven.8...tov.lihelek.": "d_%"
    }) #Simpele kolomnamen om de code overzichtelijk te houden
    
    return output

 
def get_fig(gdf, output): #Deze functie maakt de daadwerkelijke kaart

    plot_gdf = gdf.merge(output, on="gemeentenaam") #Combineren grenzen per gemeente met waarde indicator per gemeente
    plot_gdf = plot_gdf.dropna(subset=[plotted_column]) #Alleen plotten wat mensen willen plotten (aangegeven in de selectbox onder)

    fig = px.choropleth_map(
        plot_gdf,
        geojson = plot_gdf.geometry.__geo_interface__,
        locations = plot_gdf.index,
        color=plotted_column,
        labels={plotted_column: legend_labels[plotted_column]},
        center={"lat": 52.15, "lon": 5.15}, #Zodat de kaart in Nederland begint en niet in de Atlantische Oceaan
        zoom=7.2 #Zodat je meteen overzicht hebt
    )

    fig.update_layout(
        height=1200, #Zodat de kaart niet superklein is
        title_text=title_labels[plotted_column],
        title_x=0 # align title to the left 
    ) 

    return fig

##########################################
############The actual app###############
#########################################

st.set_page_config(layout="wide") #Kaart even breed als scherm
# st.markdown("<style>.stApp { background-color: white; }</style>", unsafe_allow_html=True) #App krijgt witte achtergrond voor TNO

gdf = get_gemeentegrenzen() #De gemeentegrenzen inladen

output = get_output() #De csv met data inladen

plotted_column = st.selectbox("Indicator", ["d_energiequote", "d_%"], # De gebruiker kan kiezen welke indicator hij/zij wil zien
                              format_func=lambda x:title_labels[x]) # Omzetten naar titel tekst

if st.button('render'): #Als je op render klikt, wordt de figuur geladen
    fig = get_fig(gdf, output)
    st.plotly_chart(fig, use_container_width=True)

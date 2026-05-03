from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import yaml

import plotly.express as px
import streamlit as st

##########################################
#######Het definieren van de functies####
#########################################

# Functie om juiste versie gemeente-indeling gpkg op te zoeken
def find_gpkg_for_version(version):
    matches = list(
        Path("data/wijkenbuurten").glob(f"*{version}.gpkg")
    )

    if not matches:
        raise FileNotFoundError(f"Geen GPKG gevonden voor versie {version}")

    if len(matches) > 1:
        print(f"⚠️ Meerdere GPKGs gevonden voor {version}, gebruik eerste")

    return matches[0]


# Functie om metadata in te lezen en bijbehorende gpkg zoeken
def load_indicator_datasets():
    datasets = {}
    indicators = {}

    metadata_dir = Path("metadata")
    data_dir = Path("data/indicatoren")

    for meta_file in metadata_dir.glob("*.meta.yaml"):
        
        # 1. Metadata lezen
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f)

        dataset_id = meta["dataset_id"]
        csv_path = data_dir / f"{dataset_id}.csv"

        # 2. Bijbehorende GPKG bepalen
        gpkg_path = find_gpkg_for_version(meta["gwb_version"])

        # 3. Dataset registreren
        datasets[dataset_id] = {
            "csv_path": csv_path,
            "layer": meta["layer_naam"],
            "version": meta["gwb_version"],
            "key": meta["key"],
            "gpkg_path": gpkg_path,
        }

        # 4. Indicatoren registreren
        for indicator, cfg in meta["indicators"].items():
            indicators[indicator] = {
                "dataset": dataset_id,
                "title": cfg["title"],
                "legend": cfg["legend"],
                "theme": cfg["theme"],
                "subject": cfg["subject"],
                "precision": cfg.get("precision", 1),
                "unit": cfg.get("unit", ""),
                "link": cfg["link"]
            }

    return datasets, indicators

# DATASETS is een lijst met bestanden, de bijbehorende gpkg versie en andere metadata
# INDICATORS is een lijst met alle indicatoren hun kenmerken

DATASETS, INDICATORS = load_indicator_datasets()
themes = {cfg["theme"] for cfg in INDICATORS.values()}

# Functie om databestanden in te laden, de bijbehorende gpkg in te laden en beiden te mergen 

@st.cache_data(show_spinner=False)
def load_dataset(dataset_id):
    cfg = DATASETS[dataset_id]

    # CSV
    df = pd.read_csv(cfg["csv_path"])
    df = df.drop(columns=["geometry"], errors="ignore") # Verwijder eventuele bestaande kolom "geometry"

    # GPKG
    gdf = gpd.read_file(cfg["gpkg_path"], layer=cfg["layer"])

    gdf = (
        gdf.dissolve(by=cfg["key"], as_index=False)
    )
    gdf = gdf.to_crs(epsg=4326)
    gdf = gdf.filter(['gemeentenaam','geometry'])
    
    # Merge één keer
    plot_gdf = gdf.merge(
        df,
        on=cfg["key"],
        how="left"
    )
    

    return plot_gdf

 
def get_fig(plot_gdf): #Deze functie maakt de daadwerkelijke kaart

    #plot_gdf = plot_gdf.dropna(subset=[indicator]) #Alleen plotten wat mensen willen plotten (aangegeven in de selectbox onder)
    plot_gdf["_color_value"] = plot_gdf[indicator].astype(float).fillna(-999)
   
    fig = px.choropleth_map(
        plot_gdf,
        geojson = plot_gdf.geometry.__geo_interface__,
        locations = plot_gdf.index,
        color="_color_value",
        color_continuous_scale=[[0.0, "#f0f3fa"],[1.0, "#123eb7"]],
        labels={"_color_value": INDICATORS[indicator]["legend"]},
        custom_data=["gemeentenaam"],
        range_color=(plot_gdf.loc[plot_gdf[indicator].notna(), indicator].min(), plot_gdf.loc[plot_gdf[indicator].notna(), indicator].max()),
        center={"lat": 52.15, "lon": 5.15}, #Zodat de kaart in Nederland begint en niet in de Atlantische Oceaan
        zoom=6.5, #Zodat je meteen overzicht hebt
        map_style="white-bg"
    )

    fig.update_layout(
        height=800, #Zodat de kaart niet superklein is
        title_text=INDICATORS[indicator]["title"], #titel/beschrijving figuur
        title_x=0, # align title to the left
        title_font=dict(size=24)
     ) 
    
    #Linkje naar publicatie
    link = INDICATORS[indicator]["link"]
    fig.add_annotation(
        text=f'<a href="{link}" target="_blank">Link naar publicatie &#8599;</a>',
        x=0,
        y=1.03,
        xref="paper",
        yref="paper",
        showarrow=False,
        align="left",
        font=dict(size=14, color="#000000"),
    )


    precision = INDICATORS[indicator]["precision"]
    unit = INDICATORS[indicator]["unit"]

    fig.update_traces(
        hovertemplate=(
            "%{customdata[0]}: "
            f"%{{z:.{precision}f}}{unit}"
            "<extra></extra>"
        )
    )


    return fig

##########################################
############The actual app###############
#########################################

st.set_page_config(layout="wide") #Kaart even breed als scherm
# st.markdown("<style>.stApp { background-color: white; }</style>", unsafe_allow_html=True) #App krijgt witte achtergrond voor TNO

#gdf = get_gemeentegrenzen() #De gemeentegrenzen inladen

#output = get_output() #De csv met data inladen

# with st.sidebar:
#     st.subheader("Onderwerp")

#     selected_theme = st.selectbox(
#         "Kies een onderwerp",  
#         options=themes
#         )

# indicators_in_theme = [
#     indicator
#     for indicator, cfg in INDICATORS.items()
#     if cfg["theme"] == selected_theme
# ]
   
from collections import defaultdict

# theme -> subject -> list of indicators
indicators_by_theme_subject = defaultdict(lambda: defaultdict(list))

for indicator, cfg in INDICATORS.items():
    theme = cfg["theme"]
    subject = cfg.get("subject", "Overig")
    indicators_by_theme_subject[theme][subject].append(indicator)

if "indicator" not in st.session_state:
    st.session_state.indicator = None

with st.sidebar:
    st.subheader("Onderwerpen")

    for theme, subjects in sorted(indicators_by_theme_subject.items()):
        with st.expander(theme, expanded=False):

            for subject, indicators in sorted(subjects.items()):
                # Subject header (niet uitklapbaar)
                st.markdown(f"**{subject}**")

                for indicator in indicators:
                    if indicator == st.session_state.indicator:
                        st.button(
                            INDICATORS[indicator]["title"],
                            key=f"indicator_btn_{indicator}",
                            use_container_width=True,
                            disabled=True
                        )
                    else:
                        if st.button(
                            INDICATORS[indicator]["title"],
                            key=f"indicator_btn_{indicator}",
                            use_container_width=True
                        ):
                            st.session_state.indicator = indicator

indicator = st.session_state.indicator

if indicator is not None:
    dataset_id = INDICATORS[indicator]["dataset"]

    plot_gdf = load_dataset(dataset_id)
    fig = get_fig(plot_gdf)

    st.plotly_chart(
        fig,
        use_container_width=True
    )
else:
    st.info("Selecteer een indicator om de kaart te tonen.")




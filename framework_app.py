from pathlib import Path
import pandas as pd
import geopandas as gpd

from collections import defaultdict

import plotly.express as px
import streamlit as st

from load_metadata import load_metadata #Loading the metadata, which only has to be done once
from get_fig_with_graph import get_fig_with_graph

##########################################
#######Het definieren van de functies####
#########################################


# Functie om metadata in te lezen en bijbehorende gpkg zoeken



# Functie om databestanden in te laden, de bijbehorende gpkg in te laden en beiden te mergen 

@st.cache_data(show_spinner=False)
def load_dataset(dataset_id):
    dataset_meta = DATASETS_META[dataset_id]

    # CSV
    df = pd.read_csv(dataset_meta["csv_path"])
    df = df.drop(columns=["geometry"], errors="ignore") # Verwijder eventuele bestaande kolom "geometry"

    # GPKG
    gdf = gpd.read_file(dataset_meta["gpkg_path"], layer=dataset_meta["layer"])

    gdf = (
        gdf.dissolve(by=dataset_meta["key"], as_index=False)
    )
    gdf = gdf.to_crs(epsg=4326)
    gdf = gdf.filter(['gemeentenaam','geometry'])

    # Merge één keer
    plot_gdf = gdf.merge(
        df,
        on=dataset_meta["key"],
        how="left"
    )
    

    return plot_gdf

 
##########################################
############The actual app###############
#########################################

st.set_page_config(layout="wide") #Kaart even breed als scherm

# DATASETS_META is een lijst met bestanden, de bijbehorende gpkg versie en andere metadata
# INDICATORS_META is een lijst met alle indicatoren hun kenmerken
DATASETS_META, INDICATORS_META = load_metadata()

themes = {indicator_meta["theme"] for indicator_meta in INDICATORS_META.values()}

# theme -> subject -> list of indicators
indicators_by_theme_subject = defaultdict(lambda: defaultdict(list))

for indicator, indicator_meta in INDICATORS_META.items():
    theme = indicator_meta["theme"]
    subject = indicator_meta.get("subject", "Overig")
    indicators_by_theme_subject[theme][subject].append(indicator)

if "indicator" not in st.session_state:
    st.session_state.indicator = None

if "clicked_gemeente" not in st.session_state: # Klik op gemeentes om grafiek te laten zien
    st.session_state.clicked_gemeente = None

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
                            INDICATORS_META[indicator]["title"],
                            key=f"indicator_btn_{indicator}",
                            width='stretch',
                            disabled=True
                        )
                    else:
                        if st.button(
                            INDICATORS_META[indicator]["title"],
                            key=f"indicator_btn_{indicator}",
                            width='stretch'
                        ):
                            st.session_state.indicator = indicator

indicator = st.session_state.indicator

if indicator is not None:
    dataset_id = INDICATORS_META[indicator]["dataset"]

    plot_gdf = load_dataset(dataset_id)
    fig = get_fig_with_graph(plot_gdf, indicator, DATASETS_META, INDICATORS_META)

    #Het toevoegen van de grafiek als gebruiker op een gemeente klikt
    col_map, col_trend = st.columns([2, 1])

    with col_map: # on_select="rerun" zorgt dat Streamlit herlaadt zodra de gebruiker op de kaart klikt
        event = st.plotly_chart(fig, width='stretch', on_select="rerun")

    if event.selection.points: # Als de gebruiker op een gemeente heeft geklikt, sla de naam op in session_state
        st.session_state.clicked_gemeente = event.selection.points[0]["customdata"][0]

    with col_trend:
        if st.session_state.clicked_gemeente is not None:
            gemeente = st.session_state.clicked_gemeente

            df_trend = plot_gdf.loc[plot_gdf.gemeentenaam == gemeente, ["JAAR", indicator]]
            df_trend = df_trend.sort_values("JAAR")

            fig_trend = px.line(
                df_trend,
                x="JAAR",
                y=indicator,
                title=f"{INDICATORS_META[indicator]['title']} — {gemeente}",
                markers=True,
                labels={indicator: INDICATORS_META[indicator]["legend"]}
            )
            st.plotly_chart(fig_trend, width='stretch')
        else:
            st.info("Klik op een gemeente om de trend te zien.")
else:
    st.info("Selecteer een indicator om de kaart te tonen.")




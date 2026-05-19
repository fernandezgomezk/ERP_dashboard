from pathlib import Path
import pandas as pd
import geopandas as gpd

from collections import defaultdict

import streamlit as st

from load_metadata import load_metadata #Loading the metadata, which only has to be done once
from get_fig_with_graph import get_fig_with_graph
from get_fig_no_graph import get_fig_no_graph
from get_boxplot import get_boxplot


# Functie om databestanden in te laden, de bijbehorende gpkg in te laden en beiden te mergen 
@st.cache_data(show_spinner=False)
def load_dataset(dataset_id, datasets_meta):
    dataset_meta = datasets_meta[dataset_id]

    # CSV
    df = pd.read_csv(dataset_meta["csv_path"], sep=None, engine="python")
    
    if "gpkg_path" not in dataset_meta or dataset_meta["gpkg_path"] is None:
            return df  

    df = df.drop(columns=["geometry"], errors="ignore") # Verwijder eventuele bestaande kolom "geometry"

    # GPKG
    gdf = gpd.read_file(dataset_meta["gpkg_path"], layer=dataset_meta["layer"])

    gdf = gdf[gdf["water"] == "NEE"] # Water wegfilteren uit geometrie

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


st.set_page_config(layout="wide") #Kaart even breed als scherm

# DATASETS_META is een lijst met bestanden, de bijbehorende gpkg versie en andere metadata
# INDICATORS_META is een lijst met alle indicatoren hun kenmerken
DATASETS_META, INDICATORS_META = load_metadata()

# theme -> subject -> list of indicators
indicators_by_theme_subject = defaultdict(lambda: defaultdict(list))

for indicator, indicator_meta in INDICATORS_META.items():
    theme = indicator_meta["theme"]
    subject = indicator_meta.get("subject", "Overig")
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
    visualization_type = INDICATORS_META[indicator]["visualization_type"]

    dataset_meta = DATASETS_META[dataset_id]

    plot_df = load_dataset(dataset_id, DATASETS_META)

    # ✅ NEW: filter UI (only if categories exist)
    if "categories" in dataset_meta:
        df_filtered = plot_df.copy()

        for col in dataset_meta["categories"]:
            options = plot_df[col].dropna().unique()
            selected = st.selectbox(col, options)

            df_filtered = df_filtered[df_filtered[col] == selected]
    else:
        df_filtered = plot_df

    if visualization_type == "map_with_timegraph_per_area":
        get_fig_with_graph(plot_gdf, indicator, DATASETS_META, INDICATORS_META)

    elif visualization_type == "map":
        get_fig_no_graph(plot_gdf, indicator, DATASETS_META, INDICATORS_META)

    elif visualization_type == "boxplot":
        get_boxplot(df_filtered, indicator, dataset_meta, INDICATORS_META)

else:
    st.info("Selecteer een indicator om de kaart te tonen.")

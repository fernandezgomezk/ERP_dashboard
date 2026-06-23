from pathlib import Path
import pandas as pd
import geopandas as gpd
import csv
import sys

from collections import defaultdict

import streamlit as st
from streamlit.logger import get_logger

from load_metadata import load_metadata #Loading the metadata, which only has to be done once
from get_fig_with_graph import get_fig_with_graph
from get_fig_no_graph import get_fig_no_graph
from get_boxplot import get_boxplot

logger = get_logger("app.log")
logger.info("App script started")

# Functie om databestanden in te laden, de bijbehorende gpkg in te laden en beiden te mergen 
@st.cache_data(show_spinner=False)
def load_dataset(dataset_id, datasets_meta):
    logger.info(f"load_dataset: {dataset_id}")
    dataset_meta = datasets_meta[dataset_id]

    # CSV
    csv.field_size_limit(sys.maxsize)
    df = pd.read_csv(dataset_meta["csv_path"], sep=None, engine="python")
    logger.info(f"after read_csv. {dataset_meta['csv_path']=}; {len(df)=}")

    if dataset_meta.get("gpkg_path") is None:
        return df

    df = df.drop(columns=["geometry"], errors="ignore") # Verwijder eventuele bestaande kolom "geometry"

    # GPKG
    gdf = gpd.read_file(dataset_meta["gpkg_path"], layer=dataset_meta["layer"])
    logger.info(f"after reading of gpkg. {dataset_meta['gpkg_path']=}; {dataset_meta['layer']=}; {len(gdf)=}")

    key_gwb = dataset_meta["key_gwb"]
    gdf = gdf[[key_gwb, "geometry"]]

    gdf = gdf.to_crs(epsg=4326)
    plot_df = gdf.merge(df, left_on=key_gwb, right_on=dataset_meta["key"], how="left")
    logger.info(f"after merge. ({len(plot_df)=})")

    return plot_df


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

if "clicked_gemeente" not in st.session_state:
    st.session_state.clicked_gemeente = None

selected_filters = {}
plot_df = None
dataset_meta = None

indicator = st.session_state.indicator

if indicator is not None:
    dataset_id = INDICATORS_META[indicator]["dataset"]
    dataset_meta = DATASETS_META[dataset_id]
    plot_df = load_dataset(dataset_id, DATASETS_META)


with st.sidebar:
    st.subheader("Onderwerpen")

    for theme, subjects in sorted(indicators_by_theme_subject.items()):
        with st.expander(theme, expanded=False):

            for subject, indicators in sorted(subjects.items()):
                # Subject header (niet uitklapbaar)
                st.markdown(f"**{subject}**")

                for indicator_name in indicators:

                    if indicator_name == st.session_state.indicator:
                        st.button(
                            INDICATORS_META[indicator_name]["title"],
                            key=f"indicator_btn_{indicator_name}",
                            width="stretch",
                            disabled=True
                        )

                        dataset_id = INDICATORS_META[indicator_name]["dataset"]
                        dataset_meta = DATASETS_META[dataset_id]

                        if (
                            plot_df is not None
                            and dataset_meta.get("categories")
                        ):

                            selected_filters.clear()

                            for col in dataset_meta["categories"]:
                                options = sorted(plot_df[col].dropna().unique())

                                st.markdown(f"&nbsp;&nbsp;**{col}**", unsafe_allow_html=True)
                                
                                if f"filter_{col}" not in st.session_state:
                                    st.session_state[f"filter_{col}"] = list(options)

                                current_selection = st.session_state[f"filter_{col}"]
                                new_selection = []

                                for opt in options:
                                    
                                    if st.checkbox(
                                        str(opt),
                                        value=(opt in current_selection),
                                        key=f"filter_{col}_{opt}"
                                    ):
                                        new_selection.append(opt)

                                if len(new_selection) == 0:
                                    new_selection = list(options)

                                st.session_state[f"filter_{col}"] = new_selection
                                selected_filters[col] = new_selection

                    else:
                        if st.button(
                            INDICATORS_META[indicator_name]["title"],
                            key=f"indicator_btn_{indicator_name}",
                            width="stretch"
                        ):
                            st.session_state.indicator = indicator_name
                            
                            st.session_state.clicked_gemeente = None

                            st.rerun()

indicator = st.session_state.indicator

if indicator is not None:

    meta = INDICATORS_META[indicator]

    # --- Title ---
    st.title(meta["title"])

    # --- Description ---
    st.markdown(
        f"""
        <div style="font-size:18px; color:#444; line-height:1.5;">
            {meta["description"]}
        </div>
        """,
        unsafe_allow_html=True
    )

    # --- Link ---
    st.markdown(
        f"""
        <div style="margin-top:6px;">
            <a href="{meta["link"]}" target="_blank">
                Link naar publicatie &#8599;
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

    dataset_id = INDICATORS_META[indicator]["dataset"]
    dataset_meta = DATASETS_META[dataset_id]
    logger.info(f"Show indicator. {indicator=}; {dataset_id=}")
    plot_df = load_dataset(dataset_id, DATASETS_META)
    logger.info(f"After loading dataset. {dataset_id=}")

    visualization_type = INDICATORS_META[indicator]["visualization_type"]

    if visualization_type == "map_with_timegraph_per_area":

        col_map, col_trend = st.columns([2, 1])

        # --- FIRST: build map ---
        fig, _ = get_fig_with_graph(
            plot_df,
            indicator,
            DATASETS_META,
            INDICATORS_META,
            st.session_state.clicked_gemeente
        )

        with col_map:
            event = st.plotly_chart(fig, width="stretch", on_select="rerun")

        # --- SECOND: update state from click ---
        if event is not None and event.selection is not None and event.selection.points:
            st.session_state.clicked_gemeente = event.selection.points[0]["customdata"][0]

        # --- THIRD: NOW compute trend with UPDATED state ---
        _, fig_trend = get_fig_with_graph(
            plot_df,
            indicator,
            DATASETS_META,
            INDICATORS_META,
            st.session_state.clicked_gemeente
        )

        # --- FOURTH: display ---
        with col_trend:
            if st.session_state.clicked_gemeente is None:
                st.info("Klik op een gemeente om de trend te zien.")
            elif fig_trend is not None:
                st.plotly_chart(fig_trend, width="stretch")

    elif visualization_type == "map":

        fig = get_fig_no_graph(
            plot_df,
            indicator,
            DATASETS_META,
            INDICATORS_META
        )

        st.plotly_chart(fig, width="stretch")

    elif visualization_type == "boxplot":

        if not selected_filters:
            st.warning("Selecteer filters om boxplot te tonen.")
        else:
            fig = get_boxplot(
                plot_df,
                indicator,
                dataset_meta,
                INDICATORS_META,
                selected_filters
            )

            st.plotly_chart(fig, width="stretch")
    logger.info("After showing indicator")

else:
    st.info("Selecteer een indicator.")

logger.info("App script finished")

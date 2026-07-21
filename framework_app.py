from pathlib import Path
import pandas as pd
import geopandas as gpd
import csv
import sys

from collections import defaultdict

import streamlit as st
from streamlit.logger import get_logger

from load_metadata import load_metadata
from get_fig_with_graph import get_fig_with_graph
from get_fig_no_graph import get_fig_no_graph, get_side_by_side_maps
from get_boxplot import get_boxplot

logger = get_logger("app.log")
logger.info("App script started")

# =========================
# DATA INLADEN
# =========================@st.cache_data(show_spinner=False)
def load_dataset(dataset_id, datasets_meta):
    logger.info(f"load_dataset: {dataset_id}")
    dataset_meta = datasets_meta[dataset_id]

    # CSV
    csv.field_size_limit(sys.maxsize)

    df = pd.read_csv(dataset_meta["csv_path"], 
                     sep=None, 
                     engine="python", 
                     encoding = "utf-8-sig",
                     dtype={dataset_meta["key"]: str})
    
    logger.info(f"after read_csv. {dataset_meta['csv_path']=}; {len(df)=}; {df.columns=}")

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

# =========================
# METADATA
# =========================
DATASETS_META, INDICATORS_META = load_metadata()

indicators_by_theme_subject = defaultdict(lambda: defaultdict(list))

for indicator, variants in INDICATORS_META.items():
    meta0 = variants[0]
    theme = meta0["theme"]
    subject = meta0.get("subject", "Overig")
    indicators_by_theme_subject[theme][subject].append(indicator)


# =========================
# SESSION STATE
# =========================
if "indicator" not in st.session_state:
    st.session_state.indicator = None

if "aggregation" not in st.session_state:
    st.session_state.aggregation = None

if "clicked_area" not in st.session_state:
    st.session_state.clicked_area = None


indicator = st.session_state.indicator
selected_variant = None
labels = []
dataset_map = {}

# =========================
# VARIANT SELECTION
# =========================
if indicator is not None:

    variants = INDICATORS_META[indicator]

    for v in variants:
        dataset_meta_tmp = DATASETS_META[v["dataset"]]
        label = dataset_meta_tmp.get(
            "aggregation_label",
            dataset_meta_tmp["key"]
        )
        labels.append(label)
        dataset_map[label] = v["dataset"]

    if st.session_state.aggregation is None:
        st.session_state.aggregation = dataset_map[labels[0]]

    selected_variant = next(
        v for v in variants
        if v["dataset"] == st.session_state.aggregation
    )


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.subheader("Onderwerpen")

    for theme, subjects in sorted(indicators_by_theme_subject.items()):
        with st.expander(theme, expanded=False):

            for subject, indicators in sorted(subjects.items()):
                st.markdown(f"**{subject}**")

                for indicator_name in indicators:
                    title = INDICATORS_META[indicator_name][0]["title"]

                    safe_name = indicator_name.replace(" ", "_").replace("(", "").replace(")", "")
                    btn_key = f"indicator_btn_{theme}_{subject}_{safe_name}"

                    if indicator_name == st.session_state.indicator:
                        st.button(title, key=btn_key, disabled=True, use_container_width=True)

                        # -------- CATEGORY FILTERS (BOXPLOT) --------
                        if selected_variant is not None:
                            dataset_id = selected_variant["dataset"]
                            dataset_meta_current = DATASETS_META[dataset_id]
                            plot_df_current = load_dataset(dataset_id, DATASETS_META)

                            categories = dataset_meta_current.get("categories", [])

                            if categories:
                                st.markdown("**Selecteer subpopulaties**")

                                for col in categories:
                                    options = sorted(plot_df_current[col].dropna().unique())

                                    state_key = f"filter_{dataset_id}_{col}"

                                    if state_key not in st.session_state:
                                        st.session_state[state_key] = options.copy()

                                    selected = st.multiselect(
                                        col,
                                        options,
                                        default=st.session_state[state_key],
                                        key=f"{state_key}_widget"
                                    )

                                    if len(selected) == 0:
                                        selected = options.copy()

                                    st.session_state[state_key] = selected

                    else:
                        if st.button(title, key=btn_key, use_container_width=True):
                            st.session_state.indicator = indicator_name
                            st.session_state.aggregation = None
                            st.session_state.clicked_area = None
                            st.rerun()


# =========================
# MAIN PANEL
# =========================
if indicator is not None and selected_variant is not None:

    meta = selected_variant
    dataset_id = meta["dataset"]
    dataset_meta = DATASETS_META[dataset_id]

    plot_df = load_dataset(dataset_id, DATASETS_META)

    # -------- CATEGORY FILTER COLLECTION --------
    selected_filters = {}
    for col in dataset_meta.get("categories", []):
        key = f"filter_{dataset_id}_{col}"
        if key in st.session_state:
            selected_filters[col] = st.session_state[key]

    # -------- UI HEADER --------
    st.title(meta["title"])

    st.markdown(
        f"""
        <div style="font-size:18px; color:#444; line-height:1.5;">
            {meta["description"]}
        </div>
        """,
        unsafe_allow_html=True
    )

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

    # -------- AGGREGATION SELECTOR --------
    if len(labels) > 1:
        selected_label = st.segmented_control("", labels, default=labels[0])

        if dataset_map[selected_label] != st.session_state.aggregation:
            st.session_state.aggregation = dataset_map[selected_label]
            st.session_state.clicked_area = None
            st.rerun()

    # =========================
    # VISUALIZATION
    # =========================
    visualization_type = meta["visualization_type"]

    # -------- MAP --------
    if visualization_type == "map":

        option_columns = dataset_meta.get("options", [])
        selected_option = None


        # CASE 1: no options
        if not option_columns:
            selected_option = None

        # CASE 2: single column → single select (exclusive)
        elif len(option_columns) == 1:
            col = option_columns[0]
            options = sorted(plot_df[col].dropna().unique())

            state_key = f"option_{dataset_id}_{col}"

            if state_key not in st.session_state:
                st.session_state[state_key] = options[0]

            selected = st.selectbox(
                f"Selecteer {col}",
                options,
                index=options.index(st.session_state[state_key])
                if st.session_state[state_key] in options else 0,
                key=f"{state_key}_widget"
            )

            st.session_state[state_key] = selected
            selected_option = {col: selected}

        # CASE 3: multiple columns → cascading dropdowns (exclusive per column)
        else:
            selected_option = {}
            filtered_df = plot_df.copy()

            st.markdown("### Selectie")

            cols = st.columns(len(option_columns))

            for i, col in enumerate(option_columns):
                with cols[i]:
                    options = sorted(filtered_df[col].dropna().unique())

                    state_key = f"option_{dataset_id}_{col}"

                    if state_key not in st.session_state:
                        st.session_state[state_key] = options[0]

                    current_value = st.session_state[state_key]
                    if current_value not in options:
                        current_value = options[0]

                    selected = st.selectbox(
                        col,
                        options,
                        index=options.index(current_value),
                        key=f"{state_key}_widget"
                    )

                    st.session_state[state_key] = selected
                    selected_option[col] = selected

                # Filter for next dropdown (grouping)
                filtered_df = filtered_df[filtered_df[col] == selected]
                         
        # Build figure WITH selected_option
        fig = get_fig_no_graph(
            plot_df,
            indicator,
            dataset_meta,
            meta,
            selected_option=selected_option
        )

        st.plotly_chart(fig, use_container_width=True)

    # -------- SIDE BY SIDE --------
    elif visualization_type == "side_by_side_maps":

        map_figures = get_side_by_side_maps(
            plot_df,
            meta,
            dataset_meta
        )

        col_left, col_right = st.columns(2)
        (title_left, fig_left), (title_right, fig_right) = map_figures

        with col_left:
            st.subheader(title_left)
            st.plotly_chart(fig_left, width="stretch")

        with col_right:
            st.subheader(title_right)
            st.plotly_chart(fig_right, width="stretch")

    # -------- BOXPLOT --------
    elif visualization_type == "boxplot":

        if not selected_filters:
            st.warning("Selecteer filters om boxplot te tonen.")
        else:
            fig = get_boxplot(
                plot_df,
                indicator,
                dataset_meta,
                meta,
                selected_filters
            )

            st.plotly_chart(fig, use_container_width=True)
    logger.info("After showing indicator")


else:
    st.info("Selecteer een indicator.")

logger.info("App script finished")

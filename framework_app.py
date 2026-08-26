import pandas as pd
import geopandas as gpd
import csv
import sys

from collections import defaultdict

import streamlit as st
from streamlit.logger import get_logger

from load_metadata import load_metadata
from get_fig_no_graph import get_fig_no_graph
from get_boxplot import get_boxplot
from get_attributes_for_area import get_attributes_for_area

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

    # Naam gebied behouden ook al is het niet de key
    area_name_field = dataset_meta.get("area_name_field")
    cols = [key_gwb, "geometry"]

    if area_name_field and area_name_field in gdf.columns and area_name_field != key_gwb:
        cols.append(area_name_field)

    gdf = gdf[cols]

    # Merge geometry aan indicator
    gdf = gdf.to_crs(epsg=4326)
    plot_df = gdf.merge(df, left_on=key_gwb, right_on=dataset_meta["key"], how="left")
    logger.info(f"after merge. ({len(plot_df)=})")

    return plot_df


st.set_page_config(layout="wide") #Kaart even breed als scherm

# =========================
# METADATA
# =========================
DATASETS_META, INDICATORS_META, ATTRIBUTES_META = load_metadata()

indicators_by_theme_subject = defaultdict(lambda: defaultdict(list))

for indicator, variants in INDICATORS_META.items():
    meta0 = variants[0]
    theme = meta0["theme"]
    subject = meta0["subject"]
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
selected_number_of_maps = 1

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
                # Show the subject as a clickable button (selects the first
                # indicator in that subject). Indicators are shown in the
                # main panel, so the sidebar only provides subject-level entry.
                #if subject:
                #    st.markdown(f"**{subject}**")

                if not indicators:
                    continue

                first_indicator = indicators[0]
                subject_safe = str(subject).replace(" ", "_").replace("(", "").replace(")", "")
                subj_btn_key = f"subject_btn_{theme}_{subject_safe}"

                # If the currently selected indicator belongs to this subject,
                # disable the button to show it's active.
                is_active = st.session_state.get("indicator") in indicators

                if is_active:
                    st.button(subject, key=subj_btn_key, disabled=True, width="stretch")
                else:
                    if st.button(subject, key=subj_btn_key, width="stretch"):
                        st.session_state.indicator = first_indicator
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

    # Note: Title/description/link are rendered per-map below. This keeps
    # the main panel clean when multiple maps are shown and attaches
    # metadata to each map's column.
    # -------- UI HEADER --------
    st.caption(f"{meta["theme"]} > {meta["subject"]}" if meta["subject"] and meta["subject"] != meta["theme"] else meta["theme"])

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
                         
        # Render maps: allow selecting multiple map-type indicators (from
        # `INDICATORS_META`) to show side-by-side. If no multiple selection is
        # made, show the single indicator as before.
        # Allow comparing multiple map indicators side-by-side.
        # Find candidate indicators that are maps for this dataset.
        candidate_inds = []
        for ind_name, variants in INDICATORS_META.items():
            for v in variants:
                if v.get("dataset") == dataset_id and v.get("visualization_type") == "map":
                    candidate_inds.append(ind_name)
                    break

        # Build title->indicator mapping for display
        title_by_ind = {}
        titles = []
        for ind in candidate_inds:
            # Prefer the variant for this dataset to get its title
            variant = next((v for v in INDICATORS_META[ind] if v.get("dataset") == dataset_id), INDICATORS_META[ind][0])
            title = variant.get("title", ind)
            title_by_ind[title] = ind
            titles.append(title)

        # Default selection: current indicator's title if present
        current_title = None
        if indicator in INDICATORS_META:
            variant_cur = next((v for v in INDICATORS_META[indicator] if v.get("dataset") == dataset_id), INDICATORS_META[indicator][0])
            current_title = variant_cur.get("title", indicator)

        # Replace multiselect with toggle-style buttons: show titles as
        # pressable buttons that toggle selection state. Use session state to
        # persist the selection across reruns.
        state_key = f"multi_map_selected_{dataset_id}"
        if state_key not in st.session_state:
            st.session_state[state_key] = [current_title] if current_title in titles else [titles[0]] if titles else []

        # Main page title: always show the dataset/indicator subject above the
        # indicator selection UI so it's visible in both single- and
        # multi-map modes.
        st.title(meta.get("subject", ""))

        st.markdown("**Selecteer indicatoren**")
        # Simple checkbox grid: one checkbox per title, arranged in columns.
        chk_cols = st.columns(4)
        for i, title in enumerate(titles):
            col = chk_cols[i % 4]
            chk_key = f"{state_key}_chk_{i}"
            if chk_key not in st.session_state:
                st.session_state[chk_key] = title in st.session_state[state_key]
            _ = col.checkbox(title, value=st.session_state[chk_key], key=chk_key)

        selected_titles = [title for i, title in enumerate(titles) if st.session_state.get(f"{state_key}_chk_{i}")]
        prev_count_key = f"{state_key}_prev_count"
        prev_count = st.session_state.get(prev_count_key, None)
        st.session_state[state_key] = selected_titles
        selected_inds = [title_by_ind[t] for t in selected_titles if t in title_by_ind]

        # If the number of selected maps changed, clear the clicked area so
        # the UI returns to the default "Klik op een gebied..." state.
        if prev_count is None or prev_count != len(selected_inds):
            st.session_state.clicked_area = None
        st.session_state[prev_count_key] = len(selected_inds)

        if len(selected_inds) > 1:
            # Compute shared color range across selected indicators only when
            # all selected indicators share the same legend text in their
            # metadata. If legends differ, keep each map's original scale to
            # avoid distorting values.
            shared_range = None
            # collect variant metas for selected indicators (for this dataset)
            variant_metas_for_selected = [
                next((v for v in INDICATORS_META[ind_name] if v.get("dataset") == dataset_id), INDICATORS_META[ind_name][0])
                for ind_name in selected_inds
            ]
            legends = {vm.get("legend") for vm in variant_metas_for_selected}
            if len(legends) == 1:
                combined = []
                for ind_name in selected_inds:
                    if ind_name in plot_df.columns:
                        combined.append(pd.to_numeric(plot_df[ind_name], errors="coerce"))
                if combined:
                    combined_series = pd.concat(combined, ignore_index=True).dropna()
                    if not combined_series.empty:
                        shared_range = (combined_series.min(), combined_series.max())

            # Render each selected indicator in its own column; hide duplicate colorbars
            cols = st.columns(len(selected_inds))
            for idx, (col, ind_name) in enumerate(zip(cols, selected_inds)):
                with col:
                    # pick the variant meta for this dataset (fallback to first)
                    variant_meta = next((v for v in INDICATORS_META[ind_name] if v.get("dataset") == dataset_id), INDICATORS_META[ind_name][0])
                    # Render compact per-map header (title + optional description/link)
                    st.subheader(variant_meta.get("title", ind_name))
                    desc = variant_meta.get("description", meta.get("description"))
                    if desc:
                        st.markdown(f"<div style='font-size:14px;color:#444'>{desc}</div>", unsafe_allow_html=True)
                    link = variant_meta.get("link", meta.get("link"))
                    if link:
                        st.markdown(
                            f'<a href="{link}" target="_blank">Link naar publicatie &#8599;</a>',
                            unsafe_allow_html=True
                        )

                    fig_i = get_fig_no_graph(
                        plot_df,
                        ind_name,
                        dataset_meta,
                        variant_meta,
                        selected_option=selected_option,
                        range_color_override=shared_range,
                        coloraxis_name=("coloraxis" if shared_range is not None else None),
                        include_colorbar=(shared_range is not None and idx == len(selected_inds) - 1),
                    )
                    # As a final safety fallback, ensure non-last maps do not
                    # show a per-trace colorbar.
                    try:
                        if shared_range is not None and idx < len(selected_inds) - 1:
                            fig_i.update_traces(showscale=False)
                    except Exception:
                        pass

                    st.plotly_chart(fig_i, use_container_width=True)
            # when showing multiple, set fig to None to avoid double render
            fig = None
        else:
            # single map as before
            fig = get_fig_no_graph(
                plot_df,
                indicator,
                dataset_meta,
                meta,
                selected_option=selected_option
            )
            # Use the same compact per-map header style as multi-map view.
            st.subheader(meta.get("title", indicator))
            desc = meta.get("description")
            if desc:
                st.markdown(f"<div style='font-size:14px;color:#444'>{desc}</div>", unsafe_allow_html=True)

            link = meta.get("link")
            if link:
                st.markdown(
                    f'<a href="{link}" target="_blank">Link naar publicatie &#8599;</a>',
                    unsafe_allow_html=True
                )

        # Show value of indicator + attributes upon clicking on area (only for
        # single-map view). When multiple indicators are shown side-by-side we
        # skip the click-to-details behaviour.
        if fig is not None:
            col_map, col_attributes = st.columns([4, 1])

            with col_map:
                # Capture selection events from the Plotly chart. `on_select="rerun"`
                # causes Streamlit to return a Plotly chart event object on rerun
                # which contains `selection.points` for clicked/selected points.
                try:
                    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key=f"map_{dataset_id}")
                except Exception:
                    event = st.plotly_chart(fig, use_container_width=True, key=f"map_{dataset_id}")

                # If selection occurred, extract the area's key from `customdata`.
                try:
                    if event is not None and getattr(event, "selection", None) is not None:
                        pts = event.selection.points
                        if pts:
                            cd = pts[0].get("customdata")
                            if cd:
                                st.session_state.clicked_area = cd[0]
                except Exception:
                    pass

            with col_attributes:
                if st.session_state.clicked_area is None:
                    st.info("Klik op een gebied voor meer informatie.")
                else:
                    attributes = get_attributes_for_area(
                        plot_df,
                        dataset_meta,
                        ATTRIBUTES_META,
                        dataset_id,
                        st.session_state.clicked_area,
                    )

                    selected_row = plot_df[
                        plot_df[dataset_meta["key"]].astype(str)
                        == str(st.session_state.clicked_area)
                    ]

                    area_name_field = dataset_meta.get("area_name_field")
                    if not selected_row.empty:
                        if area_name_field and area_name_field in selected_row.columns:
                            st.subheader(selected_row[area_name_field].iloc[0])
                        else:
                            st.subheader(str(st.session_state.clicked_area))

                    if not selected_row.empty:
                        selected_row = selected_row.iloc[0]

                        indicator_value = selected_row[indicator]

                        if pd.notna(indicator_value):
                            indicator_text = (
                                f"{indicator_value:.{meta['precision']}f}"
                                f" {meta['unit']}"
                            )
                        else:
                            indicator_text = "Niet beschikbaar"

                        st.markdown(
                            f"""
                            <div style=""
                                font-size: 2rem;
                                font-weight: 700;
                                margin-bottom: 0.5rem;
                            ">
                                {indicator_text}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.divider()

                    if attributes:
                        for attr in attributes:
                            value = attr["value"]

                            if pd.isna(value):
                                value_str = "Niet beschikbaar"
                            else:
                                value_str = (
                                    f"{value:.{attr['precision']}f} "
                                    f"{attr['unit']}"
                                )

                            c1, c2 = st.columns([2, 1])

                            with c1:
                                st.caption(attr["title"])

                            with c2:
                                st.markdown(
                                    f"<b>{value_str}</b>",
                                    unsafe_allow_html=True
                                )
        else:
            st.info("Meerdere kaarten worden getoond; klik-voor-details is uitgeschakeld.")

    

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
            st.plotly_chart(fig, width="stretch")
    logger.info("After showing indicator")


else:
    st.info("Selecteer een indicator.")

logger.info("App script finished")

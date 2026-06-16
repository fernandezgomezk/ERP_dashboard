import plotly.graph_objects as go
import streamlit as st
import itertools


def get_boxplot(plot_df, indicator, datasets_meta, indicators_meta, selected_filters):

    meta = indicators_meta[indicator]
    dataset_meta = datasets_meta

    stat_col = dataset_meta["key"]         
    mapping = dataset_meta["mapping"]
    value_col = indicator                  

    unit = meta["unit"]
    precision = meta["precision"]
    unit = meta["unit"]


    categories = dataset_meta.get("categories", [])



    # Check columns exist
    for col in categories:
        if col not in plot_df.columns:
            st.error(f"Kolom '{col}' niet gevonden. Beschikbaar: {plot_df.columns.tolist()}")
            return

    if value_col not in plot_df.columns:
        st.error(f"Kolom '{value_col}' niet gevonden. Beschikbaar: {plot_df.columns.tolist()}")
        return

    
    # Generate combinations
    combinations = list(itertools.product(*selected_filters.values()))

    if len(combinations) == 0:
        st.warning("Geen selectie gemaakt.")
        return

    if len(combinations) > 12:
        st.warning("Te veel combinaties geselecteerd — beperk filters.")
        return

    fig = go.Figure()

    # LOOP OVER COMBINATIONS
    for combo in combinations:

        subset = plot_df.copy()
        label_parts = []

        for col, val in zip(categories, combo):
            subset = subset[subset[col] == val]
            label_parts.append(str(val))

        label = " - ".join(label_parts)

        values = {}

        for key, stat_name in mapping.items():
            match = subset[subset[stat_col] == stat_name]

            if match.empty:
                st.warning(f"Statistiek '{stat_name}' ontbreekt voor {label}")
                values[key] = None
            else:
                values[key] = float(match[value_col].iloc[0])        
        
        fig.add_trace(go.Box(
            x=[label],   
            name=label,
            median=[values.get("median")],
            q1=[values.get("q1")],
            q3=[values.get("q3")],
            lowerfence=[values.get("min")],
            upperfence=[values.get("max")],
            boxpoints=False,
            marker_color= st.get_option("theme.primaryColor")
            
        ))


    # --- Layout ---
    fig.update_layout(
        height=600,
        yaxis_title=unit,
        showlegend=False
    )

    return fig
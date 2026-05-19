import plotly.graph_objects as go
import streamlit as st


def get_boxplot(plot_df, indicator, datasets_meta, indicators_meta):

    meta = indicators_meta[indicator]
    dataset_meta = datasets_meta

    stat_col = dataset_meta["key"]         
    mapping = dataset_meta["mapping"]
    value_col = indicator                  

    unit = meta["unit"]
    precision = meta["precision"]

    # --- Extract statistics ---
    try:
        values = {}

        for key, stat_name in mapping.items():
            match = plot_df[plot_df[stat_col] == stat_name]

            if match.empty:
                raise KeyError(stat_name)

            values[key] = float(match[value_col].iloc[0])

    except KeyError as e:
        st.error(f"Ontbrekende statistiek: {e}")
        return

    # --- Label (based on filters) ---
    label_parts = []
    for col in dataset_meta.get("categories", []):
        if col in plot_df.columns:
            val = plot_df[col].iloc[0]
            label_parts.append(f"{col}: {val}")

    label = " | ".join(label_parts)


    for col in dataset_meta["categories"]:
        if col not in plot_df.columns:
            st.error(f"Kolom '{col}' niet gevonden. Beschikbaar: {plot_df.columns.tolist()}")
            st.stop()

    # --- Plot ---
    fig = go.Figure()

    fig.add_trace(go.Box(
        name=label,
        median=[values["median"]],
        q1=[values["q1"]],
        q3=[values["q3"]],
        lowerfence=[values.get("min")],
        upperfence=[values.get("max")],
        boxpoints=False
    ))

    # --- Layout (map-style consistency) ---
    fig.update_layout(
        height=600,
        title_text=meta["title"],
        title_x=0,
        title_font=dict(size=24),
        yaxis_title=meta["unit"]
    )

    # --- Link ---
    fig.add_annotation(
        text=f'<a href="{meta["link"]}" target="_blank">Link naar publicatie &#8599;</a>',
        x=0,
        y=1.1,
        xref="paper",
        yref="paper",
        showarrow=False,
        align="left",
        font=dict(size=14)
    )

    st.plotly_chart(fig, width='stretch')

import pandas as pd
import plotly.express as px

from streamlit.logger import get_logger

logger = get_logger("app.log")

def get_fig_no_graph(
    plot_gdf,
    indicator,
    datasets_meta,
    indicators_meta,
    selected_option=None
):
    logger.info(f"Generating figure for indicator: {indicator}")

    # Get option columns (always a list)
    dataset_id = indicators_meta[indicator]["dataset"]
    option_columns = datasets_meta[dataset_id].get("options", [])

    # Apply filtering if options exist
    if option_columns and selected_option is not None:
        logger.info(f"Filtering on option columns: {option_columns}")

        # Multi-column case: expect dict
        if isinstance(selected_option, dict):
            for col in option_columns:
                if col in plot_gdf.columns and col in selected_option:
                    plot_gdf = plot_gdf[plot_gdf[col] == selected_option[col]]

        # Single-column case
        elif len(option_columns) == 1:
            col = option_columns[0]
            if col in plot_gdf.columns:
                plot_gdf = plot_gdf[plot_gdf[col] == selected_option]

    precision = indicators_meta[indicator]["precision"]
    unit = indicators_meta[indicator]["unit"]

    plot_gdf["_color_value"] = plot_gdf[indicator].astype(float).fillna(-999) # Waarde van -999 om juiste kleur te krijgen (namelijk spierwit)
    plot_gdf["_hover_label"] = plot_gdf[indicator].apply(
        lambda x: f"{x:.{precision}f}{unit}" if pd.notna(x) else "data niet beschikbaar"
    ) # Als NaN: expliciet aangeven dat data niet beschikbaar is

    fig = px.choropleth_map(
        plot_gdf,
        geojson=plot_gdf.geometry.__geo_interface__,
        locations=plot_gdf.index,
        color="_color_value",
        color_continuous_scale=[[0.0, "#f0f3fa"],[1.0, "#123eb7"]],
        labels={"_color_value": indicators_meta[indicator]["legend"]},
        custom_data=["gemeentenaam", "_hover_label"],
        range_color=(plot_gdf.loc[plot_gdf[indicator].notna(), indicator].min(), plot_gdf.loc[plot_gdf[indicator].notna(), indicator].max()),
        center={"lat": 52.15, "lon": 5.15}, #Zodat de kaart in Nederland begint en niet in de Atlantische Oceaan
        zoom=6.5, #Zodat je meteen overzicht hebt
        map_style="white-bg"
    )
    logger.info(f"After generating chloropleth")

    fig.update_layout(
        height=800, #Zodat de kaart niet superklein is
    )
    logger.info(f"After updating layout")

    fig.update_traces(
        hovertemplate=(
            "%{customdata[0]}: %{customdata[1]}"
            "<extra></extra>"
        )
    )
    logger.info(f"After updating traces")

    return fig

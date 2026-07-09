import pandas as pd
import plotly.express as px

from streamlit.logger import get_logger

logger = get_logger("app.log")


def _build_choropleth(plot_gdf, color_column, legend, precision, unit, range_color_override=None):
    plot_gdf["_color_value"] = plot_gdf[color_column].astype(float).fillna(-999)
    plot_gdf["_hover_label"] = plot_gdf[color_column].apply(
        lambda x: f"{x:.{precision}f}{unit}" if pd.notna(x) else "data niet beschikbaar"
    )

    if range_color_override is not None:
        range_color = range_color_override
    else:
        range_series = pd.to_numeric(plot_gdf[color_column], errors="coerce").dropna()
        range_color = None
        if not range_series.empty:
            range_color = (range_series.min(), range_series.max())

    fig = px.choropleth_map(
        plot_gdf,
        geojson=plot_gdf.geometry.__geo_interface__,
        locations=plot_gdf.index,
        color="_color_value",
        color_continuous_scale=[[0.0, "#f0f3fa"], [1.0, "#123eb7"]],
        labels={"_color_value": legend},
        # custom_data=["gemeentenaam", "_hover_label"],
        custom_data=["statcode", "_hover_label"],
        range_color=range_color,
        center={"lat": 52.15, "lon": 5.15},
        zoom=6.5,
        map_style="white-bg"
    )

    fig.update_layout(height=800)
    fig.update_traces(
        hovertemplate=(
            "%{customdata[0]}: %{customdata[1]}"
            "<extra></extra>"
        )
    )
    return fig

def get_fig_no_graph(plot_gdf, indicator, datasets_meta, indicators_meta):
    logger.info(f"Generating figure for indicator: {indicator}")

    precision = indicators_meta[indicator]["precision"]
    unit = indicators_meta[indicator]["unit"]

    fig = _build_choropleth(
        plot_gdf,
        color_column=indicator,
        legend=indicators_meta[indicator]["legend"],
        precision=precision,
        unit=unit,
    )
    logger.info("After generating chloropleth")

    return fig


def get_side_by_side_maps(plot_gdf, indicator, indicators_meta):
    indicator_meta = indicators_meta[indicator]
    map_columns = indicator_meta.get("map_columns")
    shared_color_scale = indicator_meta.get("shared_color_scale", True)

    if not isinstance(map_columns, list) or len(map_columns) != 2:
        raise ValueError("side_by_side_maps vereist precies 2 items in 'map_columns'.")

    map_specs = []

    for map_column_cfg in map_columns:
        if isinstance(map_column_cfg, str):
            column_name = map_column_cfg
            map_title = map_column_cfg
            legend = indicator_meta["legend"]
            precision = indicator_meta["precision"]
            unit = indicator_meta["unit"]
        elif isinstance(map_column_cfg, dict):
            column_name = map_column_cfg.get("column")
            map_title = map_column_cfg.get("title", column_name)
            legend = map_column_cfg.get("legend", indicator_meta["legend"])
            precision = map_column_cfg.get("precision", indicator_meta["precision"])
            unit = map_column_cfg.get("unit", indicator_meta["unit"])
        else:
            raise ValueError("Elk item in 'map_columns' moet een string of dict zijn.")

        if column_name not in plot_gdf.columns:
            raise KeyError(f"Kolom '{column_name}' niet gevonden in dataframe.")

        map_specs.append(
            {
                "column_name": column_name,
                "map_title": map_title,
                "legend": legend,
                "precision": precision,
                "unit": unit,
            }
        )

    shared_range_color = None
    if shared_color_scale:
        combined_series = pd.concat(
            [pd.to_numeric(plot_gdf[spec["column_name"]], errors="coerce") for spec in map_specs],
            ignore_index=True,
        ).dropna()

        if not combined_series.empty:
            shared_range_color = (combined_series.min(), combined_series.max())

    figures = []

    for spec in map_specs:

        fig = _build_choropleth(
            plot_gdf,
            color_column=spec["column_name"],
            legend=spec["legend"],
            precision=spec["precision"],
            unit=spec["unit"],
            range_color_override=shared_range_color,
        )
        figures.append((spec["map_title"], fig))

    return figures

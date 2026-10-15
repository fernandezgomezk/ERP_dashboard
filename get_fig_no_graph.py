import pandas as pd
import plotly.express as px
import math

from streamlit.logger import get_logger

logger = get_logger("app.log")


def build_indicator_display_series(values, precision, unit, show_values=True):
    numeric_values = pd.to_numeric(values, errors="coerce")

    if show_values:
        return numeric_values.apply(
            lambda value: f"{value:.{precision}f}{unit}" if pd.notna(value) else "Niet beschikbaar"
        )

    valid_values = numeric_values.dropna()
    if valid_values.empty:
        return pd.Series(["Niet beschikbaar"] * len(numeric_values), index=numeric_values.index)

    if valid_values.nunique() == 1:
        return pd.Series(
            ["0" if pd.notna(value) else "Niet beschikbaar" for value in numeric_values],
            index=numeric_values.index,
        )

    symbol_bins = pd.cut(
        valid_values,
        bins=4,
        labels=["-", "0", "+", "++"],
        include_lowest=True,
    )

    display_values = pd.Series("Niet beschikbaar", index=numeric_values.index, dtype="object")
    display_values.loc[symbol_bins.index] = symbol_bins.astype(str)
    display_values.loc[numeric_values.isna()] = "Niet beschikbaar"

    return display_values


def _build_symbolic_colorbar(range_color, legend):
    cmin, cmax = range_color
    if cmin == cmax:
        return {
            "title": {"text": legend},
            "tickmode": "array",
            "tickvals": [cmin],
            "ticktext": ["0"],
        }

    span = cmax - cmin
    return {
        "title": {"text": legend},
        "tickmode": "array",
        "tickvals": [cmin, cmin + span / 3, cmin + (2 * span / 3), cmax],
        "ticktext": ["-", "0", "+", "++"],
    }


def _calculate_map_center_and_zoom(gdf):
    """Calculate map center and zoom level based on GeoDataFrame bounds."""
    try:
        bounds = gdf.total_bounds  # (minx, miny, maxx, maxy)
        if len(bounds) == 0 or bounds is None:
            # Fallback to Netherlands center
            return {"lat": 52.15, "lon": 5.15}, 6.5
        
        minx, miny, maxx, maxy = bounds
        center_lat = (miny + maxy) / 2
        center_lon = (minx + maxx) / 2
        
        # Calculate zoom level based on bounds (in degrees WGS84)
        width = maxx - minx
        height = maxy - miny
        max_span = max(width, height)
        
        # Granular mapping for Dutch regions (in degrees)
        # Full Netherlands ~2.8°, Province ~0.8-1.5°, Municipality ~0.1-0.3°
        if max_span > 3:      # Very large (full country or larger)
            zoom = 6.5
        elif max_span > 2:    # Large (multiple provinces)
            zoom = 7
        elif max_span > 1.2:  # Large province
            zoom = 8
        elif max_span > 0.8:  # Medium province
            zoom = 8.5
        elif max_span > 0.4:  # Small province / large municipality
            zoom = 9
        elif max_span > 0.2:  # Municipality
            zoom = 10
        elif max_span > 0.1:  # Small municipality
            zoom = 10.5
        else:                 # Very small (neighborhood)
            zoom = 11
        
        return {"lat": center_lat, "lon": center_lon}, zoom
    except Exception as e:
        logger.warning(f"Could not calculate map bounds: {e}")
        # Fallback to Netherlands center
        return {"lat": 52.15, "lon": 5.15}, 6.5


def _build_choropleth(plot_gdf, color_column, legend, precision, unit, key, area_name_field=None, range_color_override=None, coloraxis_name=None, include_colorbar=False, center=None, zoom=None, show_values=True):
    plot_gdf["_color_value"] = plot_gdf[color_column].astype(float).fillna(-999)
    plot_gdf["_hover_display"] = build_indicator_display_series(
        plot_gdf[color_column],
        precision,
        unit,
        show_values=show_values,
    )

    if range_color_override is not None:
        range_color = range_color_override
    else:
        range_series = pd.to_numeric(plot_gdf[color_column], errors="coerce").dropna()
        range_color = None
        if not range_series.empty:
            range_color = (range_series.min(), range_series.max())

    # Build custom_data dynamically: always include key;
    # include area_name_field only when provided and present on the dataframe.
    custom_data = [key]
    include_area_name = False
    if area_name_field and area_name_field in plot_gdf.columns:
        custom_data.append(area_name_field)
        include_area_name = True
    custom_data.append("_hover_display")

    # Use provided center/zoom or calculate from bounds, with fallback to Netherlands
    if center is None or zoom is None:
        center, zoom = _calculate_map_center_and_zoom(plot_gdf)
    
    fig = px.choropleth_map(
        plot_gdf,
        geojson=plot_gdf.geometry.__geo_interface__,
        locations=plot_gdf.index,
        color="_color_value",
        color_continuous_scale=[[0.0, "#f0f3fa"], [1.0, "#123eb7"]],
        labels={"_color_value": legend},
        custom_data=custom_data,
        range_color=range_color,
        center=center,
        zoom=zoom,
        map_style = "white-bg"
    )

    fig.update_layout(height=750)
    # Choose hovertemplate indices depending on whether area name was added
    if include_area_name:
        hovertemplate = "<b>%{customdata[1]}</b><br>%{customdata[2]}<extra></extra>"
    else:
        hovertemplate = "<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>"
    fig.update_traces(hovertemplate=hovertemplate)

    if range_color is not None and not show_values:
        symbolic_colorbar = _build_symbolic_colorbar(range_color, legend)
        layout_coloraxis = {"cmin": range_color[0], "cmax": range_color[1]}

        if coloraxis_name is None or include_colorbar:
            layout_coloraxis["colorbar"] = symbolic_colorbar

        coloraxis_target = coloraxis_name or "coloraxis"
        try:
            fig.update_layout(**{coloraxis_target: layout_coloraxis})
        except Exception:
            pass

        if coloraxis_name is not None:
            try:
                for tr in fig.data:
                    tr.update(coloraxis=coloraxis_name)
                    if getattr(tr, "colorbar", None) is not None:
                        tr.colorbar = None
            except Exception:
                pass

    return fig

def get_fig_no_graph(plot_gdf, indicator, dataset_meta, indicator_meta, selected_option=None, range_color_override=None, coloraxis_name=None, include_colorbar=False, show_values=True):
    logger.info(f"Generating figure for indicator: {indicator}")

    key = dataset_meta["key"]
    option_columns = dataset_meta.get("options", [])

    plot_gdf = plot_gdf.copy()

    # Apply filtering if options exist
    if option_columns and selected_option is not None:
        logger.info(f"Filtering on option columns: {option_columns}")

        # Multi-column case
        if isinstance(selected_option, dict):
            for col in option_columns:
                if col in plot_gdf.columns and col in selected_option:
                    plot_gdf = plot_gdf[plot_gdf[col] == selected_option[col]]

        # Single-column case
        elif len(option_columns) == 1:
            col = option_columns[0]
            if col in plot_gdf.columns:
                plot_gdf = plot_gdf[plot_gdf[col] == selected_option]

    precision = indicator_meta["precision"]
    unit = indicator_meta["unit"]

    # Calculate map center and zoom based on filtered data bounds
    center, zoom = _calculate_map_center_and_zoom(plot_gdf)

    fig = _build_choropleth(
        plot_gdf,
        color_column=indicator,
        legend=indicator_meta["legend"],
        precision=precision,
        unit=unit,
        key=key,
        area_name_field=dataset_meta.get("area_name_field"),
        range_color_override=range_color_override,
        coloraxis_name=coloraxis_name,
        include_colorbar=include_colorbar,
        center=center,
        zoom=zoom,
        show_values=show_values,
    )
    logger.info("After generating choropleth")

    return fig


def get_side_by_side_maps(plot_gdf, indicator_meta, dataset_meta, selected_columns):
    key = dataset_meta["key"]
    map_columns = indicator_meta.get("map_columns")
    shared_color_scale = indicator_meta.get("shared_color_scale", True)
    if not isinstance(map_columns, list) or len(map_columns) < 2:
        raise ValueError("side_by_side_maps vereist minstens 2 items in 'map_columns'.")

    # build lookup dictionary for map configuration based on column names
    map_config_by_column = {}
    for map_column_cfg in map_columns:
        if isinstance(map_column_cfg, str):
            column_name = map_column_cfg
            map_config_by_column[column_name] = {
                "column_name": column_name,
                "map_title": column_name,
                "legend": indicator_meta["legend"],
                "precision": indicator_meta["precision"],
                "unit": indicator_meta["unit"],
            }
        elif isinstance(map_column_cfg, dict):
            column_name = map_column_cfg.get("column")
            if column_name is None:
                raise ValueError("Items in 'map_columns' als dict moeten een 'column' bevatten.")
            map_config_by_column[column_name] = {
                "column_name": column_name,
                "map_title": map_column_cfg.get("title", column_name),
                "legend": map_column_cfg.get("legend", indicator_meta["legend"]),
                "precision": map_column_cfg.get("precision", indicator_meta["precision"]),
                "unit": map_column_cfg.get("unit", indicator_meta["unit"]),
            }
        else:
            raise ValueError("Elk item in 'map_columns' moet een string of dict zijn.")

    # build list of map specifications based on selected columns
    map_specs = []
    for selected_column in selected_columns:
        if selected_column not in map_config_by_column:
            continue
        if selected_column not in plot_gdf.columns:
            raise KeyError(f"Kolom '{selected_column}' niet gevonden in dataframe.")
        map_specs.append(map_config_by_column[selected_column])
    if len(map_specs) < 1:
        raise ValueError("side_by_side_maps vereist minstens 1 item in 'map_columns' die in 'selected_columns' voorkomen.")

    # determine color range for shared color scale if applicable
    shared_range_color = None
    if shared_color_scale:
        combined_series = pd.concat(
            [pd.to_numeric(plot_gdf[spec["column_name"]], errors="coerce") for spec in map_specs],
            ignore_index=True,
        ).dropna()
        if not combined_series.empty:
            shared_range_color = (combined_series.min(), combined_series.max())

    # Calculate map center and zoom based on data bounds (same for all maps)
    center, zoom = _calculate_map_center_and_zoom(plot_gdf)

    figures = []
    for idx, spec in enumerate(map_specs):
        fig = _build_choropleth(
            plot_gdf,
            color_column=spec["column_name"],
            legend=spec["legend"],
            precision=spec["precision"],
            unit=spec["unit"],
            key=key,
            range_color_override=shared_range_color,
            area_name_field=dataset_meta.get("area_name_field"),
            coloraxis_name=("coloraxis" if shared_range_color is not None else None),
            include_colorbar=(shared_range_color is not None and idx == len(map_specs) - 1),
            center=center,
            zoom=zoom,
            show_values=indicator_meta.get("show_values", True),
        )


        figures.append((spec["map_title"], fig))

    return figures

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Any


def _get_indicator_variant(
    indicators_meta: dict[str, list[dict[str, Any]]], indicator_name: str, dataset_id: str | None
) -> dict[str, Any] | None:
    """Resolve the best metadata variant for one indicator.

    Args:
        indicators_meta: Mapping of indicator names to one or more metadata variants.
        indicator_name: Indicator key to resolve from the metadata mapping.
        dataset_id: Preferred dataset id used to pick the matching variant.
    Returns:
        The variant for the requested dataset when available, otherwise the first
        variant for the indicator, or None when the indicator is unknown.
    """
    variants = indicators_meta.get(indicator_name, [])
    if not variants:
        return None

    for variant in variants:
        if variant.get("dataset") == dataset_id:
            return variant

    return variants[0]


def _build_axis_label(
    indicators_meta: dict[str, list[dict[str, Any]]], indicator_name: str, dataset_id: str | None
) -> str:
    """Build a human-readable axis label from indicator metadata.

    Args:
        indicators_meta: Mapping of indicator names to metadata variants.
        indicator_name: Indicator key used for label lookup.
        dataset_id: Preferred dataset id to choose the best metadata variant.
    Returns:
        A label in the form title (unit) when available, with fallbacks to title,
        indicator name plus unit, or indicator name.
    """
    meta = _get_indicator_variant(indicators_meta, indicator_name, dataset_id)
    if not meta:
        return indicator_name

    title = (meta.get("title") or "").strip()
    unit = (meta.get("unit") or "").strip()

    if title and unit:
        return f"{title} ({unit})"
    if title:
        return title
    if unit:
        return f"{indicator_name} ({unit})"

    return indicator_name


def get_scatterplot(
    plot_df: pd.DataFrame,
    indicator: str,
    dataset_meta: dict[str, Any],
    indicator_meta: dict[str, Any],
    selected_indicators: list[str],
    indicators_meta: dict[str, list[dict[str, Any]]],
    show_regression_line: bool = True,
) -> go.Figure:
    """Create a scatterplot for a pair of indicators.

    Args:
        plot_df: Source data containing the indicator columns and optional id column.
        indicator: Scatter indicator key from the UI flow (kept for API consistency).
        dataset_meta: Dataset settings; key may define an id column for hover info.
        indicator_meta: Metadata for the selected scatter definition, including title.
        selected_indicators: Exactly two indicator column names, in x and y order.
        indicators_meta: Full indicator metadata used to derive axis labels.
        show_regression_line: Whether a linear regression line should be drawn.
    Returns:
        A Plotly Figure with a scatterplot, or a message-only figure when required
        columns or valid numeric data are unavailable.
    """
    del indicator  # kept in signature for consistency with other plotting helpers

    if len(selected_indicators) != 2:
        fig = go.Figure()
        fig.add_annotation(
            text="Scatterplot vereist precies 2 indicatoren.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        return fig

    x_col, y_col = selected_indicators
    required_columns = [x_col, y_col]
    id_col = dataset_meta.get("key")
    if id_col and id_col in plot_df.columns:
        required_columns.append(id_col)

    missing_columns = [col for col in [x_col, y_col] if col not in plot_df.columns]
    if missing_columns:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Kolommen niet gevonden: {', '.join(missing_columns)}",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        return fig

    scatter_df = plot_df[required_columns].copy()
    scatter_df[x_col] = pd.to_numeric(scatter_df[x_col], errors="coerce")
    scatter_df[y_col] = pd.to_numeric(scatter_df[y_col], errors="coerce")
    scatter_df = scatter_df.dropna(subset=[x_col, y_col])

    if scatter_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Geen geldige data beschikbaar voor scatterplot.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        return fig

    dataset_id = indicator_meta.get("dataset")
    x_label = _build_axis_label(indicators_meta, x_col, dataset_id)
    y_label = _build_axis_label(indicators_meta, y_col, dataset_id)

    labels = {
        x_col: x_label,
        y_col: y_label,
    }

    hover_data = {}
    if id_col and id_col in scatter_df.columns:
        hover_data[id_col] = True

    fig = px.scatter(
        scatter_df,
        x=x_col,
        y=y_col,
        labels=labels,
        hover_data=hover_data,
        opacity=0.75,
    )

    x_values = scatter_df[x_col].to_numpy()
    y_values = scatter_df[y_col].to_numpy()

    if show_regression_line and len(scatter_df) >= 2 and np.unique(x_values).size > 1:
        slope, intercept = np.polyfit(x_values, y_values, 1)
        x_line = np.linspace(x_values.min(), x_values.max(), 100)
        y_line = slope * x_line + intercept

        ss_res = np.sum((y_values - (slope * x_values + intercept)) ** 2)
        ss_tot = np.sum((y_values - y_values.mean()) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else 1.0

        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=y_line,
                mode="lines",
                name=f"Regressielijn (R²={r_squared:.2f})",
                line={"color": "#d34d2f", "width": 2},
                hovertemplate="Regressielijn<extra></extra>",
            )
        )

    fig.update_traces(marker={"size": 8, "color": "#123eb7"})
    fig.update_layout(
        title=indicator_meta.get("title", "Scatterplot"),
        height=700,
        legend_title_text="",
    )

    return fig

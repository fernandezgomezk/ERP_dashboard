import pandas as pd
import plotly.express as px
import textwrap


def get_fig_with_graph(plot_gdf, indicator, datasets_meta, indicators_meta, clicked_gemeente):

    precision = indicators_meta[indicator]["precision"]
    unit = indicators_meta[indicator]["unit"]

    plot_gdf["_color_value"] = plot_gdf[indicator].astype(float).fillna(-999) # Waarde van -999 om juiste kleur te krijgen (namelijk spierwit)
    plot_gdf["_hover_label"] = plot_gdf[indicator].apply(
        lambda x: f"{x:.{precision}f}{unit}" if pd.notna(x) else "data niet beschikbaar"
    ) # Als NaN: expliciet aangeven dat data niet beschikbaar is

    fig = px.choropleth_map(
        plot_gdf,
        geojson = plot_gdf.geometry.__geo_interface__,
        locations = plot_gdf.index,
        color="_color_value",
        color_continuous_scale=[[0.0, "#f0f3fa"],[1.0, "#123eb7"]],
        labels={"_color_value": indicators_meta[indicator]["legend"]},
        custom_data=["gemeentenaam", "_hover_label"],
        range_color=(plot_gdf.loc[plot_gdf[indicator].notna(), indicator].min(), plot_gdf.loc[plot_gdf[indicator].notna(), indicator].max()),
        center={"lat": 52.15, "lon": 5.15}, #Zodat de kaart in Nederland begint en niet in de Atlantische Oceaan
        zoom=6.5, #Zodat je meteen overzicht hebt
        map_style="white-bg"
    )

    fig.update_layout(height=800)

    fig.update_traces(
        hovertemplate=(
            "%{customdata[0]}: %{customdata[1]}"
            "<extra></extra>"
        )
    )

    # --- Trend ---
    fig_trend = None

    if clicked_gemeente is not None:
        df_trend = plot_gdf.loc[
            plot_gdf.gemeentenaam == clicked_gemeente,
            ["JAAR", indicator]
        ].sort_values("JAAR")

        if not df_trend.empty:            

            title = indicators_meta[indicator]['title']

            wrapped_title = "<br>".join(textwrap.wrap(title, width=40))

            title_text = (
                f"<span style='font-weight:normal;'>{wrapped_title} in </span>"
                f"<b>{clicked_gemeente}</b>"
            )

            fig_trend = px.line(
                df_trend,
                x="JAAR",
                y=indicator,
                title=title_text,
                markers=True,
                labels={indicator: indicators_meta[indicator]["legend"]}
            )

            fig_trend.update_layout(
                margin=dict(t=110)
            )


    return fig, fig_trend
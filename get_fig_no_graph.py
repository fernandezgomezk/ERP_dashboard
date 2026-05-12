import pandas as pd
import plotly.express as px
import streamlit as st


def get_fig_no_graph(plot_gdf, indicator, datasets_meta, indicators_meta):

    # Testwaarden controleren
    dataset_id = indicators_meta[indicator]["dataset"]
    dataset_meta = datasets_meta[dataset_id]
    for gemeente, expected in indicators_meta[indicator]["test_values"].items():
        actual = round(plot_gdf.loc[plot_gdf[dataset_meta["key"]] == gemeente, indicator].iloc[0], 2) # Kijk of match
        if actual != expected: # Discrete waarschuwing als testwaardes niet matchen
            unit = indicators_meta[indicator]["unit"] # Inclusief unit uiteraard
            st.warning(f"Let op: de testwaarden in de metadata komen niet overeen met de waarden in de kaart ({gemeente}: verwacht {expected}{unit}, gevonden {actual}{unit})")

    #plot_gdf = plot_gdf.dropna(subset=[indicator]) #Alleen plotten wat mensen willen plotten (aangegeven in de selectbox onder)
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

    fig.update_layout(
        height=800, #Zodat de kaart niet superklein is
        title_text=indicators_meta[indicator]["title"],
        title_x=0,
        title_font=dict(size=24)
    )

    #Linkje naar publicatie
    link = indicators_meta[indicator]["link"]
    fig.add_annotation(
        text=f'<a href="{link}" target="_blank">Link naar publicatie &#8599;</a>',
        x=0,
        y=1.03,
        xref="paper",
        yref="paper",
        showarrow=False,
        align="left",
        font=dict(size=14, color="#000000"),
    )

    fig.update_traces(
        hovertemplate=(
            "%{customdata[0]}: %{customdata[1]}"
            "<extra></extra>"
        )
    )

    st.plotly_chart(fig, width='stretch')

from pathlib import Path
import pandas as pd
import geopandas as gpd

from collections import defaultdict

import plotly.express as px
import streamlit as st

from load_indicators import load_indicators #The load_datasets is in a separate function to clean up the code

##########################################
#######Het definieren van de functies####
#########################################


# Functie om metadata in te lezen en bijbehorende gpkg zoeken

# DATASETS is een lijst met bestanden, de bijbehorende gpkg versie en andere metadata
# INDICATORS is een lijst met alle indicatoren hun kenmerken

DATASETS, INDICATORS = load_indicators()
themes = {cfg["theme"] for cfg in INDICATORS.values()}

# Functie om databestanden in te laden, de bijbehorende gpkg in te laden en beiden te mergen 

@st.cache_data(show_spinner=False)
def load_dataset(dataset_id):
    cfg = DATASETS[dataset_id]

    # CSV
    df = pd.read_csv(cfg["csv_path"])
    df = df.drop(columns=["geometry"], errors="ignore") # Verwijder eventuele bestaande kolom "geometry"

    # GPKG
    gdf = gpd.read_file(cfg["gpkg_path"], layer=cfg["layer"])

    gdf = (
        gdf.dissolve(by=cfg["key"], as_index=False)
    )
    gdf = gdf.to_crs(epsg=4326)
    gdf = gdf.filter(['gemeentenaam','geometry'])
    
    # Merge één keer
    plot_gdf = gdf.merge(
        df,
        on=cfg["key"],
        how="left"
    )
    

    return plot_gdf

 
def get_fig(plot_gdf, indicator): #Deze functie maakt de daadwerkelijke kaart

    # Testwaarden controleren
    dataset_id = INDICATORS[indicator]["dataset"]
    cfg = DATASETS[dataset_id]
    for gemeente, expected in INDICATORS[indicator]["test_values"].items():
        actual = round(plot_gdf.loc[plot_gdf[cfg["key"]] == gemeente, indicator].iloc[0], 2) # Kijk of match
        if actual != expected: # Discrete waarschuwing als testwaardes niet matchen
            unit = INDICATORS[indicator]["unit"] # Inclusief unit uiteraard
            st.warning(f"Let op: de testwaarden in de metadata komen niet overeen met de waarden in de kaart ({gemeente}: verwacht {expected}{unit}, gevonden {actual}{unit})")

    #plot_gdf = plot_gdf.dropna(subset=[indicator]) #Alleen plotten wat mensen willen plotten (aangegeven in de selectbox onder)
    precision = INDICATORS[indicator]["precision"]
    unit = INDICATORS[indicator]["unit"]

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
        labels={"_color_value": INDICATORS[indicator]["legend"]},
        custom_data=["gemeentenaam", "_hover_label"],
        range_color=(plot_gdf.loc[plot_gdf[indicator].notna(), indicator].min(), plot_gdf.loc[plot_gdf[indicator].notna(), indicator].max()),
        center={"lat": 52.15, "lon": 5.15}, #Zodat de kaart in Nederland begint en niet in de Atlantische Oceaan
        zoom=6.5, #Zodat je meteen overzicht hebt
        map_style="white-bg"
    )

    fig.update_layout(
        height=800, #Zodat de kaart niet superklein is
        title_text=INDICATORS[indicator]["title"], #titel/beschrijving figuur
        title_x=0, # align title to the left
        title_font=dict(size=24)
     ) 
    
    #Linkje naar publicatie
    link = INDICATORS[indicator]["link"]
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


    return fig

##########################################
############The actual app###############
#########################################

st.set_page_config(layout="wide") #Kaart even breed als scherm
# st.markdown("<style>.stApp { background-color: white; }</style>", unsafe_allow_html=True) #App krijgt witte achtergrond voor TNO

#gdf = get_gemeentegrenzen() #De gemeentegrenzen inladen

#output = get_output() #De csv met data inladen

# with st.sidebar:
#     st.subheader("Onderwerp")

#     selected_theme = st.selectbox(
#         "Kies een onderwerp",  
#         options=themes
#         )

# indicators_in_theme = [
#     indicator
#     for indicator, cfg in INDICATORS.items()
#     if cfg["theme"] == selected_theme
# ]
   
# theme -> subject -> list of indicators
indicators_by_theme_subject = defaultdict(lambda: defaultdict(list))

for indicator, cfg in INDICATORS.items():
    theme = cfg["theme"]
    subject = cfg.get("subject", "Overig")
    indicators_by_theme_subject[theme][subject].append(indicator)

if "indicator" not in st.session_state:
    st.session_state.indicator = None

if "clicked_gemeente" not in st.session_state: # Klik op gemeentes om grafiek te laten zien
    st.session_state.clicked_gemeente = None

with st.sidebar:
    st.subheader("Onderwerpen")

    for theme, subjects in sorted(indicators_by_theme_subject.items()):
        with st.expander(theme, expanded=False):

            for subject, indicators in sorted(subjects.items()):
                # Subject header (niet uitklapbaar)
                st.markdown(f"**{subject}**")

                for indicator in indicators:
                    if indicator == st.session_state.indicator:
                        st.button(
                            INDICATORS[indicator]["title"],
                            key=f"indicator_btn_{indicator}",
                            width='stretch',
                            disabled=True
                        )
                    else:
                        if st.button(
                            INDICATORS[indicator]["title"],
                            key=f"indicator_btn_{indicator}",
                            width='stretch'
                        ):
                            st.session_state.indicator = indicator

indicator = st.session_state.indicator

if indicator is not None:
    dataset_id = INDICATORS[indicator]["dataset"]

    plot_gdf = load_dataset(dataset_id)
    fig = get_fig(plot_gdf, indicator)

    #Het toevoegen van de grafiek als gebruiker op een gemeente klikt
    col_map, col_trend = st.columns([2, 1])    # Claude comment: Verdeel het scherm in twee kolommen: kaart (breed) en trendgrafiek (smal)

    with col_map: # Claude comment: on_select="rerun" zorgt dat Streamlit herlaadt zodra de gebruiker op de kaart klikt
        event = st.plotly_chart(fig, width='stretch', on_select="rerun")

    if event.selection.points: # Als de gebruiker op een gemeente heeft geklikt, sla de naam op in session_state
        st.session_state.clicked_gemeente = event.selection.points[0]["customdata"][0]

    with col_trend:
        if st.session_state.clicked_gemeente is not None:
            gemeente = st.session_state.clicked_gemeente

            df_trend = plot_gdf.loc[plot_gdf.gemeentenaam == gemeente, ["JAAR", indicator]] #  Claude comment: Filter de data op de aangeklikte gemeente en sorteer op jaar
            df_trend = df_trend.sort_values("JAAR")

            # Claude comment: Trendgrafiek — zodra er meerdere jaren in de data zitten verschijnen die hier automatisch
            fig_trend = px.line(
                df_trend,
                x="JAAR",
                y=indicator,
                title=f"{INDICATORS[indicator]['title']} — {gemeente}",
                markers=True,
                labels={indicator: INDICATORS[indicator]["legend"]}
            )
            st.plotly_chart(fig_trend, width='stretch')
        else:
            st.info("Klik op een gemeente om de trend te zien.")
else:
    st.info("Selecteer een indicator om de kaart te tonen.")




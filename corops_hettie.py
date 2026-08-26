"""One-off script to construct the COROP areas that Hettie used for her indicators.
"""

import pandas as pd

import geopandas as gpd

fname = "d:\\Maps\\CBS\\2020\\cbsgebiedsindelingen2020.gpkg"
fname_CRH = "d:\\Maps\\CBS\\2020\\corops_hettie.gpkg"


lyrCR = "coropgebied_gegeneraliseerd_2020"
lyrCP = "coropplusgebied_gegeneraliseerd_2020"
lyrGM = "gemeente_gegeneraliseerd_2020"

gdf_CR = gpd.read_file(fname, layer=lyrCR)
gdf_CP = gpd.read_file(fname, layer=lyrCP)
gdf_GM = gpd.read_file(fname, layer=lyrGM)

rows_23_A = gdf_CP[gdf_CP["statcode"] == "CP2311"]  # Amsterdam
rows_23_N = pd.concat([ gdf_CP[gdf_CP["statcode"] == "CP2322"],   # tnv Amsterdam
                        gdf_GM[gdf_GM["statcode"].isin(["GM0431", "GM0415"])] ])
rows_23_S = pd.concat([ gdf_CP[gdf_CP["statcode"] == "CP2323"],   # tzv Amsterdam
                        gdf_GM[gdf_GM["statcode"].isin(["GM0384", "GM0437", "GM0362"])] ])

rows_40M = gdf_CP[gdf_CP["statcode"] == "CP4002"]  # Midden
rows_40A = gdf_CP[gdf_CP["statcode"] == "CP4001"]  # Almere
rows_40U = gdf_CP[gdf_CP["statcode"] == "CP4003"]  # Urk en NO polder

rows_11 = gdf_CR[gdf_CR["statcode"].isin(["CR10", "CR11", "CR12"])]
rows_13 = gdf_CR[gdf_CR["statcode"].isin(["CR13", "CR14", "CR15", "CR16"])]
rows_31 = gdf_CR[gdf_CR["statcode"].isin(["CR31", "CR32"])]
rows_33 = gdf_CR[gdf_CR["statcode"].isin(["CR33", "CR34", "CR35", "CR36"])]
rows_37 = gdf_CR[gdf_CR["statcode"].isin(["CR37", "CR38", "CR39"])]

rows_11["Code"] = "11"
rows_13["Code"] = "13"
rows_23_A["Code"] = "23_A"
rows_23_N["Code"] = "23_N"
rows_23_S["Code"] = "23_S"
rows_40M["Code"] = "40M"
rows_40A["Code"] = "40A"
rows_40U["Code"] = "40U"
rows_31["Code"] = "31-32"
rows_33["Code"] = "33-36"
rows_37["Code"] = "37-39"

gdf_combi0 = gdf_CR[~gdf_CR["statcode"].isin([
    "CR10", "CR11", "CR12", "CR13", "CR14", "CR15", "CR16",
    "CR23", "CR40", 
    "CR31", "CR32", "CR33", "CR34", "CR35", "CR36", "CR37", "CR38", "CR39"])]
gdf_combi0["Code"] = gdf_combi0["statcode"].str.replace("CR", "")

gdf_combi = gpd.GeoDataFrame(pd.concat([
    gdf_combi0, rows_11, rows_13, 
    rows_23_A, rows_23_N, rows_23_S, rows_40M, rows_40A, rows_40U,
    rows_31, rows_33, rows_37
]))

# combine (dissolve) the geometries by Code. 
# TODO: concatenate the statnaam attributes
aggs = {col: "first" for col in gdf_combi.columns if col not in ["geometry", "Code"]}
aggs["statnaam"] = " + ".join

# gdf_combi = gdf_combi.dissolve(by="Code", as_index=False, aggfunc=aggs)
gdf_combi = gdf_combi.dissolve(by="Code", aggfunc=aggs).reset_index()

gdf_combi.to_file(fname_CRH, layer="corops_hettie", driver="GPKG")

print("Ready")
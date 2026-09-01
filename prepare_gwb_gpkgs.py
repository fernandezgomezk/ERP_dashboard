"""Prepares set of gwb (gemeente-wijken-buurten) gpkg files that are efficient to use."""

import geopandas as gpd


#%% constants

path_CBS = "d:/Maps/CBS/"

files = {}
files[2019] = "cbsgebiedsindelingen2019.gpkg"
files[2020] = "cbsgebiedsindelingen2020.gpkg"
files[2021] = "cbsgebiedsindelingen2021.gpkg"
files[2022] = "cbsgebiedsindelingen2022.gpkg"
files[2023] = "cbsgebiedsindelingen2023.gpkg"
files[2024] = "cbsgebiedsindelingen2024.gpkg"
files[2025] = "cbsgebiedsindelingen2025.2026-02.gpkg"

# relevant_fields = ["statcode", "statnaam", "gm_code", "geometry"]

path_ERP = "s:/GitLab/ERP_dashboard/"

layer_wk_gg = "wijk_gegeneraliseerd"
layer_gm_gg = "gemeente_gegeneraliseerd"
layer_pv_gg = "provincie_gegeneraliseerd"


#%% functions

def test_wk_gm_code(row):
    """Tests if WKxxxxyy corresponds to GMxxxx."""
    gm_id_wk = row["wk_code"][2:6]
    gm_id_gm = row["gm_code"][2:6]
    if gm_id_wk != gm_id_gm:
        raise ValueError(f"GM and WK codes don't match: {row['wk_code']=}")
    return "OK"


#%% read and process

first_year = 2019

for year in files.keys():
    if year < first_year: continue
    print(year)
    fname = f"{path_CBS}{year}/{files[year]}"

    if year < 2023:    
        layer_wk = f"{layer_wk_gg}_{year}"
        layer_gm = f"{layer_gm_gg}_{year}"
        layer_pv = f"{layer_pv_gg}_{year}"
    else:    
        layer_wk = layer_wk_gg
        layer_gm = layer_gm_gg
        layer_pv = layer_pv_gg

    gdf_wk = gpd.read_file(fname, layer=layer_wk)
    gdf_gm = gpd.read_file(fname, layer=layer_gm)
    gdf_pv = gpd.read_file(fname, layer=layer_pv)
    
    gdf_wk = gdf_wk.rename({"statcode": "wk_code", "statnaam": "wk_naam"}, axis=1)
    gdf_gm = gdf_gm.rename({"statcode": "gm_code", "statnaam": "gm_naam"}, axis=1)
    gdf_pv = gdf_pv.rename({"statcode": "pv_code", "statnaam": "pv_naam"}, axis=1)
    
    # test if WKxxxxyy and GMxxxx always match. that makes the lookup easy.
    codes_ok = gdf_wk.apply(test_wk_gm_code, axis=1)
    (codes_ok == "OK").all()
    
    # use representative points of the gemeenten for spatial jin with provinces
    gdf_gm_rp = gdf_gm.copy()
    gdf_gm_rp["geometry"] = gdf_gm_rp["geometry"].representative_point()
    ggdf_gm_pv = gdf_gm_rp.sjoin(gdf_pv, how="inner")
    assert len(ggdf_gm_pv) == len(gdf_gm), "gdf_gm length has changed"

    # save gemeenten (limited list of attributes)
    df_gm_pv = ggdf_gm_pv.filter(["gm_code", "pv_code", "pv_naam"])
    gdf_gm_pv = gdf_gm.merge(df_gm_pv, on="gm_code", how="inner")
    gdf_gm_pv = gdf_gm_pv.filter(["gm_code", "gm_naam", "pv_code", "pv_naam", "geometry"], axis=1)
    layer = f"gemeenten_{year}"
    fname_dest = f"{path_ERP}data/gemeentenwijkenbuurten/{layer}.gpkg"
    gdf_gm_pv.to_file(fname_dest)
    df_gm_pv = gdf_gm_pv.filter(["gm_code", "gm_naam", "pv_code", "pv_naam"])
    
    gdf_wk_gm_pv = gdf_wk.merge(df_gm_pv, on="gm_code", how="inner")
    gdf_wk_gm_pv = gdf_wk_gm_pv.filter(["wk_code", "wk_naam", "gm_code", "gm_naam", "pv_code", "pv_naam", "geometry"], axis=1)
    layer = f"wijken_{year}"
    fname_dest = f"{path_ERP}data/gemeentenwijkenbuurten/{layer}.gpkg"
    gdf_wk_gm_pv.to_file(fname_dest)

print("Ready")
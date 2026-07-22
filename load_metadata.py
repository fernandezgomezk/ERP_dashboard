import yaml
from pathlib import Path

from streamlit.logger import get_logger
from collections import defaultdict

logger = get_logger("app.log")

# Functie om metadata in te lezen en bijbehorende gpkg zoeken
def load_metadata():
    datasets_meta = {}
    indicators_meta = defaultdict(list)

    metadata_dir = Path("metadata")
    data_dir = Path("data/indicatoren")

    for meta_file in metadata_dir.glob("*.meta.yaml"):

        if meta_file.name.startswith("example"):
            continue

        logger.info(f"Loading metadata from {meta_file}")
        # 1. Metadata lezen
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f)

        dataset_id = meta["dataset_id"]
        csv_path = data_dir / f"{dataset_id}.csv"

        # 2. Bijbehorende GPKG bepalen
        version = meta.get("gwb_version")
        
        if version:
            matches = list(Path("data/gemeentenwijkenbuurten").glob(f"*{version}.gpkg"))
            if not matches:
                raise FileNotFoundError(f"Geen GPKG gevonden voor versie {version}")
            if len(matches) > 1:
                print(f"⚠️ Meerdere GPKGs gevonden voor {version}, gebruik eerste")

            gpkg_path = matches[0]
        else:
            gpkg_path = None

        # 3. Dataset registreren
        datasets_meta[dataset_id] = {
            "csv_path": csv_path,
            "layer": meta.get("layer_naam"),
            "version": version,
            "key": meta["key"],
            "options": meta.get("options", []),
            "time_column": meta.get("time_column", []),
            "key_gwb": meta.get("key_gwb", None),
            "gpkg_path": gpkg_path,
            "categories": meta.get("categories", []),
            "mapping": meta.get("mapping", {})
        }

        # 4. Indicatoren registreren
        for indicator, indicator_meta in meta["indicators"].items():
            indicators_meta[indicator].append({
                "dataset": dataset_id,
                "title": indicator_meta["title"],
                "description": indicator_meta["description"],
                "legend": indicator_meta["legend"],
                "theme": indicator_meta["theme"],
                "subject": indicator_meta["subject"] or "",
                "precision": indicator_meta.get("precision", 1),
                "unit": indicator_meta.get("unit", "") or "",
                "visualization_type": indicator_meta["visualization_type"],
                "shown_maps": indicator_meta.get("shown_maps", 2),
                "map_columns": indicator_meta.get("map_columns"),
                "shared_color_scale": indicator_meta.get("shared_color_scale", True),
                "link": indicator_meta["link"],
                "test_values": indicator_meta.get("test_values", {})
            })


    return datasets_meta, indicators_meta
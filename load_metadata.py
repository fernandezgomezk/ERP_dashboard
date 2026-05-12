import yaml
from pathlib import Path


def load_metadata():
    datasets_meta = {}
    indicators_meta = {}

    metadata_dir = Path("metadata")
    data_dir = Path("data/indicatoren")

    for meta_file in metadata_dir.glob("*.meta.yaml"):

        # 1. Metadata lezen
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f)

        dataset_id = meta["dataset_id"]
        csv_path = data_dir / f"{dataset_id}.csv"

        # 2. Bijbehorende GPKG bepalen
        version = meta["gwb_version"]

        matches = list(Path("data/wijkenbuurten").glob(f"*{version}.gpkg"))
        if not matches:
            raise FileNotFoundError(f"Geen GPKG gevonden voor versie {version}")
        if len(matches) > 1:
            print(f"⚠️ Meerdere GPKGs gevonden voor {version}, gebruik eerste")
            
        gpkg_path = matches[0]

        # 3. Dataset registreren
        datasets_meta[dataset_id] = {
            "csv_path": csv_path,
            "layer": meta["layer_naam"],
            "version": meta["gwb_version"],
            "key": meta["key"],
            "gpkg_path": gpkg_path,
        }

        # 4. Indicatoren registreren
        for indicator, indicator_meta in meta["indicators"].items():
            indicators_meta[indicator] = {
                "dataset": dataset_id,
                "title": indicator_meta["title"],
                "legend": indicator_meta["legend"],
                "theme": indicator_meta["theme"],
                "subject": indicator_meta["subject"],
                "precision": indicator_meta.get("precision", 1),
                "unit": indicator_meta.get("unit", ""),
                "visualization_type": indicator_meta["visualization_type"],
                "link": indicator_meta["link"],
                "test_values": indicator_meta.get("test_values", {})
            }

    return datasets_meta, indicators_meta
import yaml
from pathlib import Path


def load_indicators():
    datasets = {}
    indicators = {}

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
        datasets[dataset_id] = {
            "csv_path": csv_path,
            "layer": meta["layer_naam"],
            "version": meta["gwb_version"],
            "key": meta["key"],
            "gpkg_path": gpkg_path,
        }

        # 4. Indicatoren registreren
        for indicator, cfg in meta["indicators"].items():
            indicators[indicator] = {
                "dataset": dataset_id,
                "title": cfg["title"],
                "legend": cfg["legend"],
                "theme": cfg["theme"],
                "subject": cfg["subject"],
                "precision": cfg.get("precision", 1),
                "unit": cfg.get("unit", ""), # Unit (3.4 -> 3.4%)
                "link": cfg["link"],
                "test_values": cfg.get("test_values", {})
            }

    return datasets, indicators
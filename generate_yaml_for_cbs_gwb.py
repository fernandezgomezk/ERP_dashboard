from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re

from pypdf import PdfReader
import yaml


TECHNICAL_FIELDS = {
    "fid",
    "jaarstatcode",
}

IDENTIFIER_FIELDS = {
    "gemeentecode",
    "gemeentenaam",
    "wijkcode",
    "wijknaam",
    "buurtcode",
    "buurtnaam",
    "jaar",
}

STOPWORDS = {
    "aantal",
    "aantallen",
    "gemiddeld",
    "gemiddelde",
    "percentage",
    "perc",
    "tot",
    "van",
    "met",
    "in",
    "per",
    "en",
    "de",
    "het",
    "uit",
}


@dataclass
class IndicatorMeta:
    """In-memory metadata for one indicator field."""

    field_name: str
    title: str
    description: str
    legend: str
    theme: str
    subject: str
    unit: str
    precision: int
    visualization_type: str
    link: str


def normalize_name(value: str) -> str:
    """Return a normalized key for robust field matching."""

    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def parse_value_line(line: str) -> tuple[str, str] | None:
    """Parse a single key:value line from the source text file."""

    if ":" not in line:
        return None
    key, value = line.split(":", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    return key, value


def load_field_samples(path: Path) -> dict[str, str]:
    """Load field names and sample values from a key:value text file."""

    output: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_value_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        output[key] = value
    return output


def value_precision(value: str) -> int:
    """Infer decimal precision from a numeric value string."""

    text = value.strip().replace(",", ".")
    if re.fullmatch(r"-?\d+", text):
        return 0
    if re.fullmatch(r"-?\d+\.\d+", text):
        return len(text.split(".", 1)[1])
    return 0


def is_numeric_value(value: str) -> bool:
    """Return True when the value can be interpreted as a number."""

    text = value.strip().replace(",", ".")
    return bool(re.fullmatch(r"-?\d+(\.\d+)?", text))


def prettify_title(field_name: str) -> str:
    """Convert a snake_case field name to a compact human-readable title."""

    words = field_name.replace("_", " ").strip()
    words = re.sub(r"\s+", " ", words)
    words = words.replace("gescheid", "gescheiden")
    return words[:1].upper() + words[1:]


def guess_theme_subject(field_name: str) -> tuple[str, str]:
    """Map field names to a theme and subject using simple heuristics."""

    lowered = field_name.lower()
    if any(token in lowered for token in ["woning", "huur", "koop", "bouwjaar", "gasverbruik", "elektriciteitsverbruik"]):
        return "Wonen en Energie", "Wonen"
    if any(token in lowered for token in ["inkomen", "vermogen", "koopkracht", "uitkering", "sociaal_minimum"]):
        return "Inkomen en Zekerheid", "Inkomen"
    if any(token in lowered for token in ["bevolking", "inwoners", "mannen", "vrouwen", "huishoudens", "migratie", "geboorte", "sterfte"]):
        return "Demografie", "Bevolking"
    if any(token in lowered for token in ["afstand", "station", "autos", "verkeersweg", "vervoer"]):
        return "Mobiliteit en Bereikbaarheid", "Bereikbaarheid"
    if any(token in lowered for token in ["huisarts", "ziekenhuis", "apotheek", "wmo", "jeugdzorg"]):
        return "Zorg en Voorzieningen", "Zorg"
    if any(token in lowered for token in ["supermarkt", "winkels", "restaurant", "hotel", "bibliotheek", "bioscoop", "theater", "museum"]):
        return "Voorzieningen", "Voorzieningenniveau"
    if any(token in lowered for token in ["oppervlakte", "water", "land"]):
        return "Ruimte", "Oppervlakte"
    return "CBS GWB", "Overig"


def guess_unit(field_name: str, sample_value: str) -> str:
    """Infer a display unit based on field naming patterns."""

    lowered = field_name.lower()
    if lowered.startswith("percentage_") or lowered.startswith("perc_"):
        return "%"
    if "_per_1000_" in lowered:
        return " per 1000"
    if "_per_km2" in lowered:
        return " per km2"
    if "_in_km" in lowered or "afstand" in lowered:
        return " km"
    if "_in_ha" in lowered:
        return " ha"
    if "inkomen" in lowered or "woningwaarde" in lowered or "vermogen" in lowered:
        return " x1000 euro"
    if "gasverbruik" in lowered:
        return " m3"
    if "elektriciteitsverbruik" in lowered:
        return " kWh"
    if is_numeric_value(sample_value):
        return ""
    return ""


def parse_pdf_lines(pdf_path: Path) -> list[str]:
    """Extract compact non-empty lines from the PDF text."""

    reader = PdfReader(str(pdf_path))
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for line in text.splitlines():
            compact = re.sub(r"\s+", " ", line).strip()
            if len(compact) >= 24:
                lines.append(compact)
    return lines


def field_tokens(field_name: str) -> set[str]:
    """Create matching tokens from a technical field name."""

    tokens = set(part for part in field_name.lower().split("_") if part and part not in STOPWORDS)
    output: set[str] = set()
    for token in tokens:
        if len(token) >= 3:
            output.add(token)
            continue
        if token.isdigit() and len(token) >= 2:
            output.add(token)
    return output


def normalize_token(token: str) -> str:
    """Normalize a single token to reduce minor wording differences."""

    cleaned = token.lower().strip()
    if len(cleaned) > 5 and cleaned.endswith("en"):
        return cleaned[:-2]
    if len(cleaned) > 4 and cleaned.endswith("s"):
        return cleaned[:-1]
    return cleaned


def line_tokens(line: str) -> set[str]:
    """Extract comparable tokens from a PDF line."""

    parts = re.split(r"[^a-z0-9]+", line.lower())
    return {normalize_token(part) for part in parts if part}


def clean_pdf_line(line: str) -> str:
    """Normalize a PDF line so it can be used as a concise description."""

    cleaned = re.sub(r"\s+", " ", line).strip()
    cleaned = re.sub(r"^[A-Z0-9_]{2,}\s*:\s*", "", cleaned)
    return cleaned


def is_structured_definition_line(line: str) -> bool:
    """Return True when a line likely represents a variable definition entry."""

    return bool(re.match(r"^[A-Z0-9_]{2,}\s*:\s*.+", line))


def fallback_description(field_name: str, title: str, unit: str) -> str:
    """Generate a deterministic and compact fallback description."""

    lowered = field_name.lower()
    if lowered.startswith("percentage_") or lowered.startswith("perc_"):
        return f"{title} per gemeente."
    if lowered.startswith("aantal_"):
        # return f"Aantal voor '{title}' per gemeente."
        return f"{title} per gemeente."
    if lowered.startswith("gemiddeld_") or lowered.startswith("gemiddelde_"):
        return f"Gemiddelde waarde van '{title}' per gemeente."
    if "_per_1000_" in lowered:
        return f"{title} uitgedrukt per 1000 inwoners."
    if unit.strip() == "%":
        return f"Relatieve indicator '{title}' als percentage per gemeente."
    return f"{title} per gemeente op basis van CBS GWB data."


def pick_best_description(field_name: str, pdf_lines: list[str]) -> tuple[str, int]:
    """Pick the most relevant PDF definition line for a field and return confidence."""

    tokens = field_tokens(field_name)
    if not tokens:
        return "", 0
    normalized_field_tokens = {normalize_token(token) for token in tokens}

    best_line = ""
    best_score = 0
    relevant_lines = [line for line in pdf_lines if is_structured_definition_line(line)]
    if not relevant_lines:
        relevant_lines = pdf_lines

    for line in relevant_lines:
        candidate_tokens = line_tokens(line)
        overlap = sum(1 for token in normalized_field_tokens if token in candidate_tokens)
        if overlap == 0:
            continue
        token_coverage = overlap / len(normalized_field_tokens)
        density_bonus = 2 if token_coverage >= 0.5 else 0
        code_pattern_bonus = 2 if is_structured_definition_line(line) else 0
        score = overlap * 2 + density_bonus + code_pattern_bonus
        if score > best_score:
            best_score = score
            best_line = line

    return clean_pdf_line(best_line), best_score


def should_use_pdf_description(field_name: str, description: str, score: int) -> bool:
    """Decide whether a matched PDF description is semantically safe to use."""

    if not description or score < 7:
        return False

    lowered_field = field_name.lower()
    lowered_description = description.lower()

    if lowered_field.startswith("aantal_") and "%" in lowered_description:
        return False
    if lowered_field.startswith("percentage_") and "%" not in lowered_description:
        return False
    if "_met_" in lowered_field and "zonder" in lowered_description:
        return False
    if "_zonder_" in lowered_field and " met " in f" {lowered_description} ":
        return False
    if "_uit_" in lowered_field and "uitkering" in lowered_description:
        return False

    country_tokens = ["marokko", "suriname", "turkije", "aruba", "antillen"]
    for token in country_tokens:
        if token in lowered_field and token not in lowered_description:
            return False

    return True


def build_indicator_meta(field_name: str, sample_value: str, pdf_lines: list[str]) -> IndicatorMeta:
    """Create metadata content for one numeric indicator field."""

    title = prettify_title(field_name)
    unit = guess_unit(field_name, sample_value)
    description, match_score = pick_best_description(field_name, pdf_lines)
    if not should_use_pdf_description(field_name, description, match_score):
        description = fallback_description(field_name, title, unit)
    theme, subject = guess_theme_subject(field_name)

    return IndicatorMeta(
        field_name=field_name,
        title=title,
        description=description,
        legend=title,
        theme=theme,
        subject=subject,
        unit=unit,
        precision=value_precision(sample_value),
        visualization_type="map",
        link="",
    )


def choose_key(field_samples: dict[str, str]) -> str:
    """Choose the primary join key for the dataset."""

    if "gemeentecode" in field_samples:
        return "gemeentecode"
    if "gemeentenaam" in field_samples:
        return "gemeentenaam"
    candidates = [name for name in field_samples if name.endswith("code")]
    return candidates[0] if candidates else next(iter(field_samples))


def choose_key_gwb(key: str) -> str:
    """Choose the corresponding key in the geometry source."""

    if key.endswith("code"):
        return "statcode"
    return "statnaam"


def build_metadata_document(
    dataset_id: str,
    field_samples: dict[str, str],
    pdf_lines: list[str],
) -> dict:
    """Build the complete metadata structure in dashboard YAML format."""

    key = choose_key(field_samples)
    numeric_fields = [
        name
        for name, value in field_samples.items()
        if is_numeric_value(value) and name not in TECHNICAL_FIELDS and name not in IDENTIFIER_FIELDS
    ]

    indicators = {}
    for field_name in numeric_fields:
        item = build_indicator_meta(field_name, field_samples[field_name], pdf_lines)
        indicators[field_name] = {
            "title": item.title,
            "description": item.description,
            "legend": item.legend,
            "theme": item.theme,
            "subject": item.subject,
            "unit": item.unit,
            "precision": item.precision,
            "visualization_type": item.visualization_type,
            "link": item.link,
        }

    return {
        "dataset_id": dataset_id,
        "key": key,
        "options": [],
        "time_column": "jaar" if "jaar" in field_samples else "",
        "gwb_version": "2019_v3",
        "layer_naam": "gemeente_gegeneraliseerd_2019",
        "key_gwb": choose_key_gwb(key),
        "indicators": indicators,
    }


def write_compact_yaml(path: Path, content: dict) -> None:
    """Write YAML without comments and blank lines in compact style."""

    serialized = yaml.safe_dump(
        content,
        allow_unicode=False,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    compact_lines = [line for line in serialized.splitlines() if line.strip()]
    path.write_text("\n".join(compact_lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for metadata generation."""

    parser = argparse.ArgumentParser(description="Generate compact dashboard YAML metadata from CBS GWB sources.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/gemeentenwijkenbuurten/voorbeeld.txt"),
        help="Path to key:value source file with CBS fields.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("data/gemeentenwijkenbuurten/Doc/toelichting-wijk-en-buurtkaart-2017-2018-en-2019.pdf"),
        help="Path to PDF with field descriptions.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("metadata/temp/voorbeeld.meta.yaml"),
        help="Path of the generated compact metadata YAML.",
    )
    parser.add_argument(
        "--dataset-id",
        type=str,
        default="voorbeeld",
        help="Dataset identifier to write into YAML.",
    )
    return parser.parse_args()


def main() -> None:
    """Generate a compact YAML metadata file from the configured sources."""

    args = parse_args()
    field_samples = load_field_samples(args.source)
    pdf_lines = parse_pdf_lines(args.pdf)
    metadata = build_metadata_document(args.dataset_id, field_samples, pdf_lines)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_compact_yaml(args.output, metadata)

    print(f"Generated compact YAML: {args.output}")
    print(f"Indicators: {len(metadata['indicators'])}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEATHER_METADATA_PATH = PROJECT_ROOT / "data" / "external" / "weather_history_metadata.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "external" / "air_quality_history.csv"
DEFAULT_METADATA = PROJECT_ROOT / "data" / "external" / "air_quality_history_metadata.json"

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

SEASON_PERIODS_2025 = {
    "hiver": ("2024-12-01", "2025-02-28"),
    "printemps": ("2025-03-01", "2025-05-31"),
    "été": ("2025-06-01", "2025-08-31"),
    "automne": ("2025-09-01", "2025-11-30"),
}


def fetch_json(url: str, params: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def load_locations(metadata_path: Path) -> dict[str, Any]:
    if not metadata_path.exists():
        raise FileNotFoundError(
            "Le fichier météo doit être généré avant la qualité de l'air : "
            f"{metadata_path}"
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return metadata["destinations"]


def clean_values(values: list[Any]) -> list[float]:
    return [float(value) for value in values if value is not None]


def summarize_air_quality(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict[str, float | int]:
    payload = fetch_json(
        AIR_QUALITY_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": [
                "pm10",
                "pm2_5",
                "european_aqi",
                "uv_index",
            ],
            "timezone": "auto",
        },
    )
    hourly = payload["hourly"]

    pm10_values = clean_values(hourly.get("pm10", []))
    pm25_values = clean_values(hourly.get("pm2_5", []))
    aqi_values = clean_values(hourly.get("european_aqi", []))
    uv_values = clean_values(hourly.get("uv_index", []))

    return {
        "pm10_moyen": round(mean(pm10_values), 2) if pm10_values else 0.0,
        "pm2_5_moyen": round(mean(pm25_values), 2) if pm25_values else 0.0,
        "european_aqi_moyen": round(mean(aqi_values), 2) if aqi_values else 0.0,
        "uv_index_moyen": round(mean(uv_values), 2) if uv_values else 0.0,
        "heures_observees_air": int(len(hourly.get("time", []))),
    }


def build_air_quality_history(
    weather_metadata_path: Path,
    output_path: Path,
    metadata_path: Path,
) -> None:
    locations = load_locations(weather_metadata_path)
    rows = []

    for destination, location in locations.items():
        for season, (start_date, end_date) in SEASON_PERIODS_2025.items():
            summary = summarize_air_quality(
                latitude=float(location["latitude"]),
                longitude=float(location["longitude"]),
                start_date=start_date,
                end_date=end_date,
            )
            rows.append({
                "destination": destination,
                "saison": season,
                "pm10_moyen": summary["pm10_moyen"],
                "pm2_5_moyen": summary["pm2_5_moyen"],
                "european_aqi_moyen": summary["european_aqi_moyen"],
                "uv_index_moyen": summary["uv_index_moyen"],
                "heures_observees_air": summary["heures_observees_air"],
                "source_air_quality": "Open-Meteo Air Quality API",
                "periode_reference_air_quality": f"{start_date}/{end_date}",
            })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "destination",
                "saison",
                "pm10_moyen",
                "pm2_5_moyen",
                "european_aqi_moyen",
                "uv_index_moyen",
                "heures_observees_air",
                "source_air_quality",
                "periode_reference_air_quality",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Open-Meteo Air Quality API",
        "air_quality_url": AIR_QUALITY_URL,
        "rows": len(rows),
        "season_periods": SEASON_PERIODS_2025,
        "usage": "Données réelles de qualité de l'air disponibles avant modélisation, agrégées par destination et saison.",
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construit data/external/air_quality_history.csv depuis Open-Meteo.",
    )
    parser.add_argument("--weather-metadata", type=Path, default=WEATHER_METADATA_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_air_quality_history(args.weather_metadata, args.output, args.metadata)
    print(f"Fichier qualité de l'air généré : {args.output}")
    print(f"Métadonnées générées : {args.metadata}")


if __name__ == "__main__":
    main()

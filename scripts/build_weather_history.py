from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

try:
    import requests
except ImportError:  # pragma: no cover - fallback for minimal environments
    requests = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "external" / "weather_history.csv"
DEFAULT_METADATA = PROJECT_ROOT / "data" / "external" / "weather_history_metadata.json"

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DESTINATIONS = {
    "paris": {"query": "Paris", "country_code": "FR"},
    "rome": {"query": "Rome", "country_code": "IT"},
    "lisbonne": {"query": "Lisbon", "country_code": "PT"},
    "new york": {"query": "New York", "country_code": "US"},
    "tokyo": {"query": "Tokyo", "country_code": "JP"},
    "sydney": {"query": "Sydney", "country_code": "AU"},
    "dubaï": {"query": "Dubai", "country_code": "AE"},
    "bali": {"query": "Denpasar", "country_code": "ID"},
}

SEASON_PERIODS_2025 = {
    "hiver": ("2024-12-01", "2025-02-28"),
    "printemps": ("2025-03-01", "2025-05-31"),
    "été": ("2025-06-01", "2025-08-31"),
    "automne": ("2025-09-01", "2025-11-30"),
}


def fetch_json(url: str, params: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    if requests is not None:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()

    api_url = f"{url}?{urlencode(params, doseq=True)}"
    with urlopen(api_url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def geocode_destination(destination: str, config: dict[str, str]) -> dict[str, Any]:
    payload = fetch_json(
        GEOCODING_URL,
        {
            "name": config["query"],
            "count": 5,
            "language": "fr",
            "format": "json",
        },
    )
    results = payload.get("results", [])
    country_code = config["country_code"].upper()
    filtered = [
        result for result in results
        if str(result.get("country_code", "")).upper() == country_code
    ]
    selected = (filtered or results)[0]
    return {
        "destination": destination,
        "query": config["query"],
        "country_code": selected.get("country_code"),
        "city_name": selected.get("name"),
        "latitude": float(selected["latitude"]),
        "longitude": float(selected["longitude"]),
        "timezone": selected.get("timezone", "auto"),
    }


def summarize_weather(latitude: float, longitude: float, start_date: str, end_date: str) -> dict[str, float]:
    payload = fetch_json(
        ARCHIVE_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": [
                "temperature_2m_mean",
                "precipitation_sum",
                "wind_speed_10m_max",
            ],
            "timezone": "auto",
        },
    )
    daily = payload["daily"]
    temperatures = [value for value in daily["temperature_2m_mean"] if value is not None]
    precipitations = [value for value in daily["precipitation_sum"] if value is not None]
    winds = [value for value in daily["wind_speed_10m_max"] if value is not None]

    rainy_days = sum(1 for value in precipitations if value > 1.0)
    days = len(precipitations)

    return {
        "temperature_moyenne_saison": round(mean(temperatures), 2),
        "pluie_moyenne_mm": round(mean(precipitations), 2),
        "jours_pluie_moyen": int(rainy_days),
        "vent_max_moyen_kmh": round(mean(winds), 2),
        "nb_jours_observes": int(days),
    }


def build_weather_history(output_path: Path, metadata_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    locations = {
        destination: geocode_destination(destination, config)
        for destination, config in DESTINATIONS.items()
    }

    rows = []
    for destination, location in locations.items():
        for season, (start_date, end_date) in SEASON_PERIODS_2025.items():
            summary = summarize_weather(
                latitude=location["latitude"],
                longitude=location["longitude"],
                start_date=start_date,
                end_date=end_date,
            )
            rows.append({
                "destination": destination,
                "saison": season,
                "temperature_moyenne_saison": summary["temperature_moyenne_saison"],
                "pluie_moyenne_mm": summary["pluie_moyenne_mm"],
                "jours_pluie_moyen": summary["jours_pluie_moyen"],
                "vent_max_moyen_kmh": summary["vent_max_moyen_kmh"],
                "nb_jours_observes": summary["nb_jours_observes"],
                "latitude": round(location["latitude"], 6),
                "longitude": round(location["longitude"], 6),
                "source": "Open-Meteo Historical Weather API",
                "periode_reference": f"{start_date}/{end_date}",
            })

    fieldnames = [
        "destination",
        "saison",
        "temperature_moyenne_saison",
        "pluie_moyenne_mm",
        "jours_pluie_moyen",
        "vent_max_moyen_kmh",
        "nb_jours_observes",
        "latitude",
        "longitude",
        "source",
        "periode_reference",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Open-Meteo Historical Weather API",
        "geocoding_source": "Open-Meteo Geocoding API",
        "archive_url": ARCHIVE_URL,
        "geocoding_url": GEOCODING_URL,
        "rows": len(rows),
        "destinations": locations,
        "season_periods": SEASON_PERIODS_2025,
        "usage": "Données météo historiques disponibles avant modélisation, agrégées par destination et saison.",
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construit data/external/weather_history.csv depuis Open-Meteo.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_weather_history(args.output, args.metadata)
    print(f"Fichier météo généré : {args.output}")
    print(f"Métadonnées générées : {args.metadata}")


if __name__ == "__main__":
    main()

import json
from pathlib import Path

import pandas as pd

from scripts.enrich_dataset import enrich_dataset


def test_enrich_dataset_adds_external_columns(tmp_path: Path):
    base_path = tmp_path / "base.csv"
    hotel_path = tmp_path / "hotel_quality.csv"
    config_path = tmp_path / "enrichment_sources.json"
    output_dir = tmp_path / "output"

    pd.DataFrame([
        {
            "destination": "rome",
            "type_hebergement": "hôtel",
            "saison": "printemps",
            "budget_total": 4200,
        },
        {
            "destination": "bali",
            "type_hebergement": "resort",
            "saison": "été",
            "budget_total": 3600,
        },
    ]).to_csv(base_path, index=False)

    pd.DataFrame([
        {
            "destination": "Rome",
            "type_hebergement": "Hôtel",
            "note_hebergement": 4.6,
            "nb_avis_hebergement": 1280,
            "classement_hebergement": 5,
        }
    ]).to_csv(hotel_path, index=False)

    config_path.write_text(
        json.dumps({
            "policy": {"use_only_before_departure_data": True},
            "sources": [
                {
                    "name": "hotel_quality",
                    "file": str(hotel_path),
                    "join_keys": ["destination", "type_hebergement"],
                    "expected_columns": [
                        "destination",
                        "type_hebergement",
                        "note_hebergement",
                        "nb_avis_hebergement",
                        "classement_hebergement",
                    ],
                }
            ],
        }),
        encoding="utf-8",
    )

    output_dataset_path, output_report_path = enrich_dataset(
        base_dataset_path=base_path,
        config_path=config_path,
        output_dir=output_dir,
    )

    enriched = pd.read_csv(output_dataset_path)
    report = json.loads(output_report_path.read_text(encoding="utf-8"))

    assert "note_hebergement" in enriched.columns
    assert enriched.loc[0, "note_hebergement"] == 4.6
    assert pd.isna(enriched.loc[1, "note_hebergement"])
    assert report["sources"][0]["status"] == "loaded"
    assert report["sources"][0]["rows_matched"] == 1


def test_enrich_dataset_skips_missing_source(tmp_path: Path):
    base_path = tmp_path / "base.csv"
    config_path = tmp_path / "enrichment_sources.json"
    output_dir = tmp_path / "output"

    pd.DataFrame([{"destination": "rome"}]).to_csv(base_path, index=False)

    config_path.write_text(
        json.dumps({
            "sources": [
                {
                    "name": "flight_features",
                    "file": str(tmp_path / "missing.csv"),
                    "join_keys": ["destination"],
                    "expected_columns": ["destination", "duree_vol_heures"],
                }
            ],
        }),
        encoding="utf-8",
    )

    _, output_report_path = enrich_dataset(
        base_dataset_path=base_path,
        config_path=config_path,
        output_dir=output_dir,
    )

    report = json.loads(output_report_path.read_text(encoding="utf-8"))
    assert report["sources"][0]["status"] == "missing_file"

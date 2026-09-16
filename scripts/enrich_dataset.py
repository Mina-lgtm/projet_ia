from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_DATASET = (
    PROJECT_ROOT
    / "data"
    / "versions"
    / "v2_0_feature_engineering"
    / "travel_planning_dataset_v2_0.csv"
)
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "enrichment_sources.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "versions" / "v2_1_enrichment"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def normalize_text_key(values: pd.Series) -> pd.Series:
    return (
        values
        .astype("string")
        .str.strip()
        .str.lower()
    )


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration d'enrichissement introuvable: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def normalize_join_keys(df: pd.DataFrame, join_keys: list[str]) -> pd.DataFrame:
    normalized = df.copy()
    for key in join_keys:
        if key in normalized.columns:
            normalized[key] = normalize_text_key(normalized[key])
    return normalized


def deduplicate_external_source(
    source_df: pd.DataFrame,
    join_keys: list[str],
) -> pd.DataFrame:
    data_columns = [column for column in source_df.columns if column not in join_keys]
    aggregations = {}

    for column in data_columns:
        numeric_values = pd.to_numeric(source_df[column], errors="coerce")
        if numeric_values.notna().any():
            source_df[column] = numeric_values
            aggregations[column] = "mean"
        else:
            aggregations[column] = "first"

    if not aggregations:
        return source_df[join_keys].drop_duplicates()

    return (
        source_df
        .groupby(join_keys, as_index=False, dropna=False)
        .agg(aggregations)
    )


def apply_enrichment_source(
    base_df: pd.DataFrame,
    source_config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_name = source_config["name"]
    source_path = PROJECT_ROOT / source_config["file"]
    join_keys = source_config["join_keys"]
    expected_columns = source_config["expected_columns"]

    report: dict[str, Any] = {
        "source": source_name,
        "file": source_config["file"],
        "join_keys": join_keys,
        "status": "not_loaded",
        "rows_source": 0,
        "rows_matched": 0,
        "columns_added": [],
        "message": "",
    }

    missing_base_keys = [key for key in join_keys if key not in base_df.columns]
    if missing_base_keys:
        report["status"] = "skipped"
        report["message"] = f"Clés absentes du dataset de base: {missing_base_keys}"
        return base_df, report

    if not source_path.exists():
        report["status"] = "missing_file"
        report["message"] = "Fichier externe absent, enrichissement ignoré."
        return base_df, report

    source_df = pd.read_csv(source_path)
    if source_df.empty:
        report["status"] = "empty_file"
        report["message"] = "Fichier externe vide, enrichissement ignoré."
        return base_df, report

    missing_source_columns = [
        column for column in expected_columns
        if column not in source_df.columns
    ]
    if missing_source_columns:
        report["status"] = "invalid_schema"
        report["message"] = f"Colonnes attendues absentes: {missing_source_columns}"
        return base_df, report

    source_df = normalize_join_keys(source_df[expected_columns].copy(), join_keys)
    source_df = deduplicate_external_source(source_df, join_keys)
    base_normalized = normalize_join_keys(base_df, join_keys)

    external_keys = source_df[join_keys].drop_duplicates()
    matched = (
        base_normalized[join_keys]
        .merge(external_keys.assign(__matched=True), on=join_keys, how="left")
        ["__matched"]
        .eq(True)
    )

    columns_before = set(base_normalized.columns)
    enriched_df = base_normalized.merge(source_df, on=join_keys, how="left")
    columns_after = set(enriched_df.columns)

    report["status"] = "loaded"
    report["rows_source"] = int(source_df.shape[0])
    report["rows_matched"] = int(matched.sum())
    report["columns_added"] = sorted(columns_after - columns_before)
    report["message"] = "Source enrichie avec succès."

    return enriched_df, report


def enrich_dataset(
    base_dataset_path: Path,
    config_path: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    if not base_dataset_path.exists():
        raise FileNotFoundError(f"Dataset de base introuvable: {base_dataset_path}")

    config = load_config(config_path)
    enriched_df = pd.read_csv(base_dataset_path)

    reports = []
    for source_config in config["sources"]:
        enriched_df, report = apply_enrichment_source(enriched_df, source_config)
        reports.append(report)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dataset_path = output_dir / "travel_planning_dataset_v2_1.csv"
    output_report_path = output_dir / "enrichment_report.json"

    enriched_df.to_csv(output_dataset_path, index=False, encoding="utf-8-sig")

    report_payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_dataset": display_path(base_dataset_path),
        "output_dataset": display_path(output_dataset_path),
        "rows": int(enriched_df.shape[0]),
        "columns": int(enriched_df.shape[1]),
        "sources": reports,
        "policy": config.get("policy", {}),
    }
    output_report_path.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_dataset_path, output_report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enrichit le dataset TravelMind avec des sources externes optionnelles.",
    )
    parser.add_argument(
        "--base-dataset",
        type=Path,
        default=DEFAULT_BASE_DATASET,
        help=f"Dataset de base. Défaut: {DEFAULT_BASE_DATASET}",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Configuration des sources. Défaut: {DEFAULT_CONFIG_PATH}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Dossier de sortie. Défaut: {DEFAULT_OUTPUT_DIR}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dataset_path, output_report_path = enrich_dataset(
        base_dataset_path=args.base_dataset,
        config_path=args.config,
        output_dir=args.output_dir,
    )

    print(f"Dataset enrichi généré : {output_dataset_path}")
    print(f"Rapport généré : {output_report_path}")


if __name__ == "__main__":
    main()

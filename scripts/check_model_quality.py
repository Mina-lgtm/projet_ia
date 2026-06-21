from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "metric_minimums": {
        "accuracy": 0.30,
        "balanced_accuracy": 0.30,
        "macro_f1": 0.30,
    },
    "reference_metrics": {},
    "max_allowed_metric_drop": {},
    "row_count_minimums": {
        "train_rows": 1000,
        "test_rows": 200,
    },
    "metadata_max_age_days": 30,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vérifie que les métriques du modèle respectent les seuils CI/CD.",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=Path("models/model_pre_voyage_metadata.json"),
        help="Chemin du fichier de métadonnées produit par train.py.",
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=Path("configs/model_quality_gate.json"),
        help="Chemin du fichier JSON contenant les seuils qualité.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(path: Path) -> dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    if path.exists():
        user_config = load_json(path)
        for key, value in user_config.items():
            config[key] = value
    return config


def parse_created_at(value: str) -> datetime:
    normalized_value = value.replace("Z", "+00:00")
    created_at = datetime.fromisoformat(normalized_value)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at.astimezone(timezone.utc)


def check_metric_minimums(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> list[str]:
    failures = []
    for metric_name, minimum_value in thresholds.items():
        if metric_name not in metrics:
            failures.append(f"{metric_name} absent des métriques")
            continue
        actual_value = float(metrics.get(metric_name, float("nan")))
        if actual_value < float(minimum_value):
            failures.append(
                f"{metric_name}={actual_value:.4f} < seuil minimal {minimum_value:.4f}"
            )
    return failures


def check_metric_variation(
    metrics: dict[str, Any],
    reference_metrics: dict[str, float],
    max_allowed_drop: dict[str, float],
) -> list[str]:
    failures = []
    for metric_name, reference_value in reference_metrics.items():
        if metric_name not in metrics:
            failures.append(f"{metric_name} absent des métriques")
            continue
        allowed_drop = float(max_allowed_drop.get(metric_name, 0))
        minimum_value = float(reference_value) - allowed_drop
        actual_value = float(metrics.get(metric_name, float("nan")))
        if actual_value < minimum_value:
            failures.append(
                f"{metric_name}={actual_value:.4f} < référence {reference_value:.4f} "
                f"- baisse autorisée {allowed_drop:.4f}"
            )
    return failures


def check_row_counts(
    metrics: dict[str, Any],
    thresholds: dict[str, int],
) -> list[str]:
    failures = []
    for row_count_name, minimum_value in thresholds.items():
        if row_count_name not in metrics:
            failures.append(f"{row_count_name} absent des métriques")
            continue
        actual_value = int(metrics.get(row_count_name, 0))
        if actual_value < int(minimum_value):
            failures.append(
                f"{row_count_name}={actual_value} < seuil minimal {minimum_value}"
            )
    return failures


def check_metadata_age(metadata: dict[str, Any], max_age_days: int | None) -> list[str]:
    if max_age_days is None:
        return []

    created_at_value = metadata.get("created_at_utc")
    if not created_at_value:
        return ["created_at_utc absent des métadonnées"]

    created_at = parse_created_at(str(created_at_value))
    age_days = (datetime.now(timezone.utc) - created_at).total_seconds() / 86400
    if age_days > max_age_days:
        return [
            f"métadonnées obsolètes : âge {age_days:.1f} jours > seuil {max_age_days}"
        ]
    return []


def main() -> int:
    args = parse_args()
    metadata = load_json(args.metadata_path)
    config = load_config(args.config_path)
    metrics = metadata.get("metrics", {})

    failures = []
    failures.extend(
        check_metric_minimums(metrics, config.get("metric_minimums", {}))
    )
    failures.extend(
        check_metric_variation(
            metrics,
            config.get("reference_metrics", {}),
            config.get("max_allowed_metric_drop", {}),
        )
    )
    failures.extend(check_row_counts(metrics, config.get("row_count_minimums", {})))
    failures.extend(check_metadata_age(metadata, config.get("metadata_max_age_days")))

    print("Contrôle qualité modèle")
    print(f"Modèle : {metadata.get('model_name')}")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))

    if failures:
        print("\nÉchec du quality gate :")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nQuality gate validé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

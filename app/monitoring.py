from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from app.modeling import prepare_prediction_features
from app.schemas import TravelPredictionRequest, TravelPredictionResponse


DEFAULT_PREDICTION_LOG_PATH = Path("logs/predictions/predictions.jsonl")
DEFAULT_MODEL_METADATA_PATH = Path("models/model_pre_voyage_metadata.json")
LOW_CONFIDENCE_THRESHOLD = 0.50
NUMERIC_DRIFT_WARNING_THRESHOLD = 1.0
NUMERIC_DRIFT_CRITICAL_THRESHOLD = 2.0
CATEGORICAL_DRIFT_WARNING_THRESHOLD = 0.20
CATEGORICAL_DRIFT_CRITICAL_THRESHOLD = 0.35
MIN_MONITORING_SAMPLE_SIZE = 20
LOW_CONFIDENCE_WARNING_RATE = 40.0
LOW_CONFIDENCE_CRITICAL_RATE = 60.0


class PredictionLogger:
    def __init__(self, log_path: Path = DEFAULT_PREDICTION_LOG_PATH) -> None:
        self.log_path = log_path

    def log_prediction(
        self,
        request: TravelPredictionRequest,
        response: TravelPredictionResponse,
    ) -> dict[str, Any]:
        probabilities = [
            probability.model_dump()
            for probability in (response.probabilities or [])
        ]
        confidence = max(
            (probability["probabilite"] for probability in probabilities),
            default=None,
        )

        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "objective": response.objective,
            "model_name": response.model_name,
            "input": request.model_dump(),
            "classe_predite": response.classe_predite,
            "libelle_prediction": response.libelle_prediction,
            "probabilities": probabilities,
            "confidence": confidence,
            "low_confidence": (
                confidence is not None
                and confidence < LOW_CONFIDENCE_THRESHOLD
            ),
            "model_metrics": response.model_metrics,
        }

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record


def load_prediction_logs(log_path: Path = DEFAULT_PREDICTION_LOG_PATH) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []

    records = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))

    return records


def build_monitoring_report(
    log_path: Path = DEFAULT_PREDICTION_LOG_PATH,
) -> dict[str, Any]:
    records = load_prediction_logs(log_path)

    if not records:
        return {
            "nb_predictions": 0,
            "message": "Aucune prédiction journalisée pour le moment.",
            "prediction_distribution": {},
            "low_confidence_rate": None,
            "average_confidence": None,
            "model_distribution": {},
            "latest_model_metrics": {},
        }

    prediction_counter = Counter(
        record.get("libelle_prediction", "inconnu")
        for record in records
    )
    model_counter = Counter(
        record.get("model_name", "inconnu")
        for record in records
    )
    low_confidence_count = sum(
        1 for record in records
        if record.get("low_confidence") is True
    )
    confidence_values = [
        float(record["confidence"])
        for record in records
        if record.get("confidence") is not None
    ]
    latest_model_metrics = next(
        (
            record.get("model_metrics", {})
            for record in reversed(records)
            if record.get("model_metrics")
        ),
        {},
    )

    nb_predictions = len(records)

    return {
        "nb_predictions": nb_predictions,
        "first_prediction_utc": records[0].get("timestamp_utc"),
        "last_prediction_utc": records[-1].get("timestamp_utc"),
        "prediction_distribution": dict(prediction_counter),
        "prediction_distribution_pct": {
            label: round(count / nb_predictions * 100, 2)
            for label, count in prediction_counter.items()
        },
        "low_confidence_count": low_confidence_count,
        "low_confidence_rate": round(low_confidence_count / nb_predictions * 100, 2),
        "average_confidence": (
            round(sum(confidence_values) / len(confidence_values), 4)
            if confidence_values else None
        ),
        "model_distribution": dict(model_counter),
        "latest_model_metrics": latest_model_metrics,
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "interpretation": (
            "Un taux élevé de faible confiance indique que les prédictions doivent "
            "être relues par un humain et que le modèle pré-voyage reste indicatif."
        ),
    }


def _drift_level(score: float, warning_threshold: float, critical_threshold: float) -> str:
    if score >= critical_threshold:
        return "critical"
    if score >= warning_threshold:
        return "warning"
    return "ok"


def _total_variation_distance(
    reference_distribution: dict[str, float],
    current_distribution: dict[str, float],
) -> float:
    categories = set(reference_distribution) | set(current_distribution)
    return 0.5 * sum(
        abs(current_distribution.get(category, 0.0) - reference_distribution.get(category, 0.0))
        for category in categories
    )


def build_drift_report(
    log_path: Path = DEFAULT_PREDICTION_LOG_PATH,
    metadata_path: Path = DEFAULT_MODEL_METADATA_PATH,
) -> dict[str, Any]:
    records = load_prediction_logs(log_path)
    if not records:
        return {
            "status": "no_predictions",
            "nb_predictions_analyzed": 0,
            "message": "Aucune prédiction journalisée pour calculer une dérive.",
        }

    if not metadata_path.exists():
        return {
            "status": "no_reference_profile",
            "nb_predictions_analyzed": len(records),
            "message": f"Profil de référence introuvable: {metadata_path}. Relancer `python train.py`.",
        }

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    reference_profile = metadata.get("training_reference_profile")
    if not reference_profile:
        return {
            "status": "no_reference_profile",
            "nb_predictions_analyzed": len(records),
            "message": "Les métadonnées du modèle ne contiennent pas de profil de référence. Relancer `python train.py`.",
        }

    input_records = [record.get("input", {}) for record in records]
    input_df = pd.DataFrame(input_records)
    current_features = prepare_prediction_features(
        input_df,
        metadata.get("feature_columns", []),
    )

    numeric_drift = []
    for column, reference_stats in reference_profile.get("numeric_features", {}).items():
        if column not in current_features.columns:
            continue
        current_values = pd.to_numeric(current_features[column], errors="coerce").dropna()
        if current_values.empty:
            continue

        reference_mean = float(reference_stats.get("mean", 0.0))
        reference_std = float(reference_stats.get("std", 0.0))
        current_mean = float(current_values.mean())
        normalized_mean_shift = (
            abs(current_mean - reference_mean) / reference_std
            if reference_std > 0
            else 0.0
        )
        level = _drift_level(
            normalized_mean_shift,
            NUMERIC_DRIFT_WARNING_THRESHOLD,
            NUMERIC_DRIFT_CRITICAL_THRESHOLD,
        )

        numeric_drift.append({
            "feature": column,
            "reference_mean": round(reference_mean, 4),
            "current_mean": round(current_mean, 4),
            "reference_std": round(reference_std, 4),
            "normalized_mean_shift": round(normalized_mean_shift, 4),
            "level": level,
        })

    categorical_drift = []
    for column, reference_stats in reference_profile.get("categorical_features", {}).items():
        if column not in current_features.columns:
            continue
        current_values = current_features[column].dropna().astype(str)
        if current_values.empty:
            continue

        current_distribution = current_values.value_counts(normalize=True).sort_index().to_dict()
        reference_distribution = reference_stats.get("distribution", {})
        distance = _total_variation_distance(reference_distribution, current_distribution)
        level = _drift_level(
            distance,
            CATEGORICAL_DRIFT_WARNING_THRESHOLD,
            CATEGORICAL_DRIFT_CRITICAL_THRESHOLD,
        )
        unknown_categories = sorted(
            set(current_distribution) - set(reference_distribution)
        )

        categorical_drift.append({
            "feature": column,
            "total_variation_distance": round(distance, 4),
            "level": level,
            "unknown_categories": unknown_categories,
            "current_top_values": {
                category: round(float(percentage), 4)
                for category, percentage in list(current_distribution.items())[:5]
            },
        })

    alerts = [
        item for item in [*numeric_drift, *categorical_drift]
        if item["level"] in {"warning", "critical"}
    ]

    nb_predictions = len(records)
    return {
        "status": "ok",
        "nb_predictions_analyzed": nb_predictions,
        "minimum_recommended_sample_size": MIN_MONITORING_SAMPLE_SIZE,
        "sample_size_warning": nb_predictions < MIN_MONITORING_SAMPLE_SIZE,
        "numeric_drift": numeric_drift,
        "categorical_drift": categorical_drift,
        "alerts_count": len(alerts),
        "alerts": alerts,
        "thresholds": {
            "numeric_warning_normalized_shift": NUMERIC_DRIFT_WARNING_THRESHOLD,
            "numeric_critical_normalized_shift": NUMERIC_DRIFT_CRITICAL_THRESHOLD,
            "categorical_warning_tvd": CATEGORICAL_DRIFT_WARNING_THRESHOLD,
            "categorical_critical_tvd": CATEGORICAL_DRIFT_CRITICAL_THRESHOLD,
        },
        "interpretation": (
            "La dérive est indicative tant que le volume de prédictions est faible. "
            "Les alertes signalent des entrées API différentes du profil d'entraînement "
            "et doivent déclencher une revue métier avant réentraînement."
        ),
    }


def build_alert_report(
    log_path: Path = DEFAULT_PREDICTION_LOG_PATH,
    metadata_path: Path = DEFAULT_MODEL_METADATA_PATH,
) -> dict[str, Any]:
    monitoring_report = build_monitoring_report(log_path=log_path)
    drift_report = build_drift_report(log_path=log_path, metadata_path=metadata_path)

    nb_predictions = int(monitoring_report.get("nb_predictions", 0) or 0)
    alerts: list[dict[str, Any]] = []
    recommendations: list[str] = []

    if nb_predictions == 0:
        return {
            "status": "no_data",
            "decision": "collect_predictions",
            "retraining_recommended": False,
            "alerts": [],
            "recommendations": [
                "Collecter des appels `/predict` avant de conclure sur la stabilité du modèle.",
            ],
            "monitoring_summary": monitoring_report,
            "drift_summary": drift_report,
        }

    if nb_predictions < MIN_MONITORING_SAMPLE_SIZE:
        alerts.append({
            "type": "sample_size",
            "level": "warning",
            "message": (
                f"Seulement {nb_predictions} prédiction(s) journalisée(s). "
                f"Minimum recommandé : {MIN_MONITORING_SAMPLE_SIZE}."
            ),
        })
        recommendations.append(
            "Ne pas décider de réentraîner uniquement sur ce volume ; collecter davantage de prédictions."
        )

    low_confidence_rate = monitoring_report.get("low_confidence_rate")
    if low_confidence_rate is not None:
        if low_confidence_rate >= LOW_CONFIDENCE_CRITICAL_RATE:
            alerts.append({
                "type": "confidence",
                "level": "critical",
                "message": (
                    f"Taux de faible confiance critique : {low_confidence_rate} %."
                ),
            })
            recommendations.append(
                "Renforcer la revue humaine et analyser les cas peu confiants avant automatisation."
            )
        elif low_confidence_rate >= LOW_CONFIDENCE_WARNING_RATE:
            alerts.append({
                "type": "confidence",
                "level": "warning",
                "message": (
                    f"Taux de faible confiance élevé : {low_confidence_rate} %."
                ),
            })
            recommendations.append(
                "Surveiller les prédictions peu confiantes et vérifier leur cohérence métier."
            )

    if drift_report.get("status") != "ok":
        alerts.append({
            "type": "drift",
            "level": "warning",
            "message": drift_report.get("message", "Dérive non calculable."),
        })
        recommendations.append(
            "Vérifier la disponibilité du profil de référence avant de conclure sur la dérive."
        )
    elif not drift_report.get("sample_size_warning", False):
        critical_drift_alerts = [
            alert for alert in drift_report.get("alerts", [])
            if alert.get("level") == "critical"
        ]
        warning_drift_alerts = [
            alert for alert in drift_report.get("alerts", [])
            if alert.get("level") == "warning"
        ]

        if critical_drift_alerts:
            alerts.append({
                "type": "drift",
                "level": "critical",
                "message": (
                    f"{len(critical_drift_alerts)} variable(s) en dérive critique."
                ),
                "features": [alert.get("feature") for alert in critical_drift_alerts],
            })
            recommendations.append(
                "Analyser les variables en dérive critique et préparer un réentraînement si la dérive est confirmée métier."
            )
        elif warning_drift_alerts:
            alerts.append({
                "type": "drift",
                "level": "warning",
                "message": (
                    f"{len(warning_drift_alerts)} variable(s) en dérive modérée."
                ),
                "features": [alert.get("feature") for alert in warning_drift_alerts],
            })
            recommendations.append(
                "Surveiller les variables en dérive modérée sur les prochains lots de prédictions."
            )

    has_critical_alert = any(alert["level"] == "critical" for alert in alerts)
    has_warning_alert = any(alert["level"] == "warning" for alert in alerts)
    enough_data = nb_predictions >= MIN_MONITORING_SAMPLE_SIZE
    retraining_recommended = has_critical_alert and enough_data

    if retraining_recommended:
        decision = "review_and_prepare_retraining"
        recommendations.append(
            "Déclencher une revue métier/juridique puis réentraîner avec de nouvelles données annotées si disponibles."
        )
    elif has_warning_alert:
        decision = "monitor_and_review"
    else:
        decision = "no_action"
        recommendations.append(
            "Aucune alerte significative ; poursuivre le suivi périodique."
        )

    return {
        "status": "ok",
        "decision": decision,
        "retraining_recommended": retraining_recommended,
        "requires_human_review": has_warning_alert or has_critical_alert,
        "alerts": alerts,
        "recommendations": list(dict.fromkeys(recommendations)),
        "thresholds": {
            "minimum_sample_size": MIN_MONITORING_SAMPLE_SIZE,
            "low_confidence_warning_rate": LOW_CONFIDENCE_WARNING_RATE,
            "low_confidence_critical_rate": LOW_CONFIDENCE_CRITICAL_RATE,
        },
        "monitoring_summary": monitoring_report,
        "drift_summary": drift_report,
    }


@lru_cache(maxsize=1)
def get_prediction_logger() -> PredictionLogger:
    log_path = Path(
        os.getenv("PREDICTION_LOG_PATH", str(DEFAULT_PREDICTION_LOG_PATH))
    )
    return PredictionLogger(log_path=log_path)

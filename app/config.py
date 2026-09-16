from __future__ import annotations

import copy
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUSINESS_RULES_PATH = PROJECT_ROOT / "configs" / "business_rules.json"

DEFAULT_BUSINESS_RULES: dict[str, Any] = {
    "api_constraints": {
        "duree_jours": {"min": 1, "max": 90},
        "budget_total": {"min": 500, "max": 50000},
        "prix_vol": {"min": 0, "max": 15000},
    },
    "allowed_categories": {
        "client_type": ["famille", "couple", "solo", "business", "senior"],
        "saison": ["hiver", "printemps", "été", "automne"],
        "type_hebergement": ["hôtel", "resort", "appartement", "villa"],
        "meteo_prevue": ["ensoleillé", "nuageux", "pluie", "variable"],
        "activite_principale": [
            "plage",
            "randonnée",
            "gastronomie",
            "culture",
            "business",
        ],
    },
    "feature_engineering": {
        "sejour_long_min_days": 14,
        "meteo_risque_values": ["pluie", "variable"],
        "client_business_value": "business",
        "hebergement_luxe_values": ["resort", "villa"],
    },
    "monitoring": {
        "low_confidence_threshold": 0.5,
        "min_predictions_before_drift": 20,
        "numeric_warning_threshold": 1.0,
        "numeric_critical_threshold": 2.0,
        "categorical_warning_threshold": 0.2,
        "categorical_critical_threshold": 0.35,
        "low_confidence_warning_rate": 40.0,
        "low_confidence_critical_rate": 60.0,
    },
}


def _resolve_config_path(config_path: str | Path | None = None) -> Path:
    selected_path = Path(
        os.getenv("BUSINESS_RULES_PATH")
        or config_path
        or DEFAULT_BUSINESS_RULES_PATH
    )
    if selected_path.is_absolute():
        return selected_path
    return PROJECT_ROOT / selected_path


def _deep_merge(
    default_values: dict[str, Any],
    configured_values: dict[str, Any],
) -> dict[str, Any]:
    merged_values = copy.deepcopy(default_values)
    for key, value in configured_values.items():
        if (
            isinstance(value, dict)
            and isinstance(merged_values.get(key), dict)
        ):
            merged_values[key] = _deep_merge(merged_values[key], value)
        else:
            merged_values[key] = value
    return merged_values


@lru_cache(maxsize=1)
def load_business_rules(config_path: str | Path | None = None) -> dict[str, Any]:
    resolved_path = _resolve_config_path(config_path)
    if not resolved_path.exists():
        return copy.deepcopy(DEFAULT_BUSINESS_RULES)

    try:
        configured_rules = json.loads(resolved_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Configuration métier invalide : {resolved_path}"
        ) from error

    return _deep_merge(DEFAULT_BUSINESS_RULES, configured_rules)


def get_api_constraints() -> dict[str, dict[str, float]]:
    return load_business_rules().get("api_constraints", {})


def get_allowed_categories() -> dict[str, list[str]]:
    return load_business_rules().get("allowed_categories", {})


def get_feature_engineering_rules() -> dict[str, Any]:
    return load_business_rules().get("feature_engineering", {})


def get_monitoring_rules() -> dict[str, float]:
    return load_business_rules().get("monitoring", {})

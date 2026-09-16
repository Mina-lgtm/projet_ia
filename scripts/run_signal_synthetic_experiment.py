from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.modeling import (
    RANDOM_STATE,
    TARGET_COLUMN,
    build_preprocessor,
    candidate_models,
    clean_dataset,
    clip_satisfaction_score,
    prepare_training_dataset,
)


OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic"
OUTPUT_DATASET = OUTPUT_DIR / "travel_planning_signal_dataset.csv"
OUTPUT_REPORT = OUTPUT_DIR / "travel_planning_signal_experiment_report.json"

N_ROWS = 3000

CLIENT_TYPES = ["famille", "couple", "solo", "business", "senior"]
DESTINATIONS = ["paris", "rome", "lisbonne", "bali", "new york", "tokyo", "sydney", "dubaï"]
SAISONS = ["hiver", "printemps", "été", "automne"]
HEBERGEMENTS = ["hôtel", "resort", "appartement", "villa"]
METEO = ["ensoleillé", "nuageux", "pluie", "variable"]
ACTIVITES = ["plage", "randonnée", "gastronomie", "culture", "business"]

DESTINATION_CONTEXT = {
    "paris": {"vol": 350, "budget": 5200},
    "rome": {"vol": 450, "budget": 4300},
    "lisbonne": {"vol": 380, "budget": 3600},
    "bali": {"vol": 1150, "budget": 6200},
    "new york": {"vol": 850, "budget": 7200},
    "tokyo": {"vol": 1050, "budget": 7600},
    "sydney": {"vol": 1300, "budget": 8200},
    "dubaï": {"vol": 700, "budget": 6800},
}

ACTIVITY_MATCH = {
    "famille": {"plage", "culture"},
    "couple": {"culture", "gastronomie", "plage"},
    "solo": {"randonnée", "culture"},
    "business": {"business"},
    "senior": {"culture", "gastronomie"},
}


def sigmoid(value: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-value))


def load_external_context() -> pd.DataFrame:
    weather_path = PROJECT_ROOT / "data" / "external" / "weather_history.csv"
    air_path = PROJECT_ROOT / "data" / "external" / "air_quality_history.csv"

    context = pd.MultiIndex.from_product(
        [DESTINATIONS, SAISONS],
        names=["destination", "saison"],
    ).to_frame(index=False)

    if weather_path.exists():
        weather = pd.read_csv(weather_path)
        context = context.merge(weather, on=["destination", "saison"], how="left")

    if air_path.exists():
        air = pd.read_csv(air_path)
        context = context.merge(air, on=["destination", "saison"], how="left")

    defaults = {
        "temperature_moyenne_saison": 20.0,
        "pluie_moyenne_mm": 2.0,
        "jours_pluie_moyen": 0.25,
        "vent_max_moyen_kmh": 25.0,
        "nb_jours_observes": 90,
        "latitude": 0.0,
        "longitude": 0.0,
        "pm10_moyen": 25.0,
        "pm2_5_moyen": 12.0,
        "european_aqi_moyen": 40.0,
        "uv_index_moyen": 3.0,
        "heures_observees_air": 24 * 90,
    }
    for column, default in defaults.items():
        if column not in context.columns:
            context[column] = default
        context[column] = pd.to_numeric(context[column], errors="coerce").fillna(default)

    for column in ["source", "periode_reference", "source_air_quality", "periode_reference_air_quality"]:
        if column not in context.columns:
            context[column] = "synthetic_context_default"
        context[column] = context[column].fillna("synthetic_context_default")

    return context


def generate_signal_dataset(n_rows: int = N_ROWS, seed: int = RANDOM_STATE) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    context = load_external_context()

    df = pd.DataFrame({
        "trip_id": np.arange(1, n_rows + 1),
        "client_type": rng.choice(CLIENT_TYPES, n_rows, p=[0.25, 0.25, 0.18, 0.17, 0.15]),
        "destination": rng.choice(DESTINATIONS, n_rows),
        "saison": rng.choice(SAISONS, n_rows, p=[0.22, 0.27, 0.31, 0.20]),
        "type_hebergement": rng.choice(HEBERGEMENTS, n_rows, p=[0.42, 0.23, 0.25, 0.10]),
        "activite_principale": rng.choice(ACTIVITES, n_rows),
    })

    df["duree_jours"] = rng.integers(3, 22, n_rows)
    destination_budget = df["destination"].map(lambda value: DESTINATION_CONTEXT[value]["budget"]).astype(float)
    destination_vol = df["destination"].map(lambda value: DESTINATION_CONTEXT[value]["vol"]).astype(float)

    client_budget_factor = df["client_type"].map({
        "famille": 1.15,
        "couple": 1.00,
        "solo": 0.72,
        "business": 1.25,
        "senior": 0.95,
    }).astype(float)
    hebergement_factor = df["type_hebergement"].map({
        "hôtel": 1.00,
        "resort": 1.25,
        "appartement": 0.82,
        "villa": 1.45,
    }).astype(float)

    df["budget_total"] = (
        destination_budget
        * client_budget_factor
        * hebergement_factor
        * rng.normal(1.0, 0.22, n_rows)
    ).clip(500, 50000).round(2)

    df["prix_vol"] = (
        destination_vol
        * rng.normal(1.0, 0.18, n_rows)
        * np.where(df["saison"].eq("été"), 1.18, 1.0)
    ).clip(100, None).round(2)

    meteo_probabilities = {
        "hiver": [0.20, 0.33, 0.27, 0.20],
        "printemps": [0.42, 0.30, 0.12, 0.16],
        "été": [0.62, 0.20, 0.06, 0.12],
        "automne": [0.30, 0.33, 0.17, 0.20],
    }
    df["meteo_prevue"] = [
        rng.choice(METEO, p=meteo_probabilities[saison])
        for saison in df["saison"]
    ]

    df = df.merge(context, on=["destination", "saison"], how="left")

    budget_par_jour = df["budget_total"] / df["duree_jours"]
    part_vol_budget = df["prix_vol"] / df["budget_total"]
    activity_match = np.array([
        row.activite_principale in ACTIVITY_MATCH[row.client_type]
        for row in df[["client_type", "activite_principale"]].itertuples(index=False)
    ])
    meteo_risque = df["meteo_prevue"].isin(["pluie", "variable"]).to_numpy()
    hebergement_luxe = df["type_hebergement"].isin(["resort", "villa"]).to_numpy()
    ideal_temperature_gap = np.abs(df["temperature_moyenne_saison"] - 23.0)

    latent_score = (
        2.65
        + 0.85 * sigmoid((budget_par_jour.to_numpy() - 330) / 85)
        - 1.10 * np.maximum(part_vol_budget.to_numpy() - 0.24, 0) * 4
        + 0.55 * activity_match.astype(float)
        - 0.45 * meteo_risque.astype(float)
        + 0.30 * hebergement_luxe.astype(float)
        - 0.035 * ideal_temperature_gap.to_numpy()
        - 0.010 * np.maximum(df["european_aqi_moyen"].to_numpy() - 45, 0)
        - 0.18 * (df["duree_jours"].to_numpy() >= 16).astype(float)
        + rng.normal(0, 0.42, n_rows)
    )

    df[TARGET_COLUMN] = np.rint(np.clip(latent_score, 1, 5)).astype(int)

    risk_probability = sigmoid(
        -2.0
        + 1.0 * meteo_risque.astype(float)
        + 1.8 * np.maximum(part_vol_budget.to_numpy() - 0.30, 0)
        + 0.8 * (df[TARGET_COLUMN].to_numpy() <= 2).astype(float)
    )
    has_imprevu = rng.random(n_rows) < risk_probability
    imprevu_values = rng.choice(["météo", "retard_vol", "annulation", "bagages"], n_rows)
    df["imprevus"] = np.where(has_imprevu, imprevu_values, "aucun")
    df["reorganisation_necessaire"] = np.where(
        has_imprevu,
        (rng.random(n_rows) < 0.55).astype(int),
        0,
    )
    df["respect_budget"] = (part_vol_budget.to_numpy() <= 0.35).astype(int)

    feedback = {
        1: "très mauvaise expérience.",
        2: "séjour décevant.",
        3: "séjour correct mais perfectible.",
        4: "très bon séjour.",
        5: "excellent séjour.",
    }
    df["retour_client"] = df[TARGET_COLUMN].map(feedback)

    return df


def evaluate_regression(df: pd.DataFrame) -> list[dict[str, Any]]:
    x, y, _ = prepare_training_dataset(df)
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y.astype(int),
    )
    preprocess, _, _ = build_preprocessor(x_train)
    rows = []
    for model_name, model in candidate_models().items():
        pipeline = Pipeline(steps=[
            ("preprocess", clone(preprocess)),
            ("model", model),
        ])
        pipeline.fit(x_train, y_train)
        predictions = clip_satisfaction_score(pipeline.predict(x_test))
        rows.append({
            "modele": model_name,
            "mae": round(float(mean_absolute_error(y_test, predictions)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_test, predictions))), 4),
            "r2": round(float(r2_score(y_test, predictions)), 4),
        })

    return (
        pd.DataFrame(rows)
        .sort_values(["mae", "rmse"], ascending=[True, True])
        .to_dict(orient="records")
    )


def evaluate_binary_classification(df: pd.DataFrame) -> list[dict[str, Any]]:
    x, y, _ = prepare_training_dataset(df)
    y_binary = (y >= 4).astype(int)
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y_binary,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y_binary,
    )
    preprocess, _, _ = build_preprocessor(x_train)
    models = {
        "Dummy_majority_binary": DummyClassifier(strategy="most_frequent"),
        "LogisticRegression_balanced": LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "RandomForest_balanced": RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=8,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=1,
        ),
    }

    rows = []
    for model_name, model in models.items():
        pipeline = Pipeline(steps=[
            ("preprocess", clone(preprocess)),
            ("model", model),
        ])
        pipeline.fit(x_train, y_train)
        predictions = pipeline.predict(x_test)
        probabilities = (
            pipeline.predict_proba(x_test)[:, 1]
            if hasattr(pipeline, "predict_proba")
            else np.zeros(len(y_test))
        )
        rows.append({
            "modele": model_name,
            "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
            "balanced_accuracy": round(float(balanced_accuracy_score(y_test, predictions)), 4),
            "precision_1": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
            "recall_1": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
            "f1_1": round(float(f1_score(y_test, predictions, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        })

    return (
        pd.DataFrame(rows)
        .sort_values(["f1_1", "roc_auc"], ascending=[False, False])
        .to_dict(orient="records")
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_signal_dataset()
    df_clean, cleaning_report = clean_dataset(df)

    df.to_csv(OUTPUT_DATASET, index=False, encoding="utf-8")
    regression_results = evaluate_regression(df)
    binary_results = evaluate_binary_classification(df)

    report = {
        "dataset": str(OUTPUT_DATASET.relative_to(PROJECT_ROOT)),
        "rows_generated": int(len(df)),
        "rows_after_cleaning": int(len(df_clean)),
        "target_distribution": {
            str(key): int(value)
            for key, value in df[TARGET_COLUMN].value_counts().sort_index().items()
        },
        "positive_binary_rate_satisfaction_4_5": round(float((df[TARGET_COLUMN] >= 4).mean()), 4),
        "signal_design": [
            "budget_par_jour élevé augmente la satisfaction",
            "part_vol_budget élevée diminue la satisfaction",
            "adéquation client_type / activite_principale augmente la satisfaction",
            "météo risquée diminue la satisfaction",
            "hébergement luxe augmente la satisfaction si le budget suit",
            "qualité de l'air et météo historique réelle influencent légèrement la satisfaction",
        ],
        "cleaning_report": cleaning_report,
        "regression_results": regression_results,
        "binary_classification_results": binary_results,
    }
    OUTPUT_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Dataset généré : {OUTPUT_DATASET.relative_to(PROJECT_ROOT)}")
    print(f"Rapport généré : {OUTPUT_REPORT.relative_to(PROJECT_ROOT)}")
    print("\nDistribution satisfaction :")
    print(pd.Series(report["target_distribution"]))
    print("\nRésultats régression :")
    print(pd.DataFrame(regression_results).to_string(index=False))
    print("\nRésultats classification binaire satisfaction >= 4 :")
    print(pd.DataFrame(binary_results).to_string(index=False))


if __name__ == "__main__":
    main()

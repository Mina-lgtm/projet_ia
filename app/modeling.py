from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.config import get_api_constraints, get_feature_engineering_rules


RANDOM_STATE = 42
SOLUTION_NAME = "TravelMind"
TARGET_COLUMN = "satisfaction_client"
SATISFACTION_MIN = 1.0
SATISFACTION_MAX = 5.0

FEATURES_SUPPRIMEES_MODELISATION = [
    "budget_hors_vol",
    "region_destination",
    "distance_vol_categorie",
    "destination_luxe",
    "budget_non_respecte",
    "budget_tendu",
    "gravite_imprevu",
    "source",
    "periode_reference",
    "source_air_quality",
    "periode_reference_air_quality",
    "source_tarifaire",
    "periode_reference_tarifaire",
]

FEATURES_POST_VOYAGE_EXPLICATIVES = [
    "imprevu_present",
    "imprevu_transport",
    "imprevu_meteo",
]

POST_TRIP_COLUMNS = [
    "imprevus",
    "reorganisation_necessaire",
    "respect_budget",
    "retour_client",
    *FEATURES_POST_VOYAGE_EXPLICATIVES,
]

PRE_VOYAGE_INPUT_COLUMNS = [
    "client_type",
    "budget_total",
    "destination",
    "saison",
    "duree_jours",
    "type_hebergement",
    "prix_vol",
    "meteo_prevue",
    "activite_principale",
]


@dataclass(frozen=True)
class TrainingResult:
    model_name: str
    pipeline: Pipeline
    metrics: dict[str, float]
    feature_columns: list[str]
    numeric_features: list[str]
    categorical_features: list[str]
    evaluation_results: list[dict[str, Any]]
    residual_summary: dict[str, float]
    cleaning_report: list[dict[str, Any]]
    reference_profile: dict[str, Any]


class IQRMedianOutlierReplacer(BaseEstimator, TransformerMixin):
    """Remplace les outliers IQR par la médiane apprise sur le train."""

    def __init__(self, factor: float = 1.5):
        self.factor = factor

    def fit(self, X, y=None):
        x_array = np.asarray(X, dtype=float)
        self.q1_ = np.nanquantile(x_array, 0.25, axis=0)
        self.q3_ = np.nanquantile(x_array, 0.75, axis=0)
        self.iqr_ = self.q3_ - self.q1_
        self.lower_bounds_ = self.q1_ - self.factor * self.iqr_
        self.upper_bounds_ = self.q3_ + self.factor * self.iqr_
        self.medians_ = np.nanmedian(x_array, axis=0)
        return self

    def transform(self, X):
        x_array = np.asarray(X, dtype=float).copy()
        outlier_mask = (x_array < self.lower_bounds_) | (x_array > self.upper_bounds_)
        return np.where(outlier_mask, self.medians_, x_array)

    def get_feature_names_out(self, input_features=None):
        if input_features is None:
            return np.asarray([f"x{i}" for i in range(len(self.medians_))], dtype=object)
        return np.asarray(input_features, dtype=object)


def clean_dataset(df_source: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    df = df_source.copy()
    nb_initial = len(df)

    for column in df.select_dtypes(include=["object", "string"]).columns:
        cleaned_column = (
            df[column]
            .astype("string")
            .str.strip()
            .str.lower()
            .replace({"": np.nan, "nan": np.nan})
        )
        df[column] = cleaned_column.mask(cleaned_column.isna(), np.nan).astype(object)

    numeric_source_columns = [
        "budget_total",
        "duree_jours",
        "prix_vol",
        TARGET_COLUMN,
        "reorganisation_necessaire",
        "respect_budget",
    ]
    for column in numeric_source_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if "trip_id" in df.columns:
        df = df.drop_duplicates(subset=["trip_id"], keep="first").copy()
    nb_after_trip_id = len(df)

    df = df[df[TARGET_COLUMN].between(1, 5)].copy()
    nb_after_target = len(df)
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)

    business_constraints_mask = pd.Series(True, index=df.index)
    for column, constraints in get_api_constraints().items():
        if column not in df.columns:
            continue
        min_value = constraints.get("min")
        max_value = constraints.get("max")
        column_values = pd.to_numeric(df[column], errors="coerce")
        non_missing_valid_mask = pd.Series(True, index=df.index)
        if min_value is not None:
            non_missing_valid_mask &= column_values >= min_value
        if max_value is not None:
            non_missing_valid_mask &= column_values <= max_value
        column_mask = column_values.isna() | non_missing_valid_mask
        business_constraints_mask &= column_mask

    df = df[business_constraints_mask].copy()
    nb_after_business_constraints = len(df)

    budget_valid_mask = (
        df["prix_vol"].isna()
        | df["budget_total"].isna()
        | (df["prix_vol"] <= df["budget_total"])
    )
    df = df[budget_valid_mask].copy()
    nb_after_budget = len(df)

    imprevus_norm = (
        df["imprevus"]
        .fillna("aucun")
        .astype("string")
        .str.strip()
        .str.lower()
        .replace({"": "aucun", "nan": "aucun"})
    )
    aucun_imprevu_mais_reorganisation_mask = (
        (imprevus_norm == "aucun")
        & (df["reorganisation_necessaire"] == 1)
    )
    df = df[~aucun_imprevu_mais_reorganisation_mask].copy()
    nb_after_incoherences_metier = len(df)

    df["imprevus"] = df["imprevus"].fillna("aucun").replace({"nan": "aucun"})
    df["retour_client"] = df["retour_client"].fillna("").replace({"nan": ""})

    cleaning_report = [
        {
            "etape": "dataset_brut",
            "nb_lignes": nb_initial,
            "lignes_supprimees": 0,
        },
        {
            "etape": "unicite_trip_id",
            "nb_lignes": nb_after_trip_id,
            "lignes_supprimees": nb_initial - nb_after_trip_id,
        },
        {
            "etape": "cible_satisfaction_client_valide",
            "nb_lignes": nb_after_target,
            "lignes_supprimees": nb_after_trip_id - nb_after_target,
        },
        {
            "etape": "contraintes_metier_config",
            "nb_lignes": nb_after_business_constraints,
            "lignes_supprimees": nb_after_target - nb_after_business_constraints,
        },
        {
            "etape": "coherence_initiale_prix_vol_budget_total",
            "nb_lignes": nb_after_budget,
            "lignes_supprimees": nb_after_business_constraints - nb_after_budget,
        },
        {
            "etape": "reorganisation_sans_imprevu_declare",
            "nb_lignes": nb_after_incoherences_metier,
            "lignes_supprimees": nb_after_budget - nb_after_incoherences_metier,
        },
    ]

    return df, cleaning_report


def add_base_features(df_source: pd.DataFrame) -> pd.DataFrame:
    df = df_source.copy()
    feature_rules = get_feature_engineering_rules()
    sejour_long_min_days = int(feature_rules.get("sejour_long_min_days", 14))
    meteo_risque_values = set(feature_rules.get("meteo_risque_values", ["pluie", "variable"]))
    client_business_value = str(feature_rules.get("client_business_value", "business"))
    hebergement_luxe_values = set(
        feature_rules.get("hebergement_luxe_values", ["resort", "villa"])
    )

    for column in [
        *PRE_VOYAGE_INPUT_COLUMNS,
        "imprevus",
        "reorganisation_necessaire",
        "respect_budget",
        "retour_client",
    ]:
        if column not in df.columns:
            df[column] = np.nan

    safe_duree = df["duree_jours"].replace(0, np.nan)
    safe_budget = df["budget_total"].replace(0, np.nan)

    def indicateur(condition: pd.Series, missing_mask: pd.Series) -> pd.Series:
        return pd.Series(
            np.where(missing_mask, np.nan, condition.astype(int)),
            index=df.index,
        )

    df["budget_par_jour"] = df["budget_total"] / safe_duree
    df["part_vol_budget"] = df["prix_vol"] / safe_budget
    df["sejour_long"] = indicateur(
        df["duree_jours"] >= sejour_long_min_days,
        df["duree_jours"].isna(),
    )
    df["meteo_risque"] = indicateur(
        df["meteo_prevue"].isin(meteo_risque_values),
        df["meteo_prevue"].isna(),
    )
    df["client_business"] = indicateur(
        df["client_type"] == client_business_value,
        df["client_type"].isna(),
    )
    df["hebergement_luxe"] = indicateur(
        df["type_hebergement"].isin(hebergement_luxe_values),
        df["type_hebergement"].isna(),
    )

    df["imprevu_present"] = indicateur(df["imprevus"] != "aucun", df["imprevus"].isna())
    df["imprevu_transport"] = indicateur(
        df["imprevus"].isin(["retard_vol", "annulation", "bagages"]),
        df["imprevus"].isna(),
    )
    df["imprevu_meteo"] = indicateur(
        df["imprevus"].isin(["météo", "meteo"]),
        df["imprevus"].isna(),
    )
    for column in ["budget_par_jour", "part_vol_budget"]:
        df[column] = df[column].replace([np.inf, -np.inf], np.nan)

    for column in df.select_dtypes(include=["object", "string"]).columns:
        df[column] = df[column].mask(df[column].isna(), np.nan).astype(object)

    return df.drop(columns=FEATURES_SUPPRIMEES_MODELISATION, errors="ignore")


def satisfaction_to_3_classes(value: int) -> int:
    if value <= 2:
        return 0
    if value == 3:
        return 1
    return 2


def clip_satisfaction_score(values: Any) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), SATISFACTION_MIN, SATISFACTION_MAX)


def prepare_training_dataset(
    df_source: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, list[dict[str, Any]]]:
    df_clean, cleaning_report = clean_dataset(df_source)
    df_model = add_base_features(df_clean)

    excluded_columns = [
        "trip_id",
        TARGET_COLUMN,
        *FEATURES_SUPPRIMEES_MODELISATION,
        *POST_TRIP_COLUMNS,
    ]
    feature_columns = [
        column for column in df_model.columns
        if column not in excluded_columns
    ]

    x = df_model[feature_columns].copy()
    y = df_model[TARGET_COLUMN].astype(float)

    return x, y, cleaning_report


def prepare_prediction_features(
    df_source: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    df_model = add_base_features(df_source)
    return df_model.reindex(columns=feature_columns)


def build_reference_profile(
    x_train: pd.DataFrame,
    numeric_features: list[str],
    categorical_features: list[str],
) -> dict[str, Any]:
    numeric_profile = {}
    for column in numeric_features:
        values = pd.to_numeric(x_train[column], errors="coerce").dropna()
        if values.empty:
            continue
        numeric_profile[column] = {
            "count": int(values.shape[0]),
            "mean": float(values.mean()),
            "std": float(values.std(ddof=0)),
            "min": float(values.min()),
            "p25": float(values.quantile(0.25)),
            "median": float(values.median()),
            "p75": float(values.quantile(0.75)),
            "max": float(values.max()),
        }

    categorical_profile = {}
    for column in categorical_features:
        values = x_train[column].dropna().astype(str)
        if values.empty:
            continue
        distribution = values.value_counts(normalize=True).sort_index()
        categorical_profile[column] = {
            "count": int(values.shape[0]),
            "distribution": {
                str(category): float(percentage)
                for category, percentage in distribution.items()
            },
        }

    return {
        "created_from": "train_split",
        "n_rows": int(x_train.shape[0]),
        "numeric_features": numeric_profile,
        "categorical_features": categorical_profile,
    }


def detect_binary_numeric_features(
    x: pd.DataFrame,
    numeric_features: list[str],
) -> list[str]:
    binary_features = []
    for column in numeric_features:
        values = pd.Series(x[column].dropna().unique())
        if values.empty:
            continue
        try:
            unique_values = set(values.astype(float).tolist())
        except (TypeError, ValueError):
            continue
        if unique_values.issubset({0.0, 1.0}):
            binary_features.append(column)
    return binary_features


def build_preprocessor(x_train: pd.DataFrame) -> tuple[ColumnTransformer, list[str], list[str]]:
    numeric_features = x_train.select_dtypes(include="number").columns.tolist()
    categorical_features = x_train.select_dtypes(
        include=["object", "string", "category"],
    ).columns.tolist()

    binary_numeric_features = detect_binary_numeric_features(x_train, numeric_features)
    continuous_numeric_features = [
        column for column in numeric_features
        if column not in binary_numeric_features
    ]

    continuous_numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("outliers_iqr", IQRMedianOutlierReplacer()),
        ("scaler", StandardScaler()),
    ])

    binary_numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    transformers = []
    if continuous_numeric_features:
        transformers.append(("num_cont", continuous_numeric_transformer, continuous_numeric_features))
    if binary_numeric_features:
        transformers.append(("num_bin", binary_numeric_transformer, binary_numeric_features))
    if categorical_features:
        transformers.append(("cat", categorical_transformer, categorical_features))

    preprocess = ColumnTransformer(transformers=transformers)

    return preprocess, numeric_features, categorical_features


def candidate_models() -> dict[str, Any]:
    return {
        "Dummy_mean_regression": DummyRegressor(strategy="mean"),
        "LinearRegression_pre": LinearRegression(),
        "RidgeRegression_pre": Ridge(alpha=1.0),
        "RandomForestRegressor_pre": RandomForestRegressor(
            n_estimators=120,
            max_depth=8,
            random_state=RANDOM_STATE,
            n_jobs=1,
        ),
    }


def train_and_select_model(
    x: pd.DataFrame,
    y: pd.Series,
    cleaning_report: list[dict[str, Any]],
    test_size: float = 0.2,
) -> TrainingResult:
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=RANDOM_STATE,
        stratify=y.astype(int),
    )

    preprocess, numeric_features, categorical_features = build_preprocessor(x_train)
    rows = []
    fitted: dict[str, Pipeline] = {}

    for model_name, model in candidate_models().items():
        pipeline = Pipeline(steps=[
            ("preprocess", clone(preprocess)),
            ("model", model),
        ])
        pipeline.fit(x_train, y_train)
        predictions = clip_satisfaction_score(pipeline.predict(x_test))

        rows.append({
            "modele": model_name,
            "mae": mean_absolute_error(y_test, predictions),
            "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
            "r2": r2_score(y_test, predictions),
            "prediction_min": float(np.min(predictions)),
            "prediction_max": float(np.max(predictions)),
        })
        fitted[model_name] = pipeline

    results = (
        pd.DataFrame(rows)
        .sort_values(["mae", "rmse"], ascending=[True, True])
        .reset_index(drop=True)
    )

    best_model_name = str(results.iloc[0]["modele"])
    best_pipeline = fitted[best_model_name]
    best_predictions = clip_satisfaction_score(best_pipeline.predict(x_test))
    best_row = results.iloc[0]
    residuals = np.asarray(y_test, dtype=float) - best_predictions
    baseline_row = results[results["modele"] == "Dummy_mean_regression"].iloc[0]

    metrics = {
        "mae": float(best_row["mae"]),
        "rmse": float(best_row["rmse"]),
        "r2": float(best_row["r2"]),
        "baseline_mae": float(baseline_row["mae"]),
        "mae_gain_vs_baseline": float(baseline_row["mae"] - best_row["mae"]),
        "test_size": float(test_size),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
    }

    return TrainingResult(
        model_name=best_model_name,
        pipeline=best_pipeline,
        metrics=metrics,
        feature_columns=x.columns.tolist(),
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        evaluation_results=results.to_dict(orient="records"),
        residual_summary={
            "residual_mean": float(np.mean(residuals)),
            "residual_std": float(np.std(residuals)),
            "residual_min": float(np.min(residuals)),
            "residual_max": float(np.max(residuals)),
        },
        cleaning_report=cleaning_report,
        reference_profile=build_reference_profile(
            x_train,
            numeric_features,
            categorical_features,
        ),
    )


def save_training_artifacts(
    result: TrainingResult,
    model_path: Path,
    metadata_path: Path,
) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(result.pipeline, model_path)

    metadata = {
        "solution_name": SOLUTION_NAME,
        "display_model_name": "TravelMind Pre-Voyage Satisfaction Model",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "objective": "pre_voyage_satisfaction_score_regression",
        "model_name": result.model_name,
        "target": TARGET_COLUMN,
        "target_type": "regression",
        "prediction_scale": {
            "min": SATISFACTION_MIN,
            "max": SATISFACTION_MAX,
            "unit": "score_satisfaction_1_5",
        },
        "metrics": result.metrics,
        "feature_columns": result.feature_columns,
        "numeric_features": result.numeric_features,
        "categorical_features": result.categorical_features,
        "pre_voyage_input_columns": PRE_VOYAGE_INPUT_COLUMNS,
        "post_voyage_features_excluded": POST_TRIP_COLUMNS,
        "removed_features": FEATURES_SUPPRIMEES_MODELISATION,
        "evaluation_results": result.evaluation_results,
        "residual_summary": result.residual_summary,
        "cleaning_report": result.cleaning_report,
        "training_reference_profile": result.reference_profile,
    }

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

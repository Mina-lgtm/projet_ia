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
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


RANDOM_STATE = 42
TARGET_COLUMN = "satisfaction_client"
CLASS_LABELS = [0, 1, 2]
CLASS_NAMES = ["insatisfait_1_2", "neutre_3", "satisfait_4_5"]

FEATURES_SUPPRIMEES_MODELISATION = [
    "budget_hors_vol",
]

FEATURES_POST_VOYAGE_EXPLICATIVES = [
    "imprevus",
    "reorganisation_necessaire",
    "respect_budget",
    "imprevu_present",
    "imprevu_transport",
    "imprevu_meteo",
    "budget_non_respecte",
    "budget_tendu",
    "gravite_imprevu",
]

POST_TRIP_COLUMNS = [
    "imprevus",
    "reorganisation_necessaire",
    "respect_budget",
    "retour_client",
    *FEATURES_POST_VOYAGE_EXPLICATIVES[3:],
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
    confusion_matrix: list[list[int]]
    classification_report: dict[str, Any]
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

    df = df[df[TARGET_COLUMN].between(1, 5)].copy()
    nb_after_target = len(df)
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)

    budget_valid_mask = (
        df["prix_vol"].isna()
        | df["budget_total"].isna()
        | (df["prix_vol"] <= df["budget_total"])
    )
    df = df[budget_valid_mask].copy()
    nb_after_budget = len(df)

    imprevus_norm = df["imprevus"].fillna("").astype("string").str.strip().str.lower()
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
            "etape": "cible_satisfaction_client_valide",
            "nb_lignes": nb_after_target,
            "lignes_supprimees": nb_initial - nb_after_target,
        },
        {
            "etape": "coherence_initiale_prix_vol_budget_total",
            "nb_lignes": nb_after_budget,
            "lignes_supprimees": nb_after_target - nb_after_budget,
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
    df["budget_hors_vol"] = df["budget_total"] - df["prix_vol"]
    df["sejour_long"] = indicateur(df["duree_jours"] >= 14, df["duree_jours"].isna())
    df["meteo_risque"] = indicateur(
        df["meteo_prevue"].isin(["pluie", "variable"]),
        df["meteo_prevue"].isna(),
    )
    df["client_business"] = indicateur(
        df["client_type"] == "business",
        df["client_type"].isna(),
    )
    df["hebergement_luxe"] = indicateur(
        df["type_hebergement"].isin(["resort", "villa"]),
        df["type_hebergement"].isna(),
    )

    destination_enrichment = pd.DataFrame({
        "destination": [
            "paris",
            "rome",
            "lisbonne",
            "new york",
            "dubai",
            "tokyo",
            "bali",
            "sydney",
        ],
        "region_destination": [
            "europe",
            "europe",
            "europe",
            "amerique du nord",
            "moyen-orient",
            "asie",
            "asie",
            "oceanie",
        ],
        "distance_vol_categorie": [
            "court",
            "court",
            "court",
            "long",
            "moyen",
            "long",
            "long",
            "long",
        ],
        "destination_luxe": [1, 1, 0, 1, 1, 1, 1, 1],
    })

    df = df.merge(destination_enrichment, on="destination", how="left", validate="many_to_one")

    for column in ["region_destination", "distance_vol_categorie"]:
        if df[column].isna().any():
            df[column] = df[column].fillna("inconnu")

    df["imprevu_present"] = indicateur(df["imprevus"] != "aucun", df["imprevus"].isna())
    df["imprevu_transport"] = indicateur(
        df["imprevus"].isin(["retard_vol", "annulation", "bagages"]),
        df["imprevus"].isna(),
    )
    df["imprevu_meteo"] = indicateur(
        df["imprevus"].isin(["météo", "meteo"]),
        df["imprevus"].isna(),
    )
    df["budget_non_respecte"] = indicateur(
        df["respect_budget"] == 0,
        df["respect_budget"].isna(),
    )
    df["gravite_imprevu"] = df["imprevus"].map({
        "aucun": 0,
        "meteo": 1,
        "météo": 1,
        "bagages": 1,
        "retard_vol": 2,
        "annulation": 3,
    })
    df["budget_tendu"] = indicateur(
        df["part_vol_budget"] >= 0.5,
        df["part_vol_budget"].isna(),
    )

    for column in ["budget_par_jour", "part_vol_budget", "budget_hors_vol"]:
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
    y = df_model[TARGET_COLUMN].apply(satisfaction_to_3_classes).astype(int)

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
        "Dummy_majority_pre": DummyClassifier(strategy="most_frequent"),
        "LogisticRegression_pre": LogisticRegression(
            max_iter=500,
            class_weight="balanced",
        ),
        "RandomForest_pre": RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            random_state=RANDOM_STATE,
            class_weight="balanced",
            n_jobs=1,
        ),
        "ExtraTrees_pre": ExtraTreesClassifier(
            n_estimators=120,
            max_depth=8,
            random_state=RANDOM_STATE,
            class_weight="balanced",
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
        stratify=y,
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
        predictions = pipeline.predict(x_test)

        rows.append({
            "modele": model_name,
            "accuracy": accuracy_score(y_test, predictions),
            "balanced_accuracy": balanced_accuracy_score(y_test, predictions),
            "macro_f1": f1_score(y_test, predictions, average="macro"),
        })
        fitted[model_name] = pipeline

    results = (
        pd.DataFrame(rows)
        .sort_values("macro_f1", ascending=False)
        .reset_index(drop=True)
    )

    best_model_name = str(results.iloc[0]["modele"])
    best_pipeline = fitted[best_model_name]
    best_predictions = best_pipeline.predict(x_test)
    best_row = results.iloc[0]

    metrics = {
        "accuracy": float(best_row["accuracy"]),
        "balanced_accuracy": float(best_row["balanced_accuracy"]),
        "macro_f1": float(best_row["macro_f1"]),
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
        confusion_matrix=confusion_matrix(
            y_test,
            best_predictions,
            labels=CLASS_LABELS,
        ).tolist(),
        classification_report=classification_report(
            y_test,
            best_predictions,
            labels=CLASS_LABELS,
            target_names=CLASS_NAMES,
            output_dict=True,
            zero_division=0,
        ),
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
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "objective": "pre_voyage_satisfaction_3_classes",
        "model_name": result.model_name,
        "target": TARGET_COLUMN,
        "class_labels": CLASS_LABELS,
        "class_names": CLASS_NAMES,
        "metrics": result.metrics,
        "feature_columns": result.feature_columns,
        "numeric_features": result.numeric_features,
        "categorical_features": result.categorical_features,
        "pre_voyage_input_columns": PRE_VOYAGE_INPUT_COLUMNS,
        "post_voyage_features_excluded": POST_TRIP_COLUMNS,
        "removed_features": FEATURES_SUPPRIMEES_MODELISATION,
        "confusion_matrix": result.confusion_matrix,
        "classification_report": result.classification_report,
        "cleaning_report": result.cleaning_report,
        "training_reference_profile": result.reference_profile,
    }

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

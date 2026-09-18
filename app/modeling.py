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
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.config import get_api_constraints, get_feature_engineering_rules


RANDOM_STATE = 42
SOLUTION_NAME = "TravelMind"
TARGET_COLUMN = "satisfaction_client"
POSITIVE_CLASS = 1
CLASS_LABELS = [0, 1]
CLASS_NAMES = {
    0: "non_satisfait_1_2_3",
    1: "satisfait_4_5",
}

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

DATASET_FINAL_COLUMNS = [
    "trip_id",
    "client_type",
    "budget_total",
    "destination",
    "saison",
    "duree_jours",
    "type_hebergement",
    "prix_vol",
    "meteo_prevue",
    "activite_principale",
    TARGET_COLUMN,
    "imprevus",
    "reorganisation_necessaire",
    "respect_budget",
    "retour_client",
    "reste_budget_apres_vol",
    "budget_apres_vol_par_jour",
    "score_budget_destination",
    "score_prix_vol_coherent",
    "score_adequation_activite_profil",
    "score_meteo_prevue",
    "score_contexte_destination",
    "score_potentiel_satisfaction",
    "niveau_risque_satisfaction",
]

DESTINATION_REFERENCE = {
    "paris": {"budget": 4200, "vol": 350, "complexite": 0.20},
    "rome": {"budget": 3900, "vol": 450, "complexite": 0.25},
    "lisbonne": {"budget": 3400, "vol": 380, "complexite": 0.20},
    "bali": {"budget": 6200, "vol": 1150, "complexite": 0.75},
    "new york": {"budget": 6500, "vol": 850, "complexite": 0.55},
    "tokyo": {"budget": 7200, "vol": 1050, "complexite": 0.80},
    "sydney": {"budget": 8000, "vol": 1300, "complexite": 0.95},
    "duba\u00ef": {"budget": 6100, "vol": 700, "complexite": 0.45},
}

ACTIVITIES_BY_CLIENT = {
    "famille": {"plage", "culture", "gastronomie"},
    "couple": {"culture", "gastronomie", "plage"},
    "solo": {"randonn\u00e9e", "culture"},
    "business": {"business"},
    "senior": {"culture", "gastronomie"},
}

HEBERGEMENTS_BY_CLIENT = {
    "famille": {"resort", "appartement", "villa"},
    "couple": {"h\u00f4tel", "resort", "villa"},
    "solo": {"appartement", "h\u00f4tel"},
    "business": {"h\u00f4tel"},
    "senior": {"h\u00f4tel", "appartement"},
}

METEO_SCORE = {
    "ensoleill\u00e9": 1.00,
    "nuageux": 0.70,
    "variable": 0.45,
    "pluie": 0.25,
}


@dataclass(frozen=True)
class TrainingResult:
    model_name: str
    pipeline: Pipeline
    metrics: dict[str, float]
    feature_columns: list[str]
    numeric_features: list[str]
    categorical_features: list[str]
    evaluation_results: list[dict[str, Any]]
    confusion_matrix: list[list[int]]
    cleaning_report: list[dict[str, Any]]
    reference_profile: dict[str, Any]


class IQRMedianOutlierReplacer(BaseEstimator, TransformerMixin):
    """Remplace les outliers IQR par la mediane apprise sur le train."""

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


def satisfaction_to_binary(value: int | float) -> int:
    return int(float(value) >= 4)


def numeric_series(df: pd.DataFrame, column: str, default: float = np.nan) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce")
    return pd.Series(default, index=df.index, dtype="float64")


def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    ratio = pd.to_numeric(numerator, errors="coerce") / pd.to_numeric(denominator, errors="coerce")
    return ratio.replace([np.inf, -np.inf], np.nan)


def normalize_0_1(values: pd.Series, lower: float, upper: float, inverse: bool = False) -> pd.Series:
    normalized = ((pd.to_numeric(values, errors="coerce") - lower) / (upper - lower)).clip(0, 1)
    if inverse:
        normalized = 1 - normalized
    return normalized.fillna(0.5)


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
        df[column] = cleaned_column.astype(object).where(~cleaned_column.isna(), np.nan)

    for column in [
        "budget_total",
        "duree_jours",
        "prix_vol",
        TARGET_COLUMN,
        "reorganisation_necessaire",
        "respect_budget",
    ]:
        if column not in df.columns:
            df[column] = np.nan
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
        column_mask = column_values.isna()
        valid_mask = pd.Series(True, index=df.index)
        if min_value is not None:
            valid_mask &= column_values >= min_value
        if max_value is not None:
            valid_mask &= column_values <= max_value
        business_constraints_mask &= column_mask | valid_mask

    df = df[business_constraints_mask].copy()
    nb_after_business_constraints = len(df)

    budget_valid_mask = (
        df["prix_vol"].isna()
        | df["budget_total"].isna()
        | (df["prix_vol"] <= df["budget_total"])
    )
    df = df[budget_valid_mask].copy()
    nb_after_budget = len(df)

    if "imprevus" not in df.columns:
        df["imprevus"] = "aucun"
    if "retour_client" not in df.columns:
        df["retour_client"] = ""

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
        {"etape": "dataset_brut", "nb_lignes": nb_initial, "lignes_supprimees": 0},
        {"etape": "unicite_trip_id", "nb_lignes": nb_after_trip_id, "lignes_supprimees": nb_initial - nb_after_trip_id},
        {"etape": "cible_satisfaction_client_valide", "nb_lignes": nb_after_target, "lignes_supprimees": nb_after_trip_id - nb_after_target},
        {"etape": "contraintes_metier_config", "nb_lignes": nb_after_business_constraints, "lignes_supprimees": nb_after_target - nb_after_business_constraints},
        {"etape": "coherence_initiale_prix_vol_budget_total", "nb_lignes": nb_after_budget, "lignes_supprimees": nb_after_business_constraints - nb_after_budget},
        {"etape": "reorganisation_sans_imprevu_declare", "nb_lignes": nb_after_incoherences_metier, "lignes_supprimees": nb_after_budget - nb_after_incoherences_metier},
    ]
    return df, cleaning_report


def add_base_features(df_source: pd.DataFrame) -> pd.DataFrame:
    df = df_source.copy()
    feature_rules = get_feature_engineering_rules()
    sejour_long_min_days = int(feature_rules.get("sejour_long_min_days", 14))
    meteo_risque_values = set(feature_rules.get("meteo_risque_values", ["pluie", "variable"]))
    client_business_value = str(feature_rules.get("client_business_value", "business"))
    hebergement_luxe_values = set(feature_rules.get("hebergement_luxe_values", ["resort", "villa"]))

    for column in [*PRE_VOYAGE_INPUT_COLUMNS, *POST_TRIP_COLUMNS, TARGET_COLUMN]:
        if column not in df.columns:
            df[column] = np.nan

    for column in ["client_type", "destination", "saison", "type_hebergement", "meteo_prevue", "activite_principale", "imprevus"]:
        df[column] = df[column].astype("string").str.strip().str.lower().replace({"": np.nan, "nan": np.nan})

    df["budget_total"] = numeric_series(df, "budget_total")
    df["prix_vol"] = numeric_series(df, "prix_vol")
    df["duree_jours"] = numeric_series(df, "duree_jours", default=7).fillna(7).clip(lower=1)

    safe_duree = df["duree_jours"].replace(0, np.nan)
    safe_budget = df["budget_total"].replace(0, np.nan)

    def indicateur(condition: pd.Series, missing_mask: pd.Series) -> pd.Series:
        safe_condition = condition.fillna(False).astype(bool)
        safe_missing_mask = missing_mask.fillna(True).astype(bool)
        return pd.Series(np.where(safe_missing_mask, np.nan, safe_condition.astype(int)), index=df.index)

    df["budget_par_jour"] = df["budget_total"] / safe_duree
    df["part_vol_budget"] = df["prix_vol"] / safe_budget
    df["sejour_long"] = indicateur(df["duree_jours"] >= sejour_long_min_days, df["duree_jours"].isna())
    df["meteo_risque"] = indicateur(df["meteo_prevue"].isin(meteo_risque_values), df["meteo_prevue"].isna())
    df["client_business"] = indicateur(df["client_type"] == client_business_value, df["client_type"].isna())
    df["hebergement_luxe"] = indicateur(df["type_hebergement"].isin(hebergement_luxe_values), df["type_hebergement"].isna())

    budget_reference = df["destination"].map(lambda value: DESTINATION_REFERENCE.get(str(value), {}).get("budget", np.nan))
    vol_reference = df["destination"].map(lambda value: DESTINATION_REFERENCE.get(str(value), {}).get("vol", np.nan))
    reste_budget_apres_vol = df["budget_total"] - df["prix_vol"]
    budget_apres_vol_par_jour = safe_ratio(reste_budget_apres_vol, df["duree_jours"].replace(0, np.nan))
    ratio_budget_reference_destination = safe_ratio(df["budget_total"], budget_reference)
    ratio_prix_vol_reference_destination = safe_ratio(df["prix_vol"], vol_reference)

    def set_or_fill_feature(column: str, values: pd.Series) -> None:
        values = pd.Series(values, index=df.index)
        if column in df.columns:
            current_values = df[column]
            if pd.api.types.is_numeric_dtype(values):
                current_values = pd.to_numeric(current_values, errors="coerce")
            df[column] = current_values.combine_first(values)
        else:
            df[column] = values

    computed_score_budget_destination = normalize_0_1(ratio_budget_reference_destination, lower=0.55, upper=1.35)
    computed_score_prix_vol_coherent = normalize_0_1(ratio_prix_vol_reference_destination, lower=0.70, upper=1.60, inverse=True)
    computed_score_adequation_activite_profil = pd.Series(
        [int(activity in ACTIVITIES_BY_CLIENT.get(client_type, set())) for client_type, activity in zip(df["client_type"], df["activite_principale"])],
        index=df.index,
    )
    score_adequation_hebergement_profil = pd.Series(
        [int(hebergement in HEBERGEMENTS_BY_CLIENT.get(client_type, set())) for client_type, hebergement in zip(df["client_type"], df["type_hebergement"])],
        index=df.index,
    )
    computed_score_meteo_prevue = df["meteo_prevue"].map(METEO_SCORE).fillna(0.5)

    set_or_fill_feature("reste_budget_apres_vol", reste_budget_apres_vol)
    set_or_fill_feature("budget_apres_vol_par_jour", budget_apres_vol_par_jour)
    set_or_fill_feature("score_budget_destination", computed_score_budget_destination)
    set_or_fill_feature("score_prix_vol_coherent", computed_score_prix_vol_coherent)
    set_or_fill_feature("score_adequation_activite_profil", computed_score_adequation_activite_profil)
    set_or_fill_feature("score_meteo_prevue", computed_score_meteo_prevue)

    temperature = numeric_series(df, "temperature_moyenne_saison", default=23)
    score_confort_temperature = (1 - (temperature.sub(23).abs() / 18)).clip(0, 1).fillna(0.5)
    score_risque_pluie_reel = normalize_0_1(numeric_series(df, "jours_pluie_moyen"), lower=0.0, upper=0.55, inverse=True)
    score_qualite_air = normalize_0_1(numeric_series(df, "european_aqi_moyen"), lower=20, upper=80, inverse=True)
    computed_score_contexte_destination = (0.35 * score_confort_temperature + 0.35 * score_risque_pluie_reel + 0.30 * score_qualite_air).fillna(0.5)
    set_or_fill_feature("score_contexte_destination", computed_score_contexte_destination)

    computed_score_potentiel_satisfaction = (
        0.28 * pd.to_numeric(df["score_budget_destination"], errors="coerce")
        + 0.18 * pd.to_numeric(df["score_prix_vol_coherent"], errors="coerce")
        + 0.18 * pd.to_numeric(df["score_adequation_activite_profil"], errors="coerce")
        + 0.12 * score_adequation_hebergement_profil
        + 0.12 * pd.to_numeric(df["score_meteo_prevue"], errors="coerce")
        + 0.12 * pd.to_numeric(df["score_contexte_destination"], errors="coerce")
    ).round(4)
    set_or_fill_feature("score_potentiel_satisfaction", computed_score_potentiel_satisfaction)

    computed_niveau_risque_satisfaction = pd.cut(
        pd.to_numeric(df["score_potentiel_satisfaction"], errors="coerce"),
        bins=[-np.inf, 0.40, 0.60, np.inf],
        labels=["risque_eleve", "risque_moyen", "risque_faible"],
    ).astype(str)
    if "niveau_risque_satisfaction" in df.columns:
        df["niveau_risque_satisfaction"] = df["niveau_risque_satisfaction"].combine_first(computed_niveau_risque_satisfaction)
    else:
        df["niveau_risque_satisfaction"] = computed_niveau_risque_satisfaction

    df["imprevu_present"] = indicateur(df["imprevus"] != "aucun", df["imprevus"].isna())
    df["imprevu_transport"] = indicateur(df["imprevus"].isin(["retard_vol", "annulation", "bagages"]), df["imprevus"].isna())
    df["imprevu_meteo"] = indicateur(df["imprevus"].isin(["m\u00e9t\u00e9o", "meteo"]), df["imprevus"].isna())

    for column in ["budget_par_jour", "part_vol_budget", "budget_apres_vol_par_jour"]:
        df[column] = df[column].replace([np.inf, -np.inf], np.nan)

    for column in df.select_dtypes(include=["object", "string"]).columns:
        df[column] = df[column].astype(object).where(~df[column].isna(), np.nan)

    return df.drop(columns=FEATURES_SUPPRIMEES_MODELISATION, errors="ignore")


def prepare_training_dataset(df_source: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[dict[str, Any]]]:
    df_clean, cleaning_report = clean_dataset(df_source)
    df_model = add_base_features(df_clean)

    excluded_columns = [
        "trip_id",
        TARGET_COLUMN,
        *FEATURES_SUPPRIMEES_MODELISATION,
        *POST_TRIP_COLUMNS,
    ]
    feature_columns = [column for column in df_model.columns if column not in excluded_columns]
    x = df_model[feature_columns].copy()
    y = df_model[TARGET_COLUMN].astype(int).apply(satisfaction_to_binary).astype(int)
    return x, y, cleaning_report


def prepare_prediction_features(df_source: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    df_model = add_base_features(df_source)
    return df_model.reindex(columns=feature_columns)


def build_reference_profile(x_train: pd.DataFrame, numeric_features: list[str], categorical_features: list[str]) -> dict[str, Any]:
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
            "distribution": {str(category): float(percentage) for category, percentage in distribution.items()},
        }

    return {
        "created_from": "train_split",
        "n_rows": int(x_train.shape[0]),
        "numeric_features": numeric_profile,
        "categorical_features": categorical_profile,
    }


def detect_binary_numeric_features(x: pd.DataFrame, numeric_features: list[str]) -> list[str]:
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
    categorical_features = x_train.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    binary_numeric_features = detect_binary_numeric_features(x_train, numeric_features)
    continuous_numeric_features = [column for column in numeric_features if column not in binary_numeric_features]

    continuous_numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("outliers_iqr", IQRMedianOutlierReplacer()),
        ("scaler", StandardScaler()),
    ])
    binary_numeric_transformer = Pipeline(steps=[("imputer", SimpleImputer(strategy="most_frequent"))])
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

    return ColumnTransformer(transformers=transformers), numeric_features, categorical_features


def candidate_models() -> dict[str, Any]:
    return {
        "DummyClassifier": DummyClassifier(strategy="most_frequent"),
        "LogisticRegression": LogisticRegression(max_iter=500, class_weight="balanced"),
        "RandomForest": RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            random_state=RANDOM_STATE,
            class_weight="balanced",
            n_jobs=1,
        ),
    }


def _classification_metrics(y_test: pd.Series, predictions: np.ndarray, probabilities: np.ndarray | None) -> dict[str, float]:
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
        "macro_f1": float(f1_score(y_test, predictions, average="macro", zero_division=0)),
        "precision_satisfait": float(precision_score(y_test, predictions, pos_label=POSITIVE_CLASS, zero_division=0)),
        "recall_satisfait": float(recall_score(y_test, predictions, pos_label=POSITIVE_CLASS, zero_division=0)),
        "f1_satisfait": float(f1_score(y_test, predictions, pos_label=POSITIVE_CLASS, zero_division=0)),
    }
    if probabilities is not None and len(np.unique(y_test)) == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_test, probabilities))
    return metrics


def train_and_select_model(x: pd.DataFrame, y: pd.Series, cleaning_report: list[dict[str, Any]], test_size: float = 0.2) -> TrainingResult:
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
        pipeline = Pipeline(steps=[("preprocess", clone(preprocess)), ("model", model)])
        pipeline.fit(x_train, y_train)
        predictions = pipeline.predict(x_test)
        probabilities = None
        if hasattr(pipeline, "predict_proba"):
            probabilities_matrix = pipeline.predict_proba(x_test)
            if POSITIVE_CLASS in pipeline.classes_:
                positive_index = list(pipeline.classes_).index(POSITIVE_CLASS)
                probabilities = probabilities_matrix[:, positive_index]

        row = {"modele": model_name, **_classification_metrics(y_test, predictions, probabilities)}
        rows.append(row)
        fitted[model_name] = pipeline

    results = pd.DataFrame(rows).sort_values(["macro_f1", "balanced_accuracy", "accuracy"], ascending=[False, False, False]).reset_index(drop=True)

    best_model_name = "LogisticRegression"
    best_pipeline = fitted[best_model_name]
    best_predictions = best_pipeline.predict(x_test)
    best_probabilities = None
    if hasattr(best_pipeline, "predict_proba") and POSITIVE_CLASS in best_pipeline.classes_:
        positive_index = list(best_pipeline.classes_).index(POSITIVE_CLASS)
        best_probabilities = best_pipeline.predict_proba(x_test)[:, positive_index]

    metrics = _classification_metrics(y_test, best_predictions, best_probabilities)
    metrics.update({"test_size": float(test_size), "train_rows": int(len(x_train)), "test_rows": int(len(x_test))})
    confusion = confusion_matrix(y_test, best_predictions, labels=CLASS_LABELS)

    return TrainingResult(
        model_name=best_model_name,
        pipeline=best_pipeline,
        metrics=metrics,
        feature_columns=x.columns.tolist(),
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        evaluation_results=results.to_dict(orient="records"),
        confusion_matrix=confusion.astype(int).tolist(),
        cleaning_report=cleaning_report,
        reference_profile=build_reference_profile(x_train, numeric_features, categorical_features),
    )


def save_training_artifacts(result: TrainingResult, model_path: Path, metadata_path: Path) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(result.pipeline, model_path)

    metadata = {
        "solution_name": SOLUTION_NAME,
        "display_model_name": "TravelMind LogisticRegression Satisfaction Model",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "objective": "travelmind_satisfaction_binaire",
        "model_name": result.model_name,
        "target": TARGET_COLUMN,
        "target_type": "binary_classification",
        "positive_class": POSITIVE_CLASS,
        "class_labels": CLASS_LABELS,
        "class_names": [CLASS_NAMES[label] for label in CLASS_LABELS],
        "metrics": result.metrics,
        "feature_columns": result.feature_columns,
        "numeric_features": result.numeric_features,
        "categorical_features": result.categorical_features,
        "pre_voyage_input_columns": PRE_VOYAGE_INPUT_COLUMNS,
        "post_voyage_features_excluded": POST_TRIP_COLUMNS,
        "removed_features": FEATURES_SUPPRIMEES_MODELISATION,
        "evaluation_results": result.evaluation_results,
        "confusion_matrix": result.confusion_matrix,
        "cleaning_report": result.cleaning_report,
        "training_reference_profile": result.reference_profile,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

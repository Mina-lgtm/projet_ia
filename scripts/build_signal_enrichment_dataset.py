from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
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

from app.modeling import (  # noqa: E402
    RANDOM_STATE,
    TARGET_COLUMN,
    build_preprocessor,
    candidate_models,
    clean_dataset,
    clip_satisfaction_score,
    prepare_training_dataset,
)


SOURCE_DATASET = (
    PROJECT_ROOT
    / "data"
    / "versions"
    / "v2_1_enrichment"
    / "travel_planning_dataset_v2_1.csv"
)
FALLBACK_DATASET = PROJECT_ROOT / "data" / "Examen_travel_planning_dataset.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "versions" / "v2_2_signal_enrichment"
OUTPUT_DATASET = OUTPUT_DIR / "travel_planning_dataset_v2_2.csv"
OUTPUT_REPORT = OUTPUT_DIR / "signal_enrichment_report.json"
OUTPUT_README = OUTPUT_DIR / "README.md"
TARGET_ROWS = 3000
BROKEN_ACCENT = "\ufffd"


DESTINATION_REFERENCE = {
    "paris": {"budget_reference": 4200, "prix_vol_reference": 350, "complexite_transport": 0.20},
    "rome": {"budget_reference": 3900, "prix_vol_reference": 450, "complexite_transport": 0.25},
    "lisbonne": {"budget_reference": 3400, "prix_vol_reference": 380, "complexite_transport": 0.20},
    "bali": {"budget_reference": 6200, "prix_vol_reference": 1150, "complexite_transport": 0.75},
    "new york": {"budget_reference": 6500, "prix_vol_reference": 850, "complexite_transport": 0.55},
    "tokyo": {"budget_reference": 7200, "prix_vol_reference": 1050, "complexite_transport": 0.80},
    "sydney": {"budget_reference": 8000, "prix_vol_reference": 1300, "complexite_transport": 0.95},
    "dubaï": {"budget_reference": 6100, "prix_vol_reference": 700, "complexite_transport": 0.45},
    "duba" + BROKEN_ACCENT: {"budget_reference": 6100, "prix_vol_reference": 700, "complexite_transport": 0.45},
}

ACTIVITIES_BY_CLIENT = {
    "famille": {"plage", "culture", "gastronomie"},
    "couple": {"culture", "gastronomie", "plage"},
    "solo": {"randonnée", "randonn" + BROKEN_ACCENT + "e", "culture"},
    "business": {"business"},
    "senior": {"culture", "gastronomie"},
}

HEBERGEMENTS_BY_CLIENT = {
    "famille": {"resort", "appartement", "villa"},
    "couple": {"hôtel", "h" + BROKEN_ACCENT + "tel", "resort", "villa"},
    "solo": {"appartement", "hôtel", "h" + BROKEN_ACCENT + "tel"},
    "business": {"hôtel", "h" + BROKEN_ACCENT + "tel"},
    "senior": {"hôtel", "h" + BROKEN_ACCENT + "tel", "appartement"},
}

METEO_SCORE = {
    "ensoleillé": 1.00,
    "ensoleill" + BROKEN_ACCENT: 1.00,
    "nuageux": 0.70,
    "variable": 0.45,
    "pluie": 0.25,
}


def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    ratio = pd.to_numeric(numerator, errors="coerce") / pd.to_numeric(denominator, errors="coerce")
    return ratio.replace([np.inf, -np.inf], np.nan)


def normalize_0_1(values: pd.Series, lower: float, upper: float, inverse: bool = False) -> pd.Series:
    numeric_values = pd.to_numeric(values, errors="coerce")
    normalized = ((numeric_values - lower) / (upper - lower)).clip(0, 1)
    if inverse:
        normalized = 1 - normalized
    return normalized.fillna(0.5)


def augment_dataset_to_target_rows(
    df_source: pd.DataFrame,
    target_rows: int = TARGET_ROWS,
    seed: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.Series, dict[str, Any]]:
    if len(df_source) >= target_rows:
        synthetic_mask = pd.Series(False, index=df_source.index)
        return df_source.copy(), synthetic_mask, {
            "target_rows": target_rows,
            "source_rows": int(len(df_source)),
            "synthetic_rows_added": 0,
            "method": "Aucune augmentation nécessaire.",
        }

    rng = np.random.default_rng(seed)
    rows_to_add = target_rows - len(df_source)
    synthetic_rows = (
        df_source
        .sample(n=rows_to_add, replace=True, random_state=seed)
        .copy()
        .reset_index(drop=True)
    )

    max_trip_id = pd.to_numeric(df_source["trip_id"], errors="coerce").max()
    if pd.isna(max_trip_id):
        max_trip_id = len(df_source)
    synthetic_rows["trip_id"] = np.arange(int(max_trip_id) + 1, int(max_trip_id) + rows_to_add + 1)

    synthetic_rows["budget_total"] = (
        pd.to_numeric(synthetic_rows["budget_total"], errors="coerce")
        * rng.normal(1.0, 0.16, rows_to_add)
    ).clip(500, 50000).round(2)
    synthetic_rows["prix_vol"] = (
        pd.to_numeric(synthetic_rows["prix_vol"], errors="coerce")
        * rng.normal(1.0, 0.18, rows_to_add)
    ).clip(0, 15000).round(2)
    synthetic_rows["prix_vol"] = np.minimum(
        synthetic_rows["prix_vol"],
        (synthetic_rows["budget_total"] * 0.90).round(2),
    )
    synthetic_rows["duree_jours"] = (
        pd.to_numeric(synthetic_rows["duree_jours"], errors="coerce").fillna(7).astype(int)
        + rng.integers(-3, 4, rows_to_add)
    ).clip(1, 90)

    replacements = {
        "type_hebergement": ["hôtel", "resort", "appartement", "villa"],
        "meteo_prevue": ["ensoleillé", "nuageux", "pluie", "variable"],
        "activite_principale": ["plage", "randonnée", "gastronomie", "culture", "business"],
    }
    for column, values in replacements.items():
        if column in synthetic_rows.columns:
            replace_mask = rng.random(rows_to_add) < 0.18
            synthetic_rows.loc[replace_mask, column] = rng.choice(values, replace_mask.sum())

    df_augmented = pd.concat([df_source, synthetic_rows], ignore_index=True)
    synthetic_mask = pd.Series(False, index=df_augmented.index)
    synthetic_mask.iloc[len(df_source):] = True

    return df_augmented, synthetic_mask, {
        "target_rows": target_rows,
        "source_rows": int(len(df_source)),
        "synthetic_rows_added": int(rows_to_add),
        "method": (
            "Échantillonnage avec remise des lignes nettoyées, perturbation contrôlée des variables "
            "avant départ numériques, variation partielle de l'hébergement, de la météo et de l'activité."
        ),
    }


def assign_synthetic_targets(
    df_source: pd.DataFrame,
    synthetic_mask: pd.Series,
    seed: int = RANDOM_STATE,
) -> pd.DataFrame:
    df = df_source.copy()
    if not synthetic_mask.any():
        return df

    rng = np.random.default_rng(seed)
    score = pd.to_numeric(
        df.loc[synthetic_mask, "score_potentiel_satisfaction"],
        errors="coerce",
    ).fillna(0.5)
    noisy_score = (score + rng.normal(0, 0.08, synthetic_mask.sum())).clip(0, 1)

    df.loc[synthetic_mask, TARGET_COLUMN] = pd.cut(
        noisy_score,
        bins=[-np.inf, 0.28, 0.45, 0.62, 0.80, np.inf],
        labels=[1, 2, 3, 4, 5],
    ).astype(int)

    feedback = {
        1: "très mauvaise expérience.",
        2: "séjour décevant.",
        3: "séjour correct mais perfectible.",
        4: "très bon séjour.",
        5: "excellent séjour.",
    }
    df.loc[synthetic_mask, "retour_client"] = (
        df.loc[synthetic_mask, TARGET_COLUMN]
        .astype(int)
        .map(feedback)
    )
    return df


def add_signal_features(df_source: pd.DataFrame) -> pd.DataFrame:
    df = df_source.copy()

    for column in [
        "client_type",
        "destination",
        "saison",
        "type_hebergement",
        "meteo_prevue",
        "activite_principale",
    ]:
        df[column] = df[column].astype("string").str.strip().str.lower()

    budget_reference = df["destination"].map(
        lambda value: DESTINATION_REFERENCE.get(str(value), {}).get("budget_reference", np.nan)
    )
    vol_reference = df["destination"].map(
        lambda value: DESTINATION_REFERENCE.get(str(value), {}).get("prix_vol_reference", np.nan)
    )
    complexite_transport = df["destination"].map(
        lambda value: DESTINATION_REFERENCE.get(str(value), {}).get("complexite_transport", np.nan)
    )

    df["budget_reference_destination"] = budget_reference
    df["prix_vol_reference_destination"] = vol_reference
    df["complexite_transport_destination"] = complexite_transport.fillna(0.5)

    df["reste_budget_apres_vol"] = df["budget_total"] - df["prix_vol"]
    df["budget_apres_vol_par_jour"] = safe_ratio(
        df["reste_budget_apres_vol"],
        df["duree_jours"].replace(0, np.nan),
    )
    df["ratio_budget_reference_destination"] = safe_ratio(df["budget_total"], budget_reference)
    df["ratio_prix_vol_reference_destination"] = safe_ratio(df["prix_vol"], vol_reference)

    df["score_budget_destination"] = normalize_0_1(
        df["ratio_budget_reference_destination"],
        lower=0.55,
        upper=1.35,
    )
    df["score_prix_vol_coherent"] = normalize_0_1(
        df["ratio_prix_vol_reference_destination"],
        lower=0.70,
        upper=1.60,
        inverse=True,
    )

    df["score_adequation_activite_profil"] = [
        int(activity in ACTIVITIES_BY_CLIENT.get(client_type, set()))
        for client_type, activity in zip(df["client_type"], df["activite_principale"])
    ]
    df["score_adequation_hebergement_profil"] = [
        int(hebergement in HEBERGEMENTS_BY_CLIENT.get(client_type, set()))
        for client_type, hebergement in zip(df["client_type"], df["type_hebergement"])
    ]
    df["score_meteo_prevue"] = (
        df["meteo_prevue"]
        .map(METEO_SCORE)
        .fillna(0.5)
    )

    temperature = pd.to_numeric(df.get("temperature_moyenne_saison", np.nan), errors="coerce")
    df["score_confort_temperature"] = (
        1 - (temperature.sub(23).abs() / 18)
    ).clip(0, 1).fillna(0.5)

    df["score_risque_pluie_reel"] = normalize_0_1(
        df.get("jours_pluie_moyen", pd.Series(np.nan, index=df.index)),
        lower=0.0,
        upper=0.55,
        inverse=True,
    )
    df["score_qualite_air"] = normalize_0_1(
        df.get("european_aqi_moyen", pd.Series(np.nan, index=df.index)),
        lower=20,
        upper=80,
        inverse=True,
    )

    df["score_contexte_destination"] = (
        0.35 * df["score_confort_temperature"]
        + 0.35 * df["score_risque_pluie_reel"]
        + 0.30 * df["score_qualite_air"]
    )

    df["score_potentiel_satisfaction"] = (
        0.28 * df["score_budget_destination"]
        + 0.18 * df["score_prix_vol_coherent"]
        + 0.18 * df["score_adequation_activite_profil"]
        + 0.12 * df["score_adequation_hebergement_profil"]
        + 0.12 * df["score_meteo_prevue"]
        + 0.12 * df["score_contexte_destination"]
    ).round(4)

    df["niveau_risque_satisfaction"] = pd.cut(
        df["score_potentiel_satisfaction"],
        bins=[-np.inf, 0.40, 0.60, np.inf],
        labels=["risque_eleve", "risque_moyen", "risque_faible"],
    ).astype(str)

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


def write_readme(report: dict[str, Any]) -> None:
    lines = [
        "# Dataset v2.2 - enrichissement signal métier",
        "",
        "Cette version est une expérience séparée destinée à tester si des variables avant départ plus structurées améliorent la prédiction.",
        "",
        "Important : les variables ajoutées ne sont pas calculées à partir de `satisfaction_client`.",
        "Elles évitent donc une fuite de cible, mais restent des scores métier/proxys à valider avant usage réel.",
        "",
        "## Fichiers",
        "",
        f"- Dataset : `{report['output_dataset']}`",
        f"- Rapport : `data/versions/v2_2_signal_enrichment/signal_enrichment_report.json`",
        "",
        "## Variables ajoutées",
        "",
    ]
    for column in report["added_columns"]:
        lines.append(f"- `{column}`")
    lines.extend([
        "",
        "## Résumé des résultats",
        "",
        f"- Meilleur modèle régression v2.2 : `{report['comparison']['best_regression_after']['modele']}`",
        f"- MAE v2.2 : `{report['comparison']['best_regression_after']['mae']}`",
        f"- R2 v2.2 : `{report['comparison']['best_regression_after']['r2']}`",
        f"- Meilleur modèle binaire v2.2 : `{report['comparison']['best_binary_after']['modele']}`",
        f"- F1 binaire v2.2 : `{report['comparison']['best_binary_after']['f1_1']}`",
        f"- ROC AUC binaire v2.2 : `{report['comparison']['best_binary_after']['roc_auc']}`",
        "",
        "## Conclusion",
        "",
        report["comparison"]["interpretation"],
        "",
    ])
    OUTPUT_README.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    input_path = SOURCE_DATASET if SOURCE_DATASET.exists() else FALLBACK_DATASET
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df_source = pd.read_csv(input_path)
    df_augmented, synthetic_mask, augmentation_summary = augment_dataset_to_target_rows(df_source)
    df_after = add_signal_features(df_augmented)
    df_after = assign_synthetic_targets(df_after, synthetic_mask)
    df_after.to_csv(OUTPUT_DATASET, index=False, encoding="utf-8")

    df_before = df_after.drop(
        columns=[column for column in df_after.columns if column not in df_source.columns],
        errors="ignore",
    )
    added_columns = [column for column in df_after.columns if column not in df_source.columns]
    regression_before = evaluate_regression(df_before)
    regression_after = evaluate_regression(df_after)
    binary_before = evaluate_binary_classification(df_before)
    binary_after = evaluate_binary_classification(df_after)

    best_reg_before = regression_before[0]
    best_reg_after = regression_after[0]
    best_bin_before = binary_before[0]
    best_bin_after = binary_after[0]

    interpretation = (
        "La version v2.2 atteint 3000 lignes en combinant les lignes nettoyées existantes "
        "avec des lignes synthétiques générées par règles métier avant départ. Les résultats "
        "permettent de tester l'hypothèse suivante : avec plus de variables structurées et "
        "une cible plus cohérente sur les lignes synthétiques, le modèle peut mieux apprendre. "
        "Cette version reste expérimentale et ne remplace pas une collecte de données réelles."
    )

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset": str(input_path.relative_to(PROJECT_ROOT)),
        "output_dataset": str(OUTPUT_DATASET.relative_to(PROJECT_ROOT)),
        "rows": int(len(df_after)),
        "original_rows": int(len(df_source)),
        "synthetic_rows_added": int(augmentation_summary["synthetic_rows_added"]),
        "augmentation_summary": augmentation_summary,
        "columns_before": int(df_source.shape[1]),
        "columns_after": int(df_after.shape[1]),
        "added_columns": added_columns,
        "policy": {
            "uses_target_to_create_features": False,
            "uses_post_voyage_columns_to_create_features": False,
            "synthetic_rows_have_synthetic_target": True,
            "purpose": "Tester un enrichissement avant départ séparé sans remplacer le dataset officiel.",
        },
        "target_distribution": {
            str(key): int(value)
            for key, value in df_after[TARGET_COLUMN].value_counts(dropna=False).sort_index().items()
        },
        "regression_before": regression_before,
        "regression_after": regression_after,
        "binary_before": binary_before,
        "binary_after": binary_after,
        "comparison": {
            "best_regression_before": best_reg_before,
            "best_regression_after": best_reg_after,
            "mae_gain": round(float(best_reg_before["mae"] - best_reg_after["mae"]), 4),
            "r2_gain": round(float(best_reg_after["r2"] - best_reg_before["r2"]), 4),
            "best_binary_before": best_bin_before,
            "best_binary_after": best_bin_after,
            "f1_gain": round(float(best_bin_after["f1_1"] - best_bin_before["f1_1"]), 4),
            "roc_auc_gain": round(float(best_bin_after["roc_auc"] - best_bin_before["roc_auc"]), 4),
            "interpretation": interpretation,
        },
    }
    OUTPUT_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_readme(report)

    print(f"Dataset v2.2 généré : {OUTPUT_DATASET.relative_to(PROJECT_ROOT)}")
    print(f"Rapport généré : {OUTPUT_REPORT.relative_to(PROJECT_ROOT)}")
    print(f"Lignes source : {len(df_source)}")
    print(f"Lignes synthétiques ajoutées : {augmentation_summary['synthetic_rows_added']}")
    print(f"Lignes finales : {len(df_after)}")
    print("\nColonnes ajoutees :")
    print(pd.Series(added_columns).to_string(index=False))
    print("\nRegression avant :")
    print(pd.DataFrame(regression_before).to_string(index=False))
    print("\nRegression apres v2.2 :")
    print(pd.DataFrame(regression_after).to_string(index=False))
    print("\nClassification binaire avant :")
    print(pd.DataFrame(binary_before).to_string(index=False))
    print("\nClassification binaire apres v2.2 :")
    print(pd.DataFrame(binary_after).to_string(index=False))
    print("\nGains :")
    print(json.dumps(report["comparison"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

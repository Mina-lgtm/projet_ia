from pathlib import Path

import pandas as pd

from app.modeling import (
    POST_TRIP_COLUMNS,
    PRE_VOYAGE_INPUT_COLUMNS,
    TARGET_COLUMN,
    build_reference_profile,
    prepare_training_dataset,
    satisfaction_to_binary,
    train_and_select_model,
)


DATA_PATH = Path("data/versions/v2_2_signal_enrichment/dataset_final.csv")


def test_satisfaction_to_binary() -> None:
    assert satisfaction_to_binary(1) == 0
    assert satisfaction_to_binary(2) == 0
    assert satisfaction_to_binary(3) == 0
    assert satisfaction_to_binary(4) == 1
    assert satisfaction_to_binary(5) == 1


def test_prepare_training_dataset_uses_only_pre_voyage_columns() -> None:
    df_raw = pd.read_csv(DATA_PATH)

    x, y, cleaning_report = prepare_training_dataset(df_raw)

    assert len(x) == len(y)
    assert TARGET_COLUMN not in x.columns
    assert "trip_id" not in x.columns
    assert "retour_client" not in x.columns
    assert "budget_hors_vol" not in x.columns
    assert "region_destination" not in x.columns
    assert "distance_vol_categorie" not in x.columns
    assert "destination_luxe" not in x.columns
    assert "budget_non_respecte" not in x.columns
    assert "budget_tendu" not in x.columns
    assert "gravite_imprevu" not in x.columns
    assert set(y.unique()).issubset({0, 1})
    assert cleaning_report

    for column in POST_TRIP_COLUMNS:
        assert column not in x.columns

    for column in PRE_VOYAGE_INPUT_COLUMNS:
        assert column in x.columns


def test_train_and_select_model_returns_fitted_pipeline() -> None:
    df_raw = pd.read_csv(DATA_PATH)
    x, y, cleaning_report = prepare_training_dataset(df_raw)

    result = train_and_select_model(x, y, cleaning_report, test_size=0.2)

    assert result.model_name == "LogisticRegression"
    assert result.metrics["accuracy"] >= 0
    assert result.metrics["macro_f1"] >= 0
    assert "roc_auc" in result.metrics
    assert result.feature_columns == x.columns.tolist()
    assert hasattr(result.pipeline, "predict")
    assert hasattr(result.pipeline, "predict_proba")
    assert result.evaluation_results
    assert result.confusion_matrix
    assert result.reference_profile["n_rows"] > 0


def test_build_reference_profile_contains_numeric_and_categorical_stats() -> None:
    df_raw = pd.read_csv(DATA_PATH)
    x, _, _ = prepare_training_dataset(df_raw)

    profile = build_reference_profile(
        x_train=x,
        numeric_features=["budget_total"],
        categorical_features=["client_type"],
    )

    assert profile["n_rows"] == len(x)
    assert "budget_total" in profile["numeric_features"]
    assert "mean" in profile["numeric_features"]["budget_total"]
    assert "client_type" in profile["categorical_features"]
    assert "distribution" in profile["categorical_features"]["client_type"]

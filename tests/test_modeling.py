from pathlib import Path

import pandas as pd

from app.modeling import (
    CLASS_LABELS,
    POST_TRIP_COLUMNS,
    PRE_VOYAGE_INPUT_COLUMNS,
    TARGET_COLUMN,
    build_reference_profile,
    prepare_training_dataset,
    satisfaction_to_3_classes,
    train_and_select_model,
)


DATA_PATH = Path("data/Examen_travel_planning_dataset.csv")


def test_satisfaction_to_3_classes() -> None:
    assert satisfaction_to_3_classes(1) == 0
    assert satisfaction_to_3_classes(2) == 0
    assert satisfaction_to_3_classes(3) == 1
    assert satisfaction_to_3_classes(4) == 2
    assert satisfaction_to_3_classes(5) == 2


def test_prepare_training_dataset_uses_only_pre_voyage_columns() -> None:
    df_raw = pd.read_csv(DATA_PATH)

    x, y, cleaning_report = prepare_training_dataset(df_raw)

    assert len(x) == len(y)
    assert TARGET_COLUMN not in x.columns
    assert "trip_id" not in x.columns
    assert "retour_client" not in x.columns
    assert "budget_hors_vol" not in x.columns
    assert set(y.unique()).issubset(set(CLASS_LABELS))
    assert cleaning_report

    for column in POST_TRIP_COLUMNS:
        assert column not in x.columns

    for column in PRE_VOYAGE_INPUT_COLUMNS:
        assert column in x.columns


def test_train_and_select_model_returns_fitted_pipeline() -> None:
    df_raw = pd.read_csv(DATA_PATH)
    x, y, cleaning_report = prepare_training_dataset(df_raw)

    result = train_and_select_model(x, y, cleaning_report, test_size=0.2)

    assert result.model_name
    assert result.metrics["macro_f1"] >= 0
    assert result.feature_columns == x.columns.tolist()
    assert hasattr(result.pipeline, "predict")
    assert len(result.confusion_matrix) == len(CLASS_LABELS)
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

import json

import pandas as pd

from app.modeling import build_reference_profile, prepare_prediction_features
from app.monitoring import (
    PredictionLogger,
    build_alert_report,
    build_drift_report,
    build_monitoring_report,
)
from app.schemas import TravelPredictionRequest, TravelPredictionResponse


def make_request(**overrides) -> TravelPredictionRequest:
    values = {
        "client_type": "couple",
        "budget_total": 4200,
        "destination": "rome",
        "saison": "printemps",
        "duree_jours": 7,
        "type_hebergement": "hôtel",
        "prix_vol": 650,
        "meteo_prevue": "ensoleillé",
        "activite_principale": "culture",
    }
    values.update(overrides)
    return TravelPredictionRequest(**values)


def make_response(
    confidence: float = 0.52,
    libelle_prediction: str = "non_satisfait_1_2_3",
    low_confidence: bool = True,
) -> TravelPredictionResponse:
    classe_predite = 1 if libelle_prediction == "satisfait_4_5" else 0
    probability_positive = confidence if classe_predite == 1 else 1 - confidence
    probability_negative = 1 - probability_positive
    return TravelPredictionResponse(
        objective="travelmind_satisfaction_binaire",
        model_name="LogisticRegression",
        classe_predite=classe_predite,
        libelle_prediction=libelle_prediction,
        probabilities=[
            {"classe": 0, "libelle": "non_satisfait_1_2_3", "probabilite": round(probability_negative, 4)},
            {"classe": 1, "libelle": "satisfait_4_5", "probabilite": round(probability_positive, 4)},
        ],
        confidence=confidence,
        low_confidence=low_confidence,
        model_metrics={"accuracy": 0.7033, "macro_f1": 0.6768, "roc_auc": 0.7318},
    )


def test_prediction_logger_writes_jsonl_record(tmp_path) -> None:
    log_path = tmp_path / "predictions.jsonl"
    logger = PredictionLogger(log_path=log_path)

    request = make_request()
    response = make_response(confidence=0.52)

    record = logger.log_prediction(request, response)
    written_record = json.loads(log_path.read_text(encoding="utf-8").strip())

    assert record["model_name"] == "LogisticRegression"
    assert written_record["classe_predite"] == 0
    assert written_record["libelle_prediction"] == "non_satisfait_1_2_3"
    assert written_record["confidence"] == 0.52
    assert written_record["low_confidence"] is True
    assert written_record["input"]["destination"] == "rome"


def test_build_monitoring_report_from_prediction_logs(tmp_path) -> None:
    log_path = tmp_path / "predictions.jsonl"
    logger = PredictionLogger(log_path=log_path)
    request = make_request()

    logger.log_prediction(
        request,
        make_response(confidence=0.72, libelle_prediction="non_satisfait_1_2_3", low_confidence=False),
    )
    logger.log_prediction(
        request,
        make_response(confidence=0.51, libelle_prediction="satisfait_4_5", low_confidence=True),
    )

    report = build_monitoring_report(log_path=log_path)

    assert report["nb_predictions"] == 2
    assert report["prediction_distribution"] == {
        "non_satisfait_1_2_3": 1,
        "satisfait_4_5": 1,
    }
    assert report["low_confidence_count"] == 1
    assert report["low_confidence_rate"] == 50.0
    assert report["average_confidence"] == 0.615


def test_build_drift_report_from_prediction_logs_and_reference_profile(tmp_path) -> None:
    log_path = tmp_path / "predictions.jsonl"
    metadata_path = tmp_path / "metadata.json"
    logger = PredictionLogger(log_path=log_path)

    reference_inputs = [
        {
            "client_type": "couple",
            "budget_total": 4000,
            "destination": "rome",
            "saison": "printemps",
            "duree_jours": 7,
            "type_hebergement": "hôtel",
            "prix_vol": 650,
            "meteo_prevue": "ensoleillé",
            "activite_principale": "culture",
        },
        {
            "client_type": "famille",
            "budget_total": 4500,
            "destination": "paris",
            "saison": "été",
            "duree_jours": 10,
            "type_hebergement": "appartement",
            "prix_vol": 500,
            "meteo_prevue": "variable",
            "activite_principale": "gastronomie",
        },
    ]
    feature_columns = [
        "client_type",
        "budget_total",
        "destination",
        "saison",
        "duree_jours",
        "type_hebergement",
        "prix_vol",
        "meteo_prevue",
        "activite_principale",
        "budget_par_jour",
        "part_vol_budget",
        "sejour_long",
        "meteo_risque",
        "client_business",
        "hebergement_luxe",
    ]
    reference_features = prepare_prediction_features(
        pd.DataFrame(reference_inputs),
        feature_columns,
    )
    profile = build_reference_profile(
        reference_features,
        numeric_features=["budget_total", "duree_jours"],
        categorical_features=["client_type", "destination"],
    )
    metadata_path.write_text(
        json.dumps(
            {
                "feature_columns": feature_columns,
                "training_reference_profile": profile,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    logger.log_prediction(
        make_request(
            client_type="business",
            budget_total=20000,
            destination="tokyo",
            saison="hiver",
            duree_jours=30,
            type_hebergement="villa",
            prix_vol=3500,
            meteo_prevue="pluie",
            activite_principale="business",
        ),
        make_response(confidence=0.79, libelle_prediction="non_satisfait_1_2_3", low_confidence=False),
    )

    report = build_drift_report(log_path=log_path, metadata_path=metadata_path)

    assert report["status"] == "ok"
    assert report["nb_predictions_analyzed"] == 1
    assert report["sample_size_warning"] is True
    assert "numeric_drift" in report
    assert "categorical_drift" in report
    assert report["alerts_count"] >= 1


def test_build_alert_report_requires_more_data_before_retraining(tmp_path) -> None:
    log_path = tmp_path / "predictions.jsonl"
    logger = PredictionLogger(log_path=log_path)

    logger.log_prediction(make_request(), make_response(confidence=0.51, low_confidence=True))

    report = build_alert_report(log_path=log_path, metadata_path=tmp_path / "missing.json")

    assert report["decision"] == "monitor_and_review"
    assert report["retraining_recommended"] is False
    assert any(alert["type"] == "sample_size" for alert in report["alerts"])


def test_build_alert_report_recommends_retraining_candidate_with_confirmed_drift(tmp_path) -> None:
    log_path = tmp_path / "predictions.jsonl"
    metadata_path = tmp_path / "metadata.json"
    logger = PredictionLogger(log_path=log_path)

    feature_columns = ["destination", "budget_total", "duree_jours"]
    reference_features = prepare_prediction_features(
        pd.DataFrame([
            {"destination": "rome", "budget_total": 4000, "duree_jours": 7},
            {"destination": "paris", "budget_total": 4500, "duree_jours": 10},
        ]),
        feature_columns,
    )
    profile = build_reference_profile(
        reference_features,
        numeric_features=["budget_total", "duree_jours"],
        categorical_features=["destination"],
    )
    metadata_path.write_text(
        json.dumps(
            {
                "feature_columns": feature_columns,
                "training_reference_profile": profile,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    response = make_response(
        confidence=0.80,
        libelle_prediction="satisfait_4_5",
        low_confidence=False,
    )

    for index in range(20):
        request = make_request(
            budget_total=4200 + index,
            destination="tokyo",
        )
        logger.log_prediction(request, response)

    report = build_alert_report(log_path=log_path, metadata_path=metadata_path)

    assert report["decision"] == "review_and_prepare_retraining"
    assert report["retraining_recommended"] is True
    assert any(alert["type"] == "drift" for alert in report["alerts"])

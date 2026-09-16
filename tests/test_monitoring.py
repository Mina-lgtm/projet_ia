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
    score: float = 3.2,
    interpretation: str = "satisfaction_intermediaire",
    zone_incertitude: bool = True,
) -> TravelPredictionResponse:
    return TravelPredictionResponse(
        objective="pre_voyage_satisfaction_score_regression",
        model_name="RidgeRegression_pre",
        score_satisfaction_predit=score,
        score_satisfaction_arrondi=round(score),
        interpretation=interpretation,
        zone_incertitude=zone_incertitude,
        model_metrics={"mae": 1.0525, "rmse": 1.2533, "r2": 0.0038},
    )


def test_prediction_logger_writes_jsonl_record(tmp_path) -> None:
    log_path = tmp_path / "predictions.jsonl"
    logger = PredictionLogger(log_path=log_path)

    request = make_request()
    response = make_response(score=3.2)

    record = logger.log_prediction(request, response)
    written_record = json.loads(log_path.read_text(encoding="utf-8").strip())

    assert record["model_name"] == "RidgeRegression_pre"
    assert written_record["score_satisfaction_predit"] == 3.2
    assert written_record["score_satisfaction_arrondi"] == 3
    assert written_record["interpretation"] == "satisfaction_intermediaire"
    assert written_record["low_confidence"] is True
    assert written_record["input"]["destination"] == "rome"


def test_build_monitoring_report_from_prediction_logs(tmp_path) -> None:
    log_path = tmp_path / "predictions.jsonl"
    logger = PredictionLogger(log_path=log_path)
    request = make_request()

    logger.log_prediction(
        request,
        make_response(score=2.2, interpretation="risque_insatisfaction", zone_incertitude=False),
    )
    logger.log_prediction(
        request,
        make_response(score=3.1, interpretation="satisfaction_intermediaire", zone_incertitude=True),
    )

    report = build_monitoring_report(log_path=log_path)

    assert report["nb_predictions"] == 2
    assert report["prediction_distribution"] == {
        "risque_insatisfaction": 1,
        "satisfaction_intermediaire": 1,
    }
    assert report["low_confidence_count"] == 1
    assert report["low_confidence_rate"] == 50.0
    assert report["average_predicted_score"] == 2.65


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
        make_response(score=2.1, interpretation="risque_insatisfaction", zone_incertitude=False),
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

    logger.log_prediction(make_request(), make_response(score=3.1, zone_incertitude=True))

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
        score=4.0,
        interpretation="satisfaction_probable",
        zone_incertitude=False,
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

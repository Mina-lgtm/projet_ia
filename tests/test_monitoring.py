import json

import pandas as pd

from app.modeling import build_reference_profile, prepare_prediction_features
from app.monitoring import (
    PredictionLogger,
    build_alert_report,
    build_drift_report,
    build_monitoring_report,
)
from app.schemas import (
    PredictionProbability,
    TravelPredictionRequest,
    TravelPredictionResponse,
)


def test_prediction_logger_writes_jsonl_record(tmp_path) -> None:
    log_path = tmp_path / "predictions.jsonl"
    logger = PredictionLogger(log_path=log_path)

    request = TravelPredictionRequest(
        client_type="couple",
        budget_total=4200,
        destination="rome",
        saison="printemps",
        duree_jours=7,
        type_hebergement="hôtel",
        prix_vol=650,
        meteo_prevue="ensoleillé",
        activite_principale="culture",
    )
    response = TravelPredictionResponse(
        objective="pre_voyage_satisfaction_3_classes",
        model_name="LogisticRegression_pre",
        classe_predite=0,
        libelle_prediction="insatisfait_1_2",
        probabilities=[
            PredictionProbability(classe=0, libelle="insatisfait_1_2", probabilite=0.3875),
            PredictionProbability(classe=1, libelle="neutre_3", probabilite=0.2588),
            PredictionProbability(classe=2, libelle="satisfait_4_5", probabilite=0.3537),
        ],
        model_metrics={"macro_f1": 0.3491},
    )

    record = logger.log_prediction(request, response)
    written_record = json.loads(log_path.read_text(encoding="utf-8").strip())

    assert record["model_name"] == "LogisticRegression_pre"
    assert written_record["libelle_prediction"] == "insatisfait_1_2"
    assert written_record["confidence"] == 0.3875
    assert written_record["low_confidence"] is True
    assert written_record["input"]["destination"] == "rome"


def test_build_monitoring_report_from_prediction_logs(tmp_path) -> None:
    log_path = tmp_path / "predictions.jsonl"
    logger = PredictionLogger(log_path=log_path)

    request = TravelPredictionRequest(
        client_type="couple",
        budget_total=4200,
        destination="rome",
        saison="printemps",
        duree_jours=7,
        type_hebergement="hôtel",
        prix_vol=650,
        meteo_prevue="ensoleillé",
        activite_principale="culture",
    )

    for probability in [0.4, 0.8]:
        response = TravelPredictionResponse(
            objective="pre_voyage_satisfaction_3_classes",
            model_name="LogisticRegression_pre",
            classe_predite=2,
            libelle_prediction="satisfait_4_5",
            probabilities=[
                PredictionProbability(
                    classe=2,
                    libelle="satisfait_4_5",
                    probabilite=probability,
                )
            ],
            model_metrics={"macro_f1": 0.3491},
        )
        logger.log_prediction(request, response)

    report = build_monitoring_report(log_path=log_path)

    assert report["nb_predictions"] == 2
    assert report["prediction_distribution"] == {"satisfait_4_5": 2}
    assert report["prediction_distribution_pct"] == {"satisfait_4_5": 100.0}
    assert report["low_confidence_count"] == 1
    assert report["low_confidence_rate"] == 50.0
    assert report["average_confidence"] == 0.6


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
        "region_destination",
        "distance_vol_categorie",
        "destination_luxe",
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

    request = TravelPredictionRequest(
        client_type="business",
        budget_total=20000,
        destination="tokyo",
        saison="hiver",
        duree_jours=30,
        type_hebergement="villa",
        prix_vol=3500,
        meteo_prevue="pluie",
        activite_principale="business",
    )
    response = TravelPredictionResponse(
        objective="pre_voyage_satisfaction_3_classes",
        model_name="LogisticRegression_pre",
        classe_predite=0,
        libelle_prediction="insatisfait_1_2",
        probabilities=[
            PredictionProbability(classe=0, libelle="insatisfait_1_2", probabilite=0.7)
        ],
        model_metrics={"macro_f1": 0.3491},
    )
    logger.log_prediction(request, response)

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

    request = TravelPredictionRequest(
        client_type="couple",
        budget_total=4200,
        destination="rome",
        saison="printemps",
        duree_jours=7,
        type_hebergement="hôtel",
        prix_vol=650,
        meteo_prevue="ensoleillé",
        activite_principale="culture",
    )
    response = TravelPredictionResponse(
        objective="pre_voyage_satisfaction_3_classes",
        model_name="LogisticRegression_pre",
        classe_predite=0,
        libelle_prediction="insatisfait_1_2",
        probabilities=[
            PredictionProbability(classe=0, libelle="insatisfait_1_2", probabilite=0.4)
        ],
        model_metrics={"macro_f1": 0.3491},
    )
    logger.log_prediction(request, response)

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

    response = TravelPredictionResponse(
        objective="pre_voyage_satisfaction_3_classes",
        model_name="LogisticRegression_pre",
        classe_predite=2,
        libelle_prediction="satisfait_4_5",
        probabilities=[
            PredictionProbability(classe=2, libelle="satisfait_4_5", probabilite=0.8)
        ],
        model_metrics={"macro_f1": 0.3491},
    )

    for index in range(20):
        request = TravelPredictionRequest(
            client_type="couple",
            budget_total=4200 + index,
            destination="tokyo",
            saison="printemps",
            duree_jours=7,
            type_hebergement="hôtel",
            prix_vol=650,
            meteo_prevue="ensoleillé",
            activite_principale="culture",
        )
        logger.log_prediction(request, response)

    report = build_alert_report(log_path=log_path, metadata_path=metadata_path)

    assert report["decision"] == "review_and_prepare_retraining"
    assert report["retraining_recommended"] is True
    assert any(alert["type"] == "drift" for alert in report["alerts"])

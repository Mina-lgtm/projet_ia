from fastapi.testclient import TestClient

from app.main import app, get_logger, get_predictor
from app.schemas import TravelPredictionResponse


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class FakePredictor:
    def predict(self, payload) -> TravelPredictionResponse:
        return TravelPredictionResponse(
            objective="pre_voyage_satisfaction_score_regression",
            model_name="fake_model",
            score_satisfaction_predit=3.6,
            score_satisfaction_arrondi=4,
            interpretation="satisfaction_probable",
            zone_incertitude=False,
            model_metrics={"mae": 1.05, "rmse": 1.25, "r2": 0.004},
        )


class FakeLogger:
    def __init__(self) -> None:
        self.records = []

    def log_prediction(self, request, response):
        self.records.append((request, response))
        return {"logged": True}


def test_predict_endpoint_returns_prediction() -> None:
    app.dependency_overrides[get_predictor] = lambda: FakePredictor()
    app.dependency_overrides[get_logger] = lambda: FakeLogger()
    client = TestClient(app)

    response = client.post(
        "/predict",
        json={
            "client_type": "couple",
            "budget_total": 4200,
            "destination": "rome",
            "saison": "printemps",
            "duree_jours": 7,
            "type_hebergement": "hôtel",
            "prix_vol": 650,
            "meteo_prevue": "ensoleillé",
            "activite_principale": "culture",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["objective"] == "pre_voyage_satisfaction_score_regression"
    assert body["model_name"] == "fake_model"
    assert body["score_satisfaction_predit"] == 3.6
    assert body["score_satisfaction_arrondi"] == 4
    assert body["interpretation"] == "satisfaction_probable"


def test_predict_endpoint_rejects_incoherent_budget() -> None:
    app.dependency_overrides[get_predictor] = lambda: FakePredictor()
    app.dependency_overrides[get_logger] = lambda: FakeLogger()
    client = TestClient(app)

    response = client.post(
        "/predict",
        json={
            "client_type": "couple",
            "budget_total": 500,
            "destination": "rome",
            "saison": "printemps",
            "duree_jours": 7,
            "type_hebergement": "hôtel",
            "prix_vol": 650,
            "meteo_prevue": "ensoleillé",
            "activite_principale": "culture",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_predict_endpoint_rejects_unrealistic_trip_duration() -> None:
    app.dependency_overrides[get_predictor] = lambda: FakePredictor()
    app.dependency_overrides[get_logger] = lambda: FakeLogger()
    client = TestClient(app)

    response = client.post(
        "/predict",
        json={
            "client_type": "couple",
            "budget_total": 4200,
            "destination": "rome",
            "saison": "printemps",
            "duree_jours": 1400,
            "type_hebergement": "hôtel",
            "prix_vol": 650,
            "meteo_prevue": "ensoleillé",
            "activite_principale": "culture",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_predict_endpoint_rejects_unknown_closed_category() -> None:
    app.dependency_overrides[get_predictor] = lambda: FakePredictor()
    app.dependency_overrides[get_logger] = lambda: FakeLogger()
    client = TestClient(app)

    response = client.post(
        "/predict",
        json={
            "client_type": "etudiant",
            "budget_total": 4200,
            "destination": "rome",
            "saison": "printemps",
            "duree_jours": 7,
            "type_hebergement": "hôtel",
            "prix_vol": 650,
            "meteo_prevue": "ensoleillé",
            "activite_principale": "culture",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_predict_endpoint_accepts_unknown_destination() -> None:
    app.dependency_overrides[get_predictor] = lambda: FakePredictor()
    app.dependency_overrides[get_logger] = lambda: FakeLogger()
    client = TestClient(app)

    response = client.post(
        "/predict",
        json={
            "client_type": "couple",
            "budget_total": 4200,
            "destination": "geneve",
            "saison": "printemps",
            "duree_jours": 7,
            "type_hebergement": "hôtel",
            "prix_vol": 650,
            "meteo_prevue": "ensoleillé",
            "activite_principale": "culture",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200


def test_monitoring_summary_endpoint_returns_report() -> None:
    client = TestClient(app)

    response = client.get("/monitoring/summary")

    assert response.status_code == 200
    body = response.json()
    assert "nb_predictions" in body
    assert "prediction_distribution" in body
    assert "low_confidence_rate" in body


def test_monitoring_drift_endpoint_returns_report() -> None:
    client = TestClient(app)

    response = client.get("/monitoring/drift")

    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "nb_predictions_analyzed" in body


def test_monitoring_alerts_endpoint_returns_decision() -> None:
    client = TestClient(app)

    response = client.get("/monitoring/alerts")

    assert response.status_code == 200
    body = response.json()
    assert "decision" in body
    assert "retraining_recommended" in body
    assert "alerts" in body

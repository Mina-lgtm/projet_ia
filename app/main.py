from fastapi import Depends, FastAPI, HTTPException, status

from app.monitoring import (
    PredictionLogger,
    build_alert_report,
    build_drift_report,
    build_monitoring_report,
    get_prediction_logger,
)
from app.predictor import (
    ModelNotAvailableError,
    PredictionService,
    get_prediction_service,
)
from app.schemas import TravelPredictionRequest, TravelPredictionResponse


app = FastAPI(
    title="Examen IA API",
    description="API de prédiction pré-voyage pour le projet IA voyages.",
    version="0.2.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def get_predictor() -> PredictionService:
    try:
        return get_prediction_service()
    except ModelNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


def get_logger() -> PredictionLogger:
    return get_prediction_logger()


@app.post("/predict", response_model=TravelPredictionResponse)
def predict(
    payload: TravelPredictionRequest,
    predictor: PredictionService = Depends(get_predictor),
    logger: PredictionLogger = Depends(get_logger),
) -> TravelPredictionResponse:
    response = predictor.predict(payload)
    logger.log_prediction(payload, response)
    return response


@app.get("/monitoring/summary")
def monitoring_summary() -> dict:
    return build_monitoring_report()


@app.get("/monitoring/drift")
def monitoring_drift() -> dict:
    return build_drift_report()


@app.get("/monitoring/alerts")
def monitoring_alerts() -> dict:
    return build_alert_report()

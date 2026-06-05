from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler


class PredictionRequest(BaseModel):
    features: list[float] = Field(..., min_length=4, max_length=4)


class PredictionResponse(BaseModel):
    prediction: int
    label: str
    probabilities: dict[str, float]


model: Pipeline | None = None
labels: list[str] = []


def train_demo_model() -> tuple[Pipeline, list[str]]:
    dataset = load_iris()
    pipeline = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=300),
    )
    pipeline.fit(dataset.data, dataset.target)
    return pipeline, list(dataset.target_names)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, labels
    model, labels = train_demo_model()
    yield


app = FastAPI(
    title="Examen IA API",
    description="API de demarrage pour servir un modele IA.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    if model is None:
        raise RuntimeError("Le modele n'est pas initialise.")

    sample = np.array(payload.features).reshape(1, -1)
    prediction = int(model.predict(sample)[0])
    probabilities = model.predict_proba(sample)[0]

    return PredictionResponse(
        prediction=prediction,
        label=labels[prediction],
        probabilities={
            labels[index]: round(float(probability), 4)
            for index, probability in enumerate(probabilities)
        },
    )

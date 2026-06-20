from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.modeling import prepare_prediction_features
from app.schemas import (
    PredictionProbability,
    TravelPredictionRequest,
    TravelPredictionResponse,
)


DEFAULT_MODEL_PATH = Path("models/model_pre_voyage.pkl")
DEFAULT_METADATA_PATH = Path("models/model_pre_voyage_metadata.json")


class ModelNotAvailableError(RuntimeError):
    pass


class PredictionService:
    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        metadata_path: Path = DEFAULT_METADATA_PATH,
    ) -> None:
        if not model_path.exists():
            raise ModelNotAvailableError(
                f"Modèle introuvable: {model_path}. Exécuter `python train.py`."
            )
        if not metadata_path.exists():
            raise ModelNotAvailableError(
                f"Métadonnées introuvables: {metadata_path}. Exécuter `python train.py`."
            )

        self.model_path = model_path
        self.metadata_path = metadata_path
        self.model = joblib.load(model_path)
        self.metadata: dict[str, Any] = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )
        self.feature_columns = self.metadata["feature_columns"]
        self.class_names = self.metadata.get("class_names", [])
        self.objective = self.metadata.get("objective", "pre_voyage_satisfaction_3_classes")
        self.model_name = self.metadata.get("model_name", model_path.stem)
        self.model_metrics = self.metadata.get("metrics", {})

    def predict(self, request: TravelPredictionRequest) -> TravelPredictionResponse:
        input_df = pd.DataFrame([request.model_dump()])
        x = prepare_prediction_features(input_df, self.feature_columns)

        prediction = int(self.model.predict(x)[0])
        probabilities = self._predict_probabilities(x)

        return TravelPredictionResponse(
            objective=self.objective,
            model_name=self.model_name,
            classe_predite=prediction,
            libelle_prediction=self._label_for_class(prediction),
            probabilities=probabilities,
            model_metrics={
                key: float(value)
                for key, value in self.model_metrics.items()
                if isinstance(value, int | float)
            },
        )

    def _predict_probabilities(self, x: pd.DataFrame) -> list[PredictionProbability] | None:
        if not hasattr(self.model, "predict_proba"):
            return None

        probabilities = self.model.predict_proba(x)[0]
        classes = getattr(self.model, "classes_", range(len(probabilities)))

        return [
            PredictionProbability(
                classe=int(classe),
                libelle=self._label_for_class(int(classe)),
                probabilite=round(float(probability), 4),
            )
            for classe, probability in zip(classes, probabilities, strict=False)
        ]

    def _label_for_class(self, classe: int) -> str:
        if 0 <= classe < len(self.class_names):
            return str(self.class_names[classe])
        return str(classe)


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    model_path = Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    metadata_path = Path(os.getenv("MODEL_METADATA_PATH", str(DEFAULT_METADATA_PATH)))
    return PredictionService(model_path=model_path, metadata_path=metadata_path)


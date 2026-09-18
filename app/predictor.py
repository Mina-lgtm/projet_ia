from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.config import get_monitoring_rules
from app.modeling import CLASS_NAMES, POSITIVE_CLASS, prepare_prediction_features
from app.schemas import ClassProbability, TravelPredictionRequest, TravelPredictionResponse


DEFAULT_MODEL_PATH = Path("models/model_pre_voyage.pkl")
DEFAULT_METADATA_PATH = Path("models/model_pre_voyage_metadata.json")


class ModelNotAvailableError(RuntimeError):
    pass


class PredictionService:
    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH, metadata_path: Path = DEFAULT_METADATA_PATH) -> None:
        if not model_path.exists():
            raise ModelNotAvailableError(
                f"Modele introuvable: {model_path}. Executer `python train.py`."
            )
        if not metadata_path.exists():
            raise ModelNotAvailableError(
                f"Metadonnees introuvables: {metadata_path}. Executer `python train.py`."
            )

        self.model_path = model_path
        self.metadata_path = metadata_path
        self.model = joblib.load(model_path)
        self.metadata: dict[str, Any] = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.feature_columns = self.metadata["feature_columns"]
        self.objective = self.metadata.get("objective", "travelmind_satisfaction_binaire")
        self.model_name = self.metadata.get("model_name", model_path.stem)
        self.model_metrics = self.metadata.get("metrics", {})
        self.class_labels = [int(label) for label in self.metadata.get("class_labels", [0, 1])]
        class_names = self.metadata.get("class_names") or [CLASS_NAMES[label] for label in self.class_labels]
        self.class_names = {
            int(label): str(name)
            for label, name in zip(self.class_labels, class_names, strict=False)
        }

    def predict(self, request: TravelPredictionRequest) -> TravelPredictionResponse:
        input_df = pd.DataFrame([request.model_dump()])
        x = prepare_prediction_features(input_df, self.feature_columns)

        predicted_class = int(self.model.predict(x)[0])
        probabilities = self._predict_probabilities(x)
        confidence = float(max((item.probabilite for item in probabilities), default=0.0))
        low_confidence_threshold = float(get_monitoring_rules().get("low_confidence_threshold", 0.5))

        return TravelPredictionResponse(
            objective=self.objective,
            model_name=self.model_name,
            classe_predite=predicted_class,
            libelle_prediction=self.class_names.get(predicted_class, str(predicted_class)),
            probabilities=probabilities,
            confidence=round(confidence, 4),
            low_confidence=confidence < low_confidence_threshold,
            model_metrics={
                key: float(value)
                for key, value in self.model_metrics.items()
                if isinstance(value, int | float) and not isinstance(value, bool)
            },
        )

    def _predict_probabilities(self, x: pd.DataFrame) -> list[ClassProbability]:
        if hasattr(self.model, "predict_proba"):
            raw_probabilities = self.model.predict_proba(x)[0]
            model_classes = [int(label) for label in self.model.classes_]
            probability_by_class = {
                label: float(probability)
                for label, probability in zip(model_classes, raw_probabilities, strict=False)
            }
        else:
            predicted_class = int(self.model.predict(x)[0])
            probability_by_class = {label: 1.0 if label == predicted_class else 0.0 for label in self.class_labels}

        return [
            ClassProbability(
                classe=label,
                libelle=self.class_names.get(label, str(label)),
                probabilite=round(float(probability_by_class.get(label, 0.0)), 4),
            )
            for label in self.class_labels
        ]


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    model_path = Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    metadata_path = Path(os.getenv("MODEL_METADATA_PATH", str(DEFAULT_METADATA_PATH)))
    return PredictionService(model_path=model_path, metadata_path=metadata_path)

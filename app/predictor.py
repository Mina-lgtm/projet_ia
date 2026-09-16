from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.modeling import SATISFACTION_MAX, SATISFACTION_MIN, prepare_prediction_features
from app.schemas import (
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
        self.objective = self.metadata.get(
            "objective",
            "pre_voyage_satisfaction_score_regression",
        )
        self.model_name = self.metadata.get("model_name", model_path.stem)
        self.model_metrics = self.metadata.get("metrics", {})

    def predict(self, request: TravelPredictionRequest) -> TravelPredictionResponse:
        input_df = pd.DataFrame([request.model_dump()])
        x = prepare_prediction_features(input_df, self.feature_columns)

        raw_prediction = float(self.model.predict(x)[0])
        score = float(np.clip(raw_prediction, SATISFACTION_MIN, SATISFACTION_MAX))
        rounded_score = int(round(score))

        return TravelPredictionResponse(
            objective=self.objective,
            model_name=self.model_name,
            score_satisfaction_predit=round(score, 4),
            score_satisfaction_arrondi=rounded_score,
            interpretation=self._interpret_score(score),
            zone_incertitude=self._is_uncertain(score),
            model_metrics={
                key: float(value)
                for key, value in self.model_metrics.items()
                if isinstance(value, int | float)
            },
        )

    @staticmethod
    def _interpret_score(score: float) -> str:
        if score < 2.5:
            return "risque_insatisfaction"
        if score < 3.5:
            return "satisfaction_intermediaire"
        return "satisfaction_probable"

    @staticmethod
    def _is_uncertain(score: float) -> bool:
        return 2.5 <= score < 3.5


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    model_path = Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    metadata_path = Path(os.getenv("MODEL_METADATA_PATH", str(DEFAULT_METADATA_PATH)))
    return PredictionService(model_path=model_path, metadata_path=metadata_path)

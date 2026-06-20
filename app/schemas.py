from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TravelPredictionRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
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
        }
    )

    client_type: str = Field(..., min_length=1)
    budget_total: float = Field(..., gt=0)
    destination: str = Field(..., min_length=1)
    saison: str = Field(..., min_length=1)
    duree_jours: int = Field(..., gt=0, le=365)
    type_hebergement: str = Field(..., min_length=1)
    prix_vol: float = Field(..., ge=0)
    meteo_prevue: str = Field(..., min_length=1)
    activite_principale: str = Field(..., min_length=1)

    @field_validator(
        "client_type",
        "destination",
        "saison",
        "type_hebergement",
        "meteo_prevue",
        "activite_principale",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_budget_coherence(self) -> TravelPredictionRequest:
        if self.prix_vol > self.budget_total:
            raise ValueError("prix_vol ne peut pas être supérieur à budget_total")
        return self


class PredictionProbability(BaseModel):
    classe: int
    libelle: str
    probabilite: float


class TravelPredictionResponse(BaseModel):
    objective: str
    model_name: str
    classe_predite: int
    libelle_prediction: str
    probabilities: list[PredictionProbability] | None = None
    model_metrics: dict[str, float] = Field(default_factory=dict)


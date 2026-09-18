from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from app.config import get_allowed_categories, get_api_constraints


TEXT_NORMALIZATION = {
    "hotel": "h\u00f4tel",
    "h?tel": "h\u00f4tel",
    "hÃ´tel": "h\u00f4tel",
    "hÃƒÂ´tel": "h\u00f4tel",
    "ensoleille": "ensoleill\u00e9",
    "ensoleill?": "ensoleill\u00e9",
    "ensoleillÃ©": "ensoleill\u00e9",
    "ensoleillÃƒÂ©": "ensoleill\u00e9",
    "ete": "\u00e9t\u00e9",
    "?t?": "\u00e9t\u00e9",
    "Ã©tÃ©": "\u00e9t\u00e9",
    "ÃƒÂ©tÃƒÂ©": "\u00e9t\u00e9",
    "randonnee": "randonn\u00e9e",
    "randonn?e": "randonn\u00e9e",
    "randonnÃ©e": "randonn\u00e9e",
    "randonnÃƒÂ©e": "randonn\u00e9e",
    "dubai": "duba\u00ef",
    "duba?": "duba\u00ef",
    "dubaÃ¯": "duba\u00ef",
    "dubaÃƒÂ¯": "duba\u00ef",
}


class TravelPredictionRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_type": "couple",
                "budget_total": 4200,
                "destination": "rome",
                "saison": "printemps",
                "duree_jours": 7,
                "type_hebergement": "h\u00f4tel",
                "prix_vol": 650,
                "meteo_prevue": "ensoleill\u00e9",
                "activite_principale": "culture",
            }
        }
    )

    client_type: str = Field(..., min_length=1)
    budget_total: float = Field(...)
    destination: str = Field(..., min_length=1)
    saison: str = Field(..., min_length=1)
    duree_jours: int = Field(...)
    type_hebergement: str = Field(..., min_length=1)
    prix_vol: float = Field(...)
    meteo_prevue: str = Field(..., min_length=1)
    activite_principale: str = Field(..., min_length=1)

    @field_validator("budget_total", "prix_vol", "duree_jours")
    @classmethod
    def validate_numeric_business_rules(cls, value: float | int, info: ValidationInfo) -> float | int:
        constraints = get_api_constraints().get(info.field_name, {})
        min_value = constraints.get("min")
        max_value = constraints.get("max")
        if min_value is not None and value < min_value:
            raise ValueError(f"{info.field_name} doit etre >= {min_value}")
        if max_value is not None and value > max_value:
            raise ValueError(f"{info.field_name} doit etre <= {max_value}")
        return value

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
        normalized_value = value.strip().lower()
        return TEXT_NORMALIZATION.get(normalized_value, normalized_value)

    @field_validator(
        "client_type",
        "saison",
        "type_hebergement",
        "meteo_prevue",
        "activite_principale",
    )
    @classmethod
    def validate_known_category(cls, value: str, info: ValidationInfo) -> str:
        allowed_values = set(get_allowed_categories().get(info.field_name, []))
        if not allowed_values:
            return value
        if value not in allowed_values:
            expected_values = ", ".join(sorted(allowed_values))
            raise ValueError(
                f"{info.field_name} doit appartenir aux valeurs connues : {expected_values}"
            )
        return value

    @model_validator(mode="after")
    def validate_budget_coherence(self) -> TravelPredictionRequest:
        if self.prix_vol > self.budget_total:
            raise ValueError("prix_vol ne peut pas etre superieur a budget_total")
        return self


class ClassProbability(BaseModel):
    classe: int
    libelle: str
    probabilite: float


class TravelPredictionResponse(BaseModel):
    objective: str
    model_name: str
    classe_predite: int
    libelle_prediction: str
    probabilities: list[ClassProbability]
    confidence: float
    low_confidence: bool = False
    model_metrics: dict[str, float] = Field(default_factory=dict)

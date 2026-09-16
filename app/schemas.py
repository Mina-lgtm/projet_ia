from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from app.config import get_allowed_categories, get_api_constraints


TEXT_NORMALIZATION = {
    "hotel": "hôtel",
    "h?tel": "hôtel",
    "hã´tel": "hôtel",
    "hÃ´tel": "hôtel",
    "ensoleille": "ensoleillé",
    "ensoleill?": "ensoleillé",
    "ensoleillã©": "ensoleillé",
    "ensoleillÃ©": "ensoleillé",
    "ete": "été",
    "?t?": "été",
    "ã©tã©": "été",
    "Ã©tÃ©": "été",
    "randonnee": "randonnée",
    "randonn?e": "randonnée",
    "randonnã©e": "randonnée",
    "randonnÃ©e": "randonnée",
    "dubai": "dubaï",
    "duba?": "dubaï",
    "dubaã¯": "dubaï",
    "dubaÃ¯": "dubaï",
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
                "type_hebergement": "hôtel",
                "prix_vol": 650,
                "meteo_prevue": "ensoleillé",
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
    def validate_numeric_business_rules(
        cls,
        value: float | int,
        info: ValidationInfo,
    ) -> float | int:
        constraints = get_api_constraints().get(info.field_name, {})
        min_value = constraints.get("min")
        max_value = constraints.get("max")

        if min_value is not None and value < min_value:
            raise ValueError(f"{info.field_name} doit être >= {min_value}")
        if max_value is not None and value > max_value:
            raise ValueError(f"{info.field_name} doit être <= {max_value}")

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
            raise ValueError("prix_vol ne peut pas être supérieur à budget_total")
        return self


class TravelPredictionResponse(BaseModel):
    objective: str
    model_name: str
    score_satisfaction_predit: float
    score_satisfaction_arrondi: int
    interpretation: str
    zone_incertitude: bool = False
    model_metrics: dict[str, float] = Field(default_factory=dict)

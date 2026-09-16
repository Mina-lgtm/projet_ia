import json

from app.config import load_business_rules


def test_load_business_rules_merges_project_defaults(tmp_path) -> None:
    config_path = tmp_path / "business_rules.json"
    config_path.write_text(
        json.dumps({
            "api_constraints": {
                "duree_jours": {
                    "max": 120,
                },
            },
        }),
        encoding="utf-8",
    )

    rules = load_business_rules(config_path)

    assert rules["api_constraints"]["duree_jours"]["min"] == 1
    assert rules["api_constraints"]["duree_jours"]["max"] == 120
    assert "client_type" in rules["allowed_categories"]
    assert "numeric_warning_threshold" in rules["monitoring"]

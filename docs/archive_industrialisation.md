# Industrialisation TravelMind

## Objectif

Ce document synthétise l'industrialisation active du projet TravelMind. Le modèle servi est le modèle **pré-voyage** `LogisticRegression_pre`, entraîné pour prédire la satisfaction client en 3 classes avant le départ.

## Périmètre synchronisé

| Brique | Fichier | Rôle |
| --- | --- | --- |
| Entraînement | `train.py` | Rejouer l'entraînement à partir du CSV brut et exporter les artefacts. |
| Pipeline ML | `app/modeling.py` | Nettoyage, feature engineering, split, preprocessing, entraînement et métadonnées. |
| API | `app/main.py` | Exposer `/health`, `/predict` et les endpoints de monitoring. |
| Prédiction | `app/predictor.py` | Charger le modèle exporté et préparer les features avant prédiction. |
| Schémas | `app/schemas.py` | Valider les entrées pré-voyage avec Pydantic. |
| Monitoring | `app/monitoring.py` | Journaliser les prédictions, mesurer la confiance et suivre la dérive. |
| Tests | `tests/` | Vérifier API, pipeline, monitoring et préparation modèle. |
| CI/CD | `.github/workflows/ci-cd.yml` | Compiler, tester, entraîner, contrôler le quality gate et construire Docker. |

## Modèle industrialisé

- Objectif : `pre_voyage_satisfaction_3_classes`.
- Modèle retenu : `LogisticRegression_pre`.
- Artefacts : `models/model_pre_voyage.pkl` et `models/model_pre_voyage_metadata.json`.
- Entrées API : `client_type`, `budget_total`, `destination`, `saison`, `duree_jours`, `type_hebergement`, `prix_vol`, `meteo_prevue`, `activite_principale`.
- Features dérivées recalculées automatiquement : `budget_par_jour`, `part_vol_budget`, `sejour_long`, `meteo_risque`, `client_business`, `hebergement_luxe`.
- Variables exclues pour éviter la fuite de données : `imprevus`, `reorganisation_necessaire`, `respect_budget`, `retour_client` et features post-voyage associées.

## Résultats synchronisés

| Métrique | Valeur |
| --- | ---: |
| `accuracy` | 0.3536 |
| `balanced_accuracy` | 0.3528 |
| `macro_f1` | 0.3462 |
| `train_rows` | 1119 |
| `test_rows` | 280 |

Ces résultats correspondent au notebook final `notebooks/exam_ia.ipynb` et au fichier `models/model_pre_voyage_metadata.json` régénéré.

## Commandes utiles

```powershell
python train.py
python -m pytest -q
python scripts/check_model_quality.py
uvicorn app.main:app --reload --port 8001
python -m streamlit run app_web.py
```

## Limites

- Le déploiement distant automatique n'est pas activé.
- Le modèle pré-voyage reste indicatif, car le signal métier disponible avant départ est faible.
- Le réentraînement est documenté mais reste soumis à validation métier et technique.

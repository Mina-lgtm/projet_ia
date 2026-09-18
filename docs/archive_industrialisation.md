# Industrialisation TravelMind

## Objectif

Ce document synth?tise l'industrialisation active du projet TravelMind. La version industrialis?e correspond au notebook final `notebooks/exam_ia_final.ipynb`. L'ancien notebook `notebooks/exam_ia.ipynb` est conserv? comme archive de travail.

Apr?s nettoyage strict du dataset, le meilleur r?sultat statistique est obtenu par la baseline `Dummy_mean_regression`. Cette situation est document?e comme une limite forte : le pipeline est industrialisable techniquement, mais le mod?le ne doit pas ?tre utilis? comme aide ? la d?cision en production sans enrichissement de donn?es r?elles pr?-voyage.

## P?rim?tre synchronis?

| Brique | Fichier | R?le |
| --- | --- | --- |
| Entra?nement | `train.py` | Rejouer l'entra?nement ? partir du CSV brut et exporter les artefacts. |
| Pipeline ML | `app/modeling.py` | Nettoyage, feature engineering, split, preprocessing, entra?nement et m?tadonn?es. |
| API | `app/main.py` | Exposer `/health`, `/predict` et les endpoints de monitoring. |
| Pr?diction | `app/predictor.py` | Charger le mod?le export? et pr?parer les features avant pr?diction. |
| Sch?mas | `app/schemas.py` | Valider les entr?es pr?-voyage avec Pydantic. |
| Configuration m?tier | `configs/business_rules.json` | Centraliser les bornes, cat?gories autoris?es, r?gles de feature engineering et seuils de monitoring. |
| Monitoring | `app/monitoring.py` | Journaliser les pr?dictions, suivre la zone d'incertitude et mesurer la d?rive. |
| Tests | `tests/` | V?rifier API, pipeline, monitoring et pr?paration mod?le. |
| CI/CD | `.github/workflows/ci-cd.yml` | D?tecter les fichiers modifi?s, tester, entra?ner, contr?ler le quality gate et construire Docker si n?cessaire. |

## Mod?le export?

- Objectif : `pre_voyage_satisfaction_score_regression`.
- Meilleur r?sultat statistique actuel : `Dummy_mean_regression`.
- Artefacts : `models/model_pre_voyage.pkl` et `models/model_pre_voyage_metadata.json`.
- Entr?es API : `client_type`, `budget_total`, `destination`, `saison`, `duree_jours`, `type_hebergement`, `prix_vol`, `meteo_prevue`, `activite_principale`.
- Features d?riv?es recalcul?es automatiquement : `budget_par_jour`, `part_vol_budget`, `sejour_long`, `meteo_risque`, `client_business`, `hebergement_luxe`.
- Variables exclues pour ?viter la fuite de donn?es : `imprevus`, `reorganisation_necessaire`, `respect_budget`, `retour_client` et features post-voyage associ?es.

## R?sultats synchronis?s

| M?trique | Valeur |
| --- | ---: |
| `MAE` | 1.0636 |
| `RMSE` | 1.2522 |
| `R2` | -0.0001 |
| `gain MAE vs baseline` | 0.0000 |
| `train_rows` | 1102 |
| `test_rows` | 276 |

Ces r?sultats correspondent au notebook final `notebooks/exam_ia_final.ipynb` et au fichier `models/model_pre_voyage_metadata.json` r?g?n?r?.

## Commandes utiles

```powershell
python train.py
python -m pytest -q
python scripts/check_model_quality.py
uvicorn app.main:app --reload --port 8001
python -m streamlit run app_web.py
```

## Limites

- Le d?ploiement distant automatique n'est pas activ?.
- Le mod?le pr?-voyage reste indicatif, car le signal m?tier disponible avant d?part est faible.
- La baseline ?tant la meilleure apr?s nettoyage strict, la solution ne doit pas ?tre pr?sent?e comme une aide ? la d?cision fiable.
- Le r?entra?nement est document? mais reste soumis ? validation m?tier et technique.

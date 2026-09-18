# TravelMind

Solution IA de personnalisation de séjours et d'anticipation de la satisfaction client pour une agence de voyages haut de gamme.

TravelMind couvre le cadrage métier, la préparation des données, la modélisation pré-voyage et post-voyage, puis l'industrialisation progressive : entraînement reproductible, export du modèle, API, interface web, monitoring et réentraînement contrôlé.

## Documents principaux

- Documentation descriptive : `docs/etat_projet.md`
- Objectif 1 - identification du dataset : `docs/objectif_1_dataset.md`
- Synthèse finale pré/post-voyage : `docs/synthese_finale_pre_post_voyage.md`
- Notebook final industrialisé : `notebooks/exam_ia_final.ipynb`
- Ancienne version conservée : `notebooks/exam_ia.ipynb`
- Expériences de modélisation : `docs/experiences_modelisation.md`
- Archive industrialisation : `docs/archive_industrialisation.md`
- Stratégie de réentraînement : `docs/strategie_reentrainement.md`
- Plan de documentation : `docs/plan_documentation.md`
- Versioning des données : `docs/data_versioning.md`

## Environnement local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

## Notebook Jupyter

```powershell
.\.venv\Scripts\Activate.ps1
jupyter lab
```

Notebook recommandé pour la version finale :

```text
notebooks/exam_ia_final.ipynb
```

L'ancien notebook `notebooks/exam_ia.ipynb` est conservé comme archive de la version précédente.

## TravelMind API

TravelMind API expose un endpoint de santé et un endpoint de prédiction pré-voyage.
Avant d'appeler `/predict`, générer le modèle localement :

```powershell
python train.py
```

```powershell
uvicorn app.main:app --reload --port 8001
```

URLs :

```text
http://localhost:8001/health
http://localhost:8001/predict
```

Contraintes principales de l'API :

- `duree_jours` doit être compris entre `1` et `90` jours ;
- `prix_vol` ne peut pas dépasser `budget_total` ;
- `client_type`, `saison`, `type_hebergement`, `meteo_prevue` et `activite_principale` doivent correspondre aux catégories métier connues du dataset ;
- `destination` reste ouverte afin de permettre la saisie de nouvelles destinations, avec une fiabilité à surveiller via le monitoring.

Ces règles sont centralisées dans `configs/business_rules.json`. Pour ajuster une borne, ajouter une catégorie ou modifier un seuil de monitoring, il faut modifier ce fichier puis relancer :

```powershell
python train.py
python -m pytest -q
```

## TravelMind Dashboard

TravelMind Dashboard permet de tester le modèle sans écrire de requête API à
la main. Elle permet :

- de saisir un voyage dans un formulaire ;
- d'importer un CSV de voyages ;
- d'afficher le score de satisfaction prédit entre 1 et 5 ;
- de consulter un dashboard KPI métier ;
- de consulter les endpoints de monitoring.

Lancer d'abord l'API dans un terminal :

```powershell
uvicorn app.main:app --reload --port 8001
```

Puis lancer l'interface dans un deuxième terminal :

```powershell
python -m streamlit run app_web.py
```

URL locale Streamlit :

```text
http://localhost:8501
```

Exemple de prédiction :

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8001/predict `
  -ContentType "application/json" `
  -Body '{
    "client_type": "couple",
    "budget_total": 4200,
    "destination": "rome",
    "saison": "printemps",
    "duree_jours": 7,
    "type_hebergement": "hôtel",
    "prix_vol": 650,
    "meteo_prevue": "ensoleillé",
    "activite_principale": "culture"
  }'
```

## Entra?nement reproductible

Le script `train.py` entra?ne le mod?le industrialis? `LogisticRegression` sur le dataset enrichi final `data/versions/v2_2_signal_enrichment/dataset_final.csv`. La cible est binaire :

- `0` = `non_satisfait_1_2_3` ;
- `1` = `satisfait_4_5`.

Le script applique le nettoyage m?tier, le feature engineering pr?-voyage, le pipeline scikit-learn et exporte les artefacts dans `models/`.

```powershell
python train.py
```

Artefacts g?n?r?s :

```text
models/model_pre_voyage.pkl
models/model_pre_voyage_metadata.json
```

Le dossier `models/` est ignor? par Git afin d'?viter de versionner des artefacts locaux lourds.

## Monitoring initial

Chaque appel r?ussi ? `/predict` est enregistr? dans un fichier JSONL local :

```text
logs/predictions/predictions.jsonl
```

Chaque ligne contient la date UTC, les entr?es pr?-voyage, la classe pr?dite, les probabilit?s par classe, la confiance, l'indicateur `low_confidence` et les m?triques globales du mod?le.

Lire les derniers logs :

```powershell
Get-Content -Encoding UTF8 logs/predictions/predictions.jsonl -Tail 5
```

Un r?sum? de monitoring est disponible via l'API :

```text
http://localhost:8001/monitoring/summary
```

Il retourne notamment :

- `nb_predictions` : nombre d'appels `/predict` journalis?s ;
- `prediction_distribution` : nombre de pr?dictions par classe m?tier ;
- `prediction_distribution_pct` : pourcentage par classe pr?dite ;
- `low_confidence_rate` : part des pr?dictions ? faible confiance ;
- `average_confidence` : confiance moyenne des pr?dictions ;
- `model_distribution` : mod?les utilis?s dans les logs.

Un contr?le simple de d?rive des donn?es est disponible via :

```text
http://localhost:8001/monitoring/drift
```

Ce contr?le compare les entr?es API journalis?es avec le profil statistique du jeu d'entra?nement stock? dans `models/model_pre_voyage_metadata.json`. Il retourne :

- `numeric_drift` : ?cart moyen normalis? des variables num?riques ;
- `categorical_drift` : ?cart de distribution des variables cat?gorielles ;
- `alerts` : variables en niveau `warning` ou `critical` ;
- `sample_size_warning` : vrai si le volume de pr?dictions est encore trop faible.

Apr?s une modification de `train.py`, du dataset ou du pipeline, r?g?n?rer le mod?le pour mettre ? jour le profil de r?f?rence :

```powershell
python train.py
```

Un endpoint d'alertes consolide le monitoring et la d?rive :

```text
http://localhost:8001/monitoring/alerts
```

Il retourne une d?cision op?rationnelle :

- `collect_predictions` : volume insuffisant ou aucun log ;
- `monitor_and_review` : surveillance et revue humaine n?cessaires ;
- `review_and_prepare_retraining` : pr?parer un r?entra?nement apr?s validation m?tier ;
- `no_action` : pas d'alerte significative.

## Docker

Générer d'abord le modèle localement, car `docker-compose.yml` monte `./models`
dans le conteneur en lecture seule. Le dossier `./logs` est aussi monté pour
conserver les traces de prédiction.

```powershell
python train.py
docker compose up --build
```

API Docker :

```text
http://localhost:8001/health
http://localhost:8001/predict
http://localhost:8001/monitoring/summary
http://localhost:8001/monitoring/drift
http://localhost:8001/monitoring/alerts
```

## CI/CD et versioning

Le projet utilise Git et GitHub pour versionner le code, la documentation, le dataset synth?tique, les notebooks et les fichiers de configuration.

Un workflow GitHub Actions est d?fini dans `.github/workflows/ci-cd.yml`. Il d?tecte les fichiers modifi?s et lance uniquement les contr?les utiles :

- changements `app/`, `tests/`, `scripts/`, `train.py` ou `configs/` : compilation Python et tests `pytest` ;
- changements mod?le, donn?es ou configuration : entra?nement CI et quality gate ;
- changement `notebooks/exam_ia_final.ipynb` : validation de la structure et de la syntaxe des cellules code ;
- changements `Dockerfile`, `docker-compose.yml`, `app/`, `configs/`, `requirements.txt` ou `models/` : build Docker ;
- changement purement documentaire : ?tapes lourdes ignor?es.

Le contr?le qualit? bloque la CI si les m?triques du mod?le binaire ne respectent pas les seuils d?finis dans `configs/model_quality_gate.json` : `accuracy`, `balanced_accuracy`, `macro_f1`, `roc_auc`, `precision_satisfait`, `recall_satisfait` et volume minimal train/test.

Ce workflow met en place une livraison continue minimale et optimis?e : le projet est automatiquement v?rifi?, mais le mod?le n'est r??valu? et l'image Docker n'est reconstruite que lorsque les changements le justifient. Le d?ploiement vers un environnement distant reste volontairement non activ? tant que le prototype n'est pas valid? m?tier.

## Tests

```powershell
pytest -q
```

Les tests actuels vérifient le socle API minimal et la préparation du pipeline modèle.

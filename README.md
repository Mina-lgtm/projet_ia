# TravelMind

Solution IA de personnalisation de séjours et d'anticipation de la satisfaction client pour une agence de voyages haut de gamme.

TravelMind couvre le cadrage métier, la préparation des données, la modélisation pré-voyage et post-voyage, puis l'industrialisation progressive : entraînement reproductible, export du modèle, API, interface web, monitoring et réentraînement contrôlé.

## Documents principaux

- Documentation descriptive : `docs/etat_projet.md`
- Objectif 1 - identification du dataset : `docs/objectif_1_dataset.md`
- Synthèse finale pré/post-voyage : `docs/synthese_finale_pre_post_voyage.md`
- Notebook rattrapage industrialisé : `notebooks/exam_ia_rattrapage.ipynb`
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

Notebook recommandé pour la version rattrapage :

```text
notebooks/exam_ia_rattrapage.ipynb
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

## Entraînement reproductible

Le script `train.py` entraîne le modèle pré-voyage de régression à partir du dataset brut, applique les règles de nettoyage métier, exclut les variables connues uniquement après le séjour, construit le pipeline scikit-learn et exporte les artefacts dans `models/`.

```powershell
python train.py
```

Artefacts générés :

```text
models/model_pre_voyage.pkl
models/model_pre_voyage_metadata.json
```

Le dossier `models/` est ignoré par Git afin d'éviter de versionner des artefacts locaux lourds.

## Monitoring initial

Chaque appel réussi à `/predict` est enregistré dans un fichier JSONL local :

```text
logs/predictions/predictions.jsonl
```

Chaque ligne contient la date UTC, les entrées pré-voyage, le score de satisfaction prédit,
le score arrondi, l'interprétation métier, un indicateur de zone d'incertitude et les
métriques globales du modèle.

Lire les derniers logs :

```powershell
Get-Content -Encoding UTF8 logs/predictions/predictions.jsonl -Tail 5
```

Un résumé de monitoring est aussi disponible via l'API :

```text
http://localhost:8001/monitoring/summary
```

Il retourne notamment :

- `nb_predictions` : nombre d'appels `/predict` journalisés ;
- `prediction_distribution` : nombre de prédictions par interprétation métier ;
- `prediction_distribution_pct` : pourcentage par interprétation prédite ;
- `low_confidence_rate` : part des prédictions en zone d'incertitude ;
- `average_predicted_score` : score moyen prédit ;
- `model_distribution` : modèles utilisés dans les logs.

Un contrôle simple de dérive des données est disponible via :

```text
http://localhost:8001/monitoring/drift
```

Ce contrôle compare les entrées API journalisées avec le profil statistique du
jeu d'entraînement stocké dans `models/model_pre_voyage_metadata.json`.
Il retourne :

- `numeric_drift` : écart moyen normalisé des variables numériques ;
- `categorical_drift` : écart de distribution des variables catégorielles ;
- `alerts` : variables en niveau `warning` ou `critical` ;
- `sample_size_warning` : vrai si le volume de prédictions est encore trop faible.

Après une modification de `train.py` ou du pipeline, régénérer le modèle pour
mettre à jour le profil de référence :

```powershell
python train.py
```

Un endpoint d'alertes consolide le monitoring et la dérive :

```text
http://localhost:8001/monitoring/alerts
```

Il retourne une décision opérationnelle :

- `collect_predictions` : volume insuffisant ou aucun log ;
- `monitor_and_review` : surveillance et revue humaine nécessaires ;
- `review_and_prepare_retraining` : préparer un réentraînement après validation métier ;
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

Le projet utilise Git et GitHub pour versionner le code, la documentation, le dataset synthétique et les notebooks.

Un workflow GitHub Actions est défini dans `.github/workflows/ci-cd.yml`. Il détecte les fichiers modifiés et lance uniquement les contrôles utiles :

- changements `app/`, `tests/`, `scripts/`, `train.py` ou `configs/` : compilation Python et tests `pytest` ;
- changements modèle, données ou configuration : entraînement CI et quality gate ;
- changement `notebooks/exam_ia_rattrapage.ipynb` : validation de la structure et de la syntaxe des cellules code ;
- changements `Dockerfile`, `docker-compose.yml`, `app/`, `configs/`, `requirements.txt` ou `models/` : build Docker ;
- changement purement documentaire : étapes lourdes ignorées.

Le contrôle qualité bloque la CI si les métriques du modèle ne respectent pas les seuils de régression : `MAE` et `RMSE` maximums, `R2` minimum, volume train/test minimal.

Ce workflow met en place une livraison continue minimale et optimisée : le projet est automatiquement vérifié, mais le modèle n'est réévalué et l'image Docker n'est reconstruite que lorsque les changements le justifient. Le déploiement vers un environnement distant reste volontairement non activé tant que le notebook rattrapage et le pipeline modèle ne sont pas figés.

## Tests

```powershell
pytest -q
```

Les tests actuels vérifient le socle API minimal et la préparation du pipeline modèle.

# Examen IA

Projet IA de planification de voyages.

La phase d'industrialisation est reprise progressivement à partir du notebook final : architecture cible, entraînement reproductible, export du modèle, API, monitoring et réentraînement contrôlé.

## Documents principaux

- Documentation descriptive : `docs/etat_projet.md`
- Objectif 1 - identification du dataset : `docs/objectif_1_dataset.md`
- Synthèse finale pré/post-voyage : `docs/synthese_finale_pre_post_voyage.md`
- Notebook final propre : `notebooks/00_notebook_final_pre_post_voyage.ipynb`
- Expériences de modélisation : `docs/experiences_modelisation.md`
- Archive industrialisation : `docs/archive_industrialisation.md`
- Stratégie de réentraînement : `docs/strategie_reentrainement.md`
- Plan de documentation : `docs/plan_documentation.md`

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

Notebook final recommandé :

```text
notebooks/00_notebook_final_pre_post_voyage.ipynb
```

## API de prédiction

L'API FastAPI expose un endpoint de santé et un endpoint de prédiction pré-voyage.
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

## Interface web Streamlit

Une interface web locale permet de tester le modèle sans écrire de requête API à
la main. Elle permet :

- de saisir un voyage dans un formulaire ;
- d'importer un CSV de voyages ;
- d'afficher les probabilités de prédiction ;
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

Le script `train.py` entraîne le modèle pré-voyage 3 classes à partir du dataset brut, applique les règles de nettoyage métier, exclut les variables connues uniquement après le séjour, construit le pipeline scikit-learn et exporte les artefacts dans `models/`.

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

Chaque ligne contient la date UTC, les entrées pré-voyage, la classe prédite,
les probabilités, la confiance maximale, un indicateur `low_confidence` et les
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
- `prediction_distribution` : nombre de prédictions par classe ;
- `prediction_distribution_pct` : pourcentage par classe prédite ;
- `low_confidence_rate` : part des prédictions avec confiance `< 50 %` ;
- `average_confidence` : confiance moyenne des prédictions ;
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

Un workflow GitHub Actions est défini dans `.github/workflows/ci-cd.yml`. À chaque push ou pull request vers `main`, il :

- installe les dépendances ;
- valide la syntaxe Python ;
- exécute les tests API ;
- exécute les tests du pipeline de préparation et d'entraînement ;
- vérifie la structure et la syntaxe des cellules code du notebook final ;
- construit l'image Docker.

Ce workflow met en place une livraison continue minimale : le projet est automatiquement vérifié et packagé sous forme d'image Docker. Le déploiement vers un environnement distant reste volontairement non activé tant que le notebook final et le pipeline modèle ne sont pas figés.

## Tests

```powershell
pytest -q
```

Les tests actuels vérifient le socle API minimal et la préparation du pipeline modèle.

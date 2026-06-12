# Examen IA

Projet IA conteneurise avec FastAPI, scikit-learn et Docker.

Documentation descriptive : `docs/etat_projet.md`

Objectif 1 - identification du dataset : `docs/objectif_1_dataset.md`

Plan de documentation : `docs/plan_documentation.md`

## Environnement local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001
```

API locale : http://localhost:8001/docs

## Notebook Jupyter

```powershell
.\.venv\Scripts\Activate.ps1
jupyter lab
```

Notebook de demarrage : `notebooks/01_exploration.ipynb`

Si le kernel Jupyter se ferme pendant les imports, arrete temporairement Docker
pour liberer de la memoire :

```powershell
docker compose stop
```

## Docker

```powershell
docker compose up --build
```

API Docker : http://localhost:8001/docs

## Exemple de prediction

```powershell
curl -X POST http://localhost:8001/predict `
  -H "Content-Type: application/json" `
  -d "{\"features\":[5.1,3.5,1.4,0.2]}"
```

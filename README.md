# Examen IA

Projet IA de planification de voyages.

La phase d'industrialisation a ete archivee temporairement afin de continuer a
enrichir le notebook final.

## Documents principaux

- Documentation descriptive : `docs/etat_projet.md`
- Objectif 1 - identification du dataset : `docs/objectif_1_dataset.md`
- Synthese finale pre/post-voyage : `docs/synthese_finale_pre_post_voyage.md`
- Notebook final propre : `notebooks/00_notebook_final_pre_post_voyage.ipynb`
- Experiences de modelisation : `docs/experiences_modelisation.md`
- Archive industrialisation : `docs/archive_industrialisation.md`
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

Notebook final recommande :

```text
notebooks/00_notebook_final_pre_post_voyage.ipynb
```

## API minimale

Une API FastAPI minimale est conservee uniquement pour garder le socle Docker
fonctionnel pendant la finalisation du notebook.

```powershell
uvicorn app.main:app --reload --port 8001
```

URL :

```text
http://localhost:8001/health
```

## Docker

```powershell
docker compose up --build
```

API Docker :

```text
http://localhost:8001/health
```

## Tests

Les tests d'industrialisation ont ete retires temporairement avec l'API modele.
Ils pourront etre restaures quand le notebook final sera fige.

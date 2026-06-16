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

## CI/CD et versioning

Le projet utilise Git et GitHub pour versionner le code, la documentation, le
dataset synthetique et les notebooks.

Un workflow GitHub Actions est defini dans `.github/workflows/ci-cd.yml`. A
chaque push ou pull request vers `main`, il :

- installe les dependances ;
- valide la syntaxe Python ;
- execute les tests API ;
- verifie la structure et la syntaxe des cellules code du notebook final ;
- construit l'image Docker.

Ce workflow met en place une livraison continue minimale : le projet est
automatiquement verifie et packagé sous forme d'image Docker. Le deploiement
vers un environnement distant reste volontairement non active tant que le
notebook final et le pipeline modele ne sont pas figes.

## Tests

```powershell
pytest -q
```

Les tests actuels verifient le socle API minimal. Les tests du pipeline modele
seront ajoutes lorsque l'industrialisation sera restauree.

# Examen IA

Projet IA conteneurise avec FastAPI, scikit-learn et Docker.

## Environnement local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001
```

API locale : http://localhost:8001/docs

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

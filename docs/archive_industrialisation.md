---
noteId: "273e88c0676a11f1ac6d875fbf061d80"
tags: []

---

# Archive de l'industrialisation

## Objectif du document

Ce document conserve la trace de l'industrialisation realisee dans le projet.

Il permet de :

- documenter ce qui a ete mis en place ;
- expliquer les choix techniques ;
- conserver une preuve de faisabilite ;
- pouvoir revenir plus tard a l'industrialisation sans repartir de zero.

Cette archive est utile si le notebook final continue d'evoluer avant de figer
definitivement le modele.

Statut au 13 juin 2026 : l'industrialisation a ete supprimee temporairement du
code actif du projet. Cette archive reste la reference pour la restaurer plus
tard.

## Perimetre couvert

L'industrialisation mise en place couvre :

| Etape | Statut | Description |
| --- | --- | --- |
| Donnees | Fait | Chargement, nettoyage, controle de coherence et feature engineering |
| Entrainement | Fait | Script reproductible d'entrainement |
| Validation | Fait | Train/test, metriques, tests automatises |
| Export modele | Fait | Export du pipeline entraine avec `joblib` |
| API | Fait | TravelMind API avec endpoint de prediction |
| Docker | Fait | Execution conteneurisee via Docker Compose |
| Monitoring | Fait | Logs de predictions et controle simple de derive |
| Reentrainement continu | Partiel | Script pret, automatisation planifiee non mise en place |

## Fichiers principaux crees ou modifies

### Pipeline modele

```text
app/modeling.py
```

Role :

- charger le dataset ;
- nettoyer les donnees ;
- creer les features ;
- exclure les variables retirees du modele ;
- construire le preprocesseur ;
- entrainer le modele `ExtraTrees_3_classes` ;
- produire un profil de reference pour le monitoring.

Variables explicitement exclues du modele :

- `budget_hors_vol` ;
- `saison_haute` ;
- `cout_vie_destination` ;
- `type_destination` ;
- `decalage_horaire_categorie` ;
- `risque_meteo_destination` ;
- `annulation_et_reorganisation` ;
- `retard_et_budget_non_respecte` ;
- `imprevu_transport_et_sejour_court` ;
- `budget_tendu_et_hebergement_luxe`.

### Script d'entrainement

```text
scripts/train_post_voyage_model.py
```

Commande :

```powershell
python scripts/train_post_voyage_model.py
```

Sorties :

- `models/post_voyage_model.joblib` ;
- `models/post_voyage_metrics.json`.

### TravelMind API

```text
app/main.py
```

Endpoints crees :

| Endpoint | Role |
| --- | --- |
| `/health` | Verifier que l'API et le modele sont charges |
| `/predict` | Predire la satisfaction post-voyage |
| `/monitoring/summary` | Resumer les predictions journalisees |
| `/monitoring/drift` | Detecter une derive simple par rapport au profil train |

### Monitoring

```text
app/monitoring.py
```

Role :

- journaliser les predictions dans `logs/predictions.jsonl` ;
- lire les logs ;
- compter les predictions par classe ;
- comparer les nouvelles donnees au profil de reference.

### Tests automatises

```text
tests/
```

Tests ajoutes :

- `tests/test_modeling.py` ;
- `tests/test_api.py` ;
- `tests/test_monitoring.py`.

Commande :

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Resultat obtenu :

```text
5 passed
```

### Configuration

Fichiers ajoutes ou modifies :

- `.env.example` ;
- `.gitignore` ;
- `.dockerignore` ;
- `Dockerfile` ;
- `docker-compose.yml` ;
- `requirements.txt` ;
- `requirements-dev.txt` ;
- `scripts/project.ps1`.

## Resultats du modele industrialise

Modele exporte :

```text
ExtraTrees_3_classes
```

Metriques apres suppression des features retirees :

| Metrique | Valeur |
| --- | ---: |
| `accuracy` | 0.4346 |
| `balanced_accuracy` | 0.3955 |
| `macro_f1` | 0.3939 |

Volume utilise :

| Jeu | Nombre de lignes |
| --- | ---: |
| Train | 1131 |
| Test | 283 |
| Total | 1414 |

## Commandes utiles

### Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

### Entrainement

```powershell
python scripts/train_post_voyage_model.py
```

### API locale

```powershell
uvicorn app.main:app --reload --port 8001
```

### Docker

```powershell
docker compose up --build
```

### Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Limites de cette industrialisation

- Le reentrainement continu n'est pas automatise.
- Les logs sont stockes en fichier local, pas en base de donnees.
- Le monitoring de derive est volontairement simple.
- Il n'y a pas encore d'authentification API.
- Le modele reste un prototype, avec performance moderee.

## Strategie recommandee si le notebook final evolue

Pendant que le notebook continue d'etre enrichi :

1. conserver cette archive comme trace de l'industrialisation ;
2. travailler librement dans le notebook final ;
3. ne resynchroniser `app/modeling.py` qu'une fois le modele definitif fige ;
4. regenerer ensuite le modele exporte ;
5. relancer les tests ;
6. remettre a jour la documentation finale.

## Option d'annulation temporaire

Si l'objectif est de revenir a une phase notebook uniquement, il est possible de
mettre l'industrialisation de cote.

Deux approches sont possibles :

### Option A - Non destructive

Conserver les fichiers d'industrialisation dans le projet, mais ne plus les
modifier pendant l'evolution du notebook.

Avantage :

- aucune perte de travail ;
- restauration immediate possible.

### Option B - Suppression des fichiers d'industrialisation

Supprimer temporairement :

- `app/modeling.py` ;
- `app/monitoring.py` ;
- `scripts/train_post_voyage_model.py` ;
- `scripts/project.ps1` ;
- `tests/` ;
- `docs/industrialisation_api.md` ;
- `docs/demarrage_projet.md` ;
- `.env.example` ;
- les modifications Docker/API associees.

Avantage :

- le projet redevient centre sur le notebook.

Inconvenient :

- il faudra restaurer ou refaire l'industrialisation plus tard.

## Recommandation

L'option recommandee est l'option A.

Elle permet de continuer a enrichir le notebook final sans perdre le travail
d'industrialisation deja realise.

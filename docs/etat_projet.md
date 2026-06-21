# Documentation descriptive du projet IA

Date de reference : 5 juin 2026.

Ce document explique ce qui a ete mis en place dans le projet `Examen_IA`,
mais aussi la raison et l'objectif de chaque element. Il sert de trace de
conception pour comprendre les choix techniques et reprendre le projet sans
perdre le contexte.

## 1. Objectif global du projet

Le projet vise a construire progressivement une application IA autour d'un
dataset de planification de voyage.

L'objectif final est de passer par toutes les etapes classiques d'un projet IA :

1. preparer un environnement de developpement propre ;
2. organiser le code, les donnees et les notebooks ;
3. explorer un dataset CSV ;
4. entrainer un premier modele ;
5. evaluer ce modele avec des metriques ;
6. exposer le modele via une API ;
7. conteneuriser l'application avec Docker ;
8. versionner le projet avec Git et GitHub.

## 2. Vue d'ensemble des elements

| Element | Pourquoi on l'a ajoute | Objectif |
| --- | --- | --- |
| `.venv` | Isoler les bibliotheques du projet | Eviter les conflits avec les autres projets Python |
| `requirements.txt` | Declarer les dependances de production | Reinstaller facilement l'environnement runtime |
| `requirements-dev.txt` | Declarer les outils de developpement | Travailler avec Jupyter, tests, linting et visualisations |
| `app/main.py` | Creer une API de demarrage | Tester l'exposition d'un modele IA via HTTP |
| `Dockerfile` | Construire une image Docker | Rendre l'application portable et reproductible |
| `docker-compose.yml` | Lancer le service plus simplement | Gerer le conteneur API avec une commande unique |
| `.dockerignore` | Exclure les fichiers inutiles de l'image | Accelerer les builds et alleger le contexte Docker |
| `.gitignore` | Eviter de versionner les fichiers locaux | Garder Git propre et ne pas envoyer `.venv`, caches, `.env` |
| `.gitattributes` | Stabiliser les fins de ligne | Eviter les problemes Windows/Linux dans Git |
| `README.md` | Donner les commandes essentielles | Servir de point d'entree rapide au projet |
| `docs/etat_projet.md` | Documenter les decisions prises | Garder une trace claire du projet et des choix |
| `docs/objectif_1_dataset.md` | Justifier le choix du dataset | Repondre a l'objectif 1 de l'evaluation |
| `data/` | Stocker les donnees du projet | Separer les donnees du code applicatif |
| `notebooks/` | Explorer et experimenter | Faire l'analyse IA sans polluer le code de l'API |
| Git/GitHub | Versionner et sauvegarder le projet | Suivre l'historique et synchroniser le travail |

## 3. Structure actuelle du projet

```text
Examen_IA/
  app/
    __init__.py
    main.py
  data/
    Examen_travel_planning_dataset.csv
  docs/
    etat_projet.md
  notebooks/
    01_exploration.ipynb
  .dockerignore
  .gitattributes
  .gitignore
  Dockerfile
  docker-compose.yml
  README.md
  requirements.txt
  requirements-dev.txt
```

### Pourquoi cette structure ?

La structure separe les responsabilites :

- `app/` contient le code applicatif qui pourra etre lance en production ;
- `data/` contient les fichiers de donnees ;
- `notebooks/` contient les experimentations et analyses ;
- `docs/` contient la documentation de conception ;
- les fichiers Docker et Git restent a la racine car ils pilotent le projet.

### Objectif

L'objectif est d'avoir un projet lisible, facile a maintenir et proche d'une
organisation professionnelle. Chaque type de fichier a sa place, ce qui reduit
les confusions lorsque le projet grandit.

## 4. Environnement Python local

Un environnement virtuel Python a ete cree dans `.venv`.

### Pourquoi creer un nouvel environnement ?

Un projet IA depend souvent de bibliotheques lourdes et sensibles aux versions :
`numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`, etc.

Sans environnement dedie, ces bibliotheques seraient installees globalement sur
la machine. Cela peut provoquer des conflits avec d'autres projets ou casser un
ancien projet qui utilisait d'autres versions.

### Objectif

L'environnement `.venv` permet de :

- isoler les dependances du projet ;
- reproduire l'installation plus facilement ;
- garder le systeme Python principal propre ;
- savoir exactement quelles bibliotheques sont necessaires ;
- faciliter le passage entre developpement local, notebook et Docker.

### Commandes utilisees

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

## 5. Fichiers de dependances

Deux fichiers de dependances ont ete crees :

- `requirements.txt` ;
- `requirements-dev.txt`.

### Pourquoi deux fichiers ?

Toutes les dependances n'ont pas le meme role.

`requirements.txt` contient ce qui est necessaire pour faire tourner
l'application. Ce fichier est utilise dans Docker.

`requirements-dev.txt` contient les outils utiles pendant le developpement :
notebooks, graphiques, tests et linting.

### Objectif

Cette separation permet de :

- garder l'image Docker plus simple ;
- eviter d'installer Jupyter dans un conteneur de production si ce n'est pas
  necessaire ;
- clarifier les outils utiles uniquement aux developpeurs ;
- faciliter la maintenance des versions.

### Dependances runtime

`requirements.txt` contient notamment :

- `fastapi` pour creer l'API ;
- `uvicorn` pour lancer le serveur web ;
- `pydantic` pour valider les donnees d'entree et de sortie ;
- `numpy`, `pandas`, `scipy`, `scikit-learn` pour le traitement IA ;
- `python-dotenv` pour charger de la configuration depuis un fichier `.env`.

### Dependances de developpement

`requirements-dev.txt` ajoute notamment :

- `matplotlib` et `seaborn` pour les visualisations ;
- `jupyterlab` et `ipykernel` pour les notebooks ;
- `pytest` et `httpx` pour les tests ;
- `ruff` pour analyser la qualite du code.

### Pourquoi stabiliser les versions ?

Les versions des bibliotheques sont stabilisees pour garantir la reproductibilite
du projet sur un autre poste, dans Docker ou dans un environnement CI/CD. Cela
evite les incompatibilites entre `numpy`, `pandas`, `scikit-learn`, `scipy` et
les outils de notebook.

Important : apres modification des dependances, il faut relancer une
installation propre de l'environnement.

## 6. API FastAPI

Le fichier `app/main.py` contient une API FastAPI de demarrage.

### Pourquoi creer une API ?

Dans un projet IA, le modele ne doit pas rester uniquement dans un notebook. Pour
qu'il soit utilisable par une application, un site, un autre service ou un
utilisateur, il faut l'exposer via une interface.

Une API permet d'envoyer des donnees en entree et de recevoir une prediction en
sortie.

### Objectif

L'API actuelle sert a valider l'architecture :

- demarrer un serveur HTTP ;
- exposer un endpoint de verification ;
- exposer un endpoint de prediction ;
- verifier que l'API fonctionne en local ;
- verifier que l'API fonctionne dans Docker.

### Endpoints disponibles

- `GET /health` : verifie que l'API repond ;
- `POST /predict` : retourne une prediction de demonstration.

### Pourquoi utiliser un modele demo Iris ?

Le modele actuel est base sur le dataset Iris de `scikit-learn`.

Ce n'est pas le modele final du projet. Il sert a tester toute la chaine
technique avant d'integrer le vrai modele :

- FastAPI ;
- validation Pydantic ;
- prediction ;
- Docker ;
- appel HTTP ;
- documentation interactive.

### Objectif du modele demo

Le but est de valider l'infrastructure avant de complexifier le modele. Une fois
le travail sur le dataset travel planning avance, le endpoint `/predict` sera
adapte au vrai modele du projet.

### Commande locale

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8001
```

Documentation interactive :

```text
http://localhost:8001/docs
```

## 7. Port `8001`

Le port local utilise est `8001`.

### Pourquoi ne pas garder `8000` ?

Le port `8000` etait deja utilise par un autre projet. Garder le meme port
aurait provoque un conflit et empeche le lancement de l'API.

### Objectif

Le port `8001` permet de faire tourner ce projet sans bloquer l'autre projet.

En Docker, le mapping est :

```yaml
ports:
  - "8001:8000"
```

Cela signifie :

- `8001` est le port accessible depuis l'ordinateur ;
- `8000` est le port utilise a l'interieur du conteneur.

## 8. Docker

La conteneurisation a ete ajoutee avec :

- `Dockerfile` ;
- `docker-compose.yml` ;
- `.dockerignore`.

### Pourquoi adapter la conteneurisation ?

Un projet IA peut fonctionner sur une machine mais echouer sur une autre a cause
des versions Python, des dependances ou de la configuration systeme.

Docker permet d'emballer l'application et ses dependances dans un environnement
controle.

### Objectif

Docker sert a :

- rendre le projet reproductible ;
- simplifier le lancement de l'API ;
- preparer un futur deploiement ;
- eviter les problemes de configuration locale ;
- tester l'application dans un environnement proche de la production.

### Role du `Dockerfile`

Le `Dockerfile` decrit comment construire l'image :

- partir de `python:3.12-slim` ;
- definir le dossier `/app` ;
- installer les dependances ;
- copier le code de l'application ;
- exposer le port `8000` ;
- lancer Uvicorn.

### Role de `docker-compose.yml`

`docker-compose.yml` simplifie le lancement du conteneur.

Au lieu de taper une longue commande `docker run`, on utilise :

```powershell
docker compose up -d --build
```

### Role de `.dockerignore`

`.dockerignore` evite d'envoyer dans l'image Docker des fichiers inutiles comme :

- `.venv` ;
- caches Python ;
- fichiers Git ;
- fichiers locaux.

Cela rend les builds plus propres et plus rapides.

### Commandes Docker utiles

```powershell
docker compose up -d --build
docker compose ps
docker compose logs api
docker compose stop
```

### Validation effectuee

L'API Docker a deja ete testee avec succes :

- `GET http://localhost:8001/health` repondait `{"status": "ok"}` ;
- `POST http://localhost:8001/predict` retournait une prediction ;
- l'image Docker contenait bien `numpy` et `pandas`.

### Bonne pratique

Docker permet de tester l'application dans un environnement isole. Pour eviter
les conflits entre notebook, API et conteneur, il est preferable de ne lancer
que les services necessaires pendant une phase de travail donnee.

## 9. Git et GitHub

Un depot Git a ete initialise sur la branche `main`.

### Pourquoi utiliser Git ?

Git permet de suivre l'historique du projet. Chaque commit est un point de
sauvegarde qui permet de comprendre ce qui a change et de revenir en arriere si
necessaire.

### Objectif

Git sert a :

- sauvegarder les etapes importantes ;
- suivre les modifications ;
- eviter de perdre du travail ;
- documenter l'evolution du projet ;
- preparer le travail collaboratif.

### Pourquoi utiliser GitHub ?

GitHub permet de sauvegarder le depot en ligne et de le consulter depuis une
autre machine. C'est aussi une preuve de versionnement pour un projet d'examen
ou de portfolio.

### Objectif

GitHub sert a :

- synchroniser le depot local ;
- conserver une copie distante ;
- partager le projet si necessaire ;
- suivre l'historique depuis une interface web.

### Fichiers de configuration Git

`.gitignore` a ete ajoute pour eviter de versionner :

- `.venv` ;
- `.env` ;
- caches Python ;
- checkpoints Jupyter ;
- fichiers temporaires.

`.gitattributes` a ete ajoute pour stabiliser les fins de ligne entre Windows et
Linux. Cela evite les avertissements et les modifications inutiles dans Git.

### Etat GitHub confirme

Le depot local a ete relie au depot GitHub `projet_ia` via `origin`.

Un etat propre a deja ete confirme :

```text
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

Depuis, de nouveaux changements ont ete ajoutes localement et devront etre
commites puis pousses vers GitHub.

Commandes utiles :

```powershell
git status
git add .
git commit -m "Add notebook and project documentation"
git push
```

## 10. Dataset CSV

Le dataset ajoute est :

```text
data/Examen_travel_planning_dataset.csv
```

### Pourquoi creer un dossier `data/` ?

Les donnees ne doivent pas etre melangees avec le code. Les separer rend le
projet plus lisible et facilite la preparation des donnees.

### Objectif

Le dossier `data/` sert a stocker les donnees utilisees par le projet IA.

La structure recommandee pour la suite est :

```text
data/
  raw/
    donnees_originales.csv
  processed/
    donnees_preparees.csv
```

Actuellement, le fichier est directement dans `data/`. Il pourra etre deplace
plus tard dans `data/raw/` si on veut une organisation plus stricte.

### Informations observees

Le dataset contient :

- 1500 lignes ;
- 15 colonnes ;
- des informations de planification de voyage.

Colonnes observees :

- `trip_id` ;
- `client_type` ;
- `budget_total` ;
- `destination` ;
- `saison` ;
- `duree_jours` ;
- `type_hebergement` ;
- `prix_vol` ;
- `meteo_prevue` ;
- `activite_principale` ;
- `satisfaction_client` ;
- `imprevus` ;
- `reorganisation_necessaire` ;
- `respect_budget` ;
- `retour_client`.

### Variable cible principale recommandee

Avec le contexte metier de l'agence de voyages haut de gamme, la cible
principale recommandee est :

```text
satisfaction_client
```

### Pourquoi cette cible ?

`satisfaction_client` correspond directement a l'objectif central du projet :
personnaliser les sejours et maximiser la qualite de l'experience client.

### Objectif

Ce choix permet de construire un modele capable d'estimer la satisfaction
attendue pour plusieurs options de sejour. Le conseiller peut ensuite recommander
l'option qui maximise la satisfaction, tout en tenant compte du budget, de la
saison, de la duree et des risques.

Les colonnes `respect_budget`, `reorganisation_necessaire` et `imprevus`
restent utiles comme cibles secondaires ou indicateurs de risque.

### Attention GitHub

Le dataset est synthetique et anonymise dans le cadre de la certification. Il
peut donc etre versionne pour ce projet. En revanche, si le projet etait enrichi
avec des donnees reelles, il faudrait verifier les contraintes RGPD et
confidentialite avant tout envoi sur GitHub.

## 11. Notebook Jupyter

Un notebook de demarrage a ete cree :

```text
notebooks/01_exploration.ipynb
```

### Pourquoi creer un notebook ?

Un notebook est utile pour l'exploration IA car il permet d'executer le travail
cellule par cellule :

- chargement des donnees ;
- observation des colonnes ;
- statistiques descriptives ;
- visualisations ;
- premiers tests de modeles ;
- interpretation des resultats.

### Objectif

Le notebook sert a comprendre le dataset avant d'ecrire du code applicatif plus
stable. Il permet de tester vite, puis de transformer les meilleures idees en
scripts ou en API.

### Contenu du notebook

Le notebook contient :

- configuration des imports ;
- chargement du CSV ;
- vue d'ensemble des dimensions, types et valeurs manquantes ;
- analyse descriptive ;
- choix de la cible principale recommandee ;
- premier modele baseline avec `LogisticRegression` ;
- preprocessing avec imputation, standardisation et encodage one-hot ;
- rapport de classification ;
- matrice de confusion ;
- visualisations legeres.

### Pourquoi alleger le notebook ?

Le notebook final doit rester lisible, maintenable et reproductible. Il a donc
ete adapte pour charger les bibliotheques de facon structuree, limiter les
operations inutiles et separer les experimentations lourdes dans des notebooks
de brouillon.

### Commande pour lancer Jupyter

```powershell
.\.venv\Scripts\Activate.ps1
jupyter lab
```

Dans VS Code, il faut selectionner le kernel `.venv`.

## 12. Documentation du projet

Le fichier de documentation principal est :

```text
docs/etat_projet.md
```

### Pourquoi documenter maintenant ?

Le projet avance par etapes : environnement, Docker, Git, dataset, notebook,
modelisation, industrialisation et monitoring. Sans documentation, il devient
difficile de se souvenir des decisions prises et de leurs raisons.

### Objectif

Cette documentation sert a :

- expliquer les choix techniques ;
- justifier les fichiers crees ;
- garder une trace des problemes rencontres ;
- faciliter la reprise du projet ;
- preparer une eventuelle presentation ou soutenance.

## 13. Sobriete et maitrise des ressources

Le projet adopte une approche volontairement sobre : le modele industrialise est
un pipeline tabulaire scikit-learn, plus simple a expliquer, tester et deployer
qu'un modele lourd.

### Objectif des choix effectues

Les choix techniques visent a :

- stabiliser les versions des bibliotheques ;
- garder un notebook final lisible ;
- isoler les experimentations lourdes ;
- limiter les traitements non indispensables ;
- utiliser `n_jobs=1` pour obtenir des executions plus reproductibles ;
- mesurer l'empreinte carbone avec CodeCarbon ;
- conserver le NLP avance comme experience separee et non comme dependance du
  modele principal pre-voyage.

### Bonnes pratiques recommandees

- lancer uniquement les services utiles pendant une phase de travail ;
- utiliser Docker pour verifier la portabilite ;
- conserver les artefacts lourds hors Git ;
- documenter les choix de simplification ;
- privilegier des modeles interpretable et maintenables avant de tester des
  architectures plus couteuses.

## 14. Etat actuel du projet

### Deja fait

- environnement virtuel cree ;
- dependances IA et developpement ajoutees ;
- API FastAPI de demarrage creee ;
- Dockerfile et Compose ajoutes ;
- port local passe de `8000` a `8001` ;
- depot Git initialise ;
- depot GitHub configure ;
- premier commit deja pousse ;
- dataset CSV ajoute localement ;
- notebook Jupyter cree ;
- documentation descriptive ajoutee.

### A faire avant de continuer

- relancer l'installation des dependances stabilisees si elles changent ;
- tester le notebook cellule par cellule ;
- verifier si le dataset peut etre pousse sur GitHub ;
- faire un commit des nouveaux changements si tout est valide.

## 15. Prochaines etapes recommandees

1. Executer le notebook cellule par cellule.
2. Confirmer la vraie variable cible du projet.
3. Nettoyer et preparer le dataset.
4. Entrainer plusieurs modeles baseline.
5. Choisir une metrique d'evaluation.
6. Sauvegarder le meilleur modele.
7. Adapter l'API `/predict` au modele final.
8. Tester l'API avec Docker.
9. Commit et push des changements valides sur GitHub.

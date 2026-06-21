# Versioning des donnees

## Objectif

Le versioning des donnees permet de garantir la reproductibilite du projet IA : un score de modele doit pouvoir etre rattache a une version precise du dataset, avec ses traitements et ses controles qualite.

Dans ce projet, le dataset est leger et synthetique. La strategie retenue est donc volontairement simple :

- versioning des CSV dans Git ;
- generation reproductible avec `scripts/version_data.py` ;
- tracabilite des transformations dans `data/versions/manifest.json` ;
- empreinte SHA-256 pour verifier qu'un fichier n'a pas ete modifie.

Si le projet evolue vers des donnees volumineuses ou multi-sources, une solution dediee comme DVC ou LakeFS deviendra plus pertinente.

## Versions retenues

| Version | Role | Fichier | Usage |
| --- | --- | --- | --- |
| `v1.0` | Dataset brut fourni | `data/versions/v1_0_raw/travel_planning_dataset_v1_0.csv` | Reference initiale, non modifiee |
| `v1.1` | Nettoyage colonnes, espaces, formats | `data/versions/v1_1_cleaning/travel_planning_dataset_v1_1.csv` | Controle de structure et harmonisation |
| `v1.2` | Suppression des incoherences critiques | `data/versions/v1_2_incoherences/travel_planning_dataset_v1_2.csv` | Base propre avant feature engineering |
| `v2.0` | Feature engineering | `data/versions/v2_0_feature_engineering/travel_planning_dataset_v2_0.csv` | Dataset enrichi pour analyse et modelisation |
| `v2.1` | Enrichissement eventuel | `data/versions/v2_1_enrichment/README.md` | Reserve aux futures sources externes validees |

## Transformations appliquees

### v1.0 - Donnees brutes

- Copie conforme du fichier fourni.
- Aucune correction.
- Sert de point de retour arriere.

### v1.1 - Nettoyage structurel

- Normalisation des noms de colonnes.
- Suppression des espaces en debut et fin de chaine.
- Passage des valeurs texte en minuscules.
- Conversion des colonnes numeriques attendues.
- Conversion des chaines vides en valeurs manquantes.

### v1.2 - Incoherences critiques

- Suppression des lignes sans `satisfaction_client` valide entre `1` et `5`.
- Suppression des cas `prix_vol > budget_total`.
- Suppression des cas `reorganisation_necessaire = 1` avec `imprevus = aucun`.
- Remplissage de `imprevus` manquant par `aucun`.
- Remplissage de `retour_client` manquant par une chaine vide.

### v2.0 - Feature engineering

- Creation de `budget_par_jour`.
- Creation de `part_vol_budget`.
- Creation de `sejour_long`.
- Creation de `meteo_risque`.
- Creation de `client_business`.
- Creation de `hebergement_luxe`.
- Ajout de variables d'enrichissement interne liees a la destination.
- Creation d'indicateurs post-voyage explicatifs pour l'analyse qualite.

### v2.1 - Enrichissement futur

Cette version n'est pas encore materialisee par un CSV, car aucune source externe supplementaire n'a ete validee. Elle pourra etre creee si le projet integre par exemple :

- une duree de vol ;
- des donnees meteo historiques ;
- des donnees tarifaires ;
- des avis clients supplementaires ;
- de nouvelles donnees metier fournies par l'agence.

## Reproduction

Pour regenerer toutes les versions :

```powershell
python scripts/version_data.py
```

Le script genere :

- les fichiers CSV versionnes ;
- le fichier `data/versions/manifest.json` ;
- les empreintes SHA-256 ;
- le rapport de nettoyage de `v1.2`.

## Gouvernance

Toute nouvelle version doit documenter :

- la source utilisee ;
- les transformations appliquees ;
- le nombre de lignes et colonnes ;
- les suppressions ou corrections effectuees ;
- l'impact attendu sur la modelisation ;
- la validation metier ou technique associee.

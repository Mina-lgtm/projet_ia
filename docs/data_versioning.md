# TravelMind - Versioning des donnees

## Objectif

Le versioning des donnees garantit la reproductibilite du projet : chaque resultat de modele doit pouvoir etre rattache a une version precise du dataset, avec ses traitements, ses controles qualite et son empreinte SHA-256.

La strategie retenue est volontairement simple car le dataset est synthetique et leger :

- versioning des CSV dans Git ;
- generation reproductible par scripts ;
- tracabilite des transformations dans `data/versions/manifest.json` ;
- empreinte SHA-256 pour verifier qu'un fichier n'a pas ete modifie.

Si le projet evolue vers des donnees volumineuses, reelles ou multi-sources, une solution dediee comme DVC ou LakeFS sera plus adaptee.

## Versions retenues

| Version | Role | Fichier | Usage |
| --- | --- | --- | --- |
| `v1.0` | Dataset brut fourni | `data/versions/v1_0_raw/travel_planning_dataset_v1_0.csv` | Reference initiale non modifiee |
| `v1.1` | Nettoyage colonnes, espaces, formats | `data/versions/v1_1_cleaning/travel_planning_dataset_v1_1.csv` | Harmonisation structurelle |
| `v1.2` | Suppression des incoherences critiques | `data/versions/v1_2_incoherences/travel_planning_dataset_v1_2.csv` | Base propre avant enrichissement |
| `v2.0` | Feature engineering | `data/versions/v2_0_feature_engineering/travel_planning_dataset_v2_0.csv` | Ajout de variables derivees |
| `v2.1` | Enrichissement externe optionnel | `data/versions/v2_1_enrichment/travel_planning_dataset_v2_1.csv` | Ajout de sources meteo / air / tarifaires si disponibles |
| `v2.2` | Enrichissement signal metier et augmentation synthetique | `data/versions/v2_2_signal_enrichment/travel_planning_dataset_v2_2.csv` | Version complete enrichie a 3000 lignes |
| `v2.2-light` | Variante allegee | `data/versions/v2_2_signal_enrichment/travel_planning_dataset_v2_2_light.csv` | Colonnes detaillees reduites |
| `v2.2-minimal` | Variante minimale | `data/versions/v2_2_signal_enrichment/travel_planning_dataset_v2_2_minimal.csv` | Colonnes minimales pour tests |
| `v2.2-final` | Dataset final retenu | `data/versions/v2_2_signal_enrichment/dataset_final.csv` | Dataset utilise par le notebook final |

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

- Suppression des doublons sur `trip_id` si presents.
- Suppression des lignes sans `satisfaction_client` valide entre `1` et `5`.
- Suppression des valeurs hors bornes metier configurees.
- Suppression des cas `prix_vol > budget_total`.
- Suppression des cas `reorganisation_necessaire = 1` avec `imprevus` absent ou `aucun`.
- Remplissage de `imprevus` manquant par `aucun`.
- Remplissage de `retour_client` manquant par une chaine vide.

### v2.0 - Feature engineering

- Creation de `budget_par_jour`.
- Creation de `part_vol_budget`.
- Creation de `sejour_long`.
- Creation de `meteo_risque`.
- Creation de `client_business`.
- Creation de `hebergement_luxe`.
- Creation d'indicateurs explicatifs utiles a l'analyse qualite.

### v2.1 - Enrichissement optionnel

Cette version peut integrer, si les fichiers reels sont fournis dans `data/external/` :

- donnees meteo historiques ;
- donnees de qualite de l'air ;
- donnees tarifaires de reference par destination ;
- autres sources validees par le metier et compatibles RGPD.

Les sources attendues sont decrites dans `configs/enrichment_sources.json`.

### v2.2 - Enrichissement signal metier

Cette version ajoute un signal metier structure et augmente le volume a `3000` lignes :

- `1378` lignes source nettoyees ;
- `1622` lignes synthetiques generees par duplication controlee et perturbation limitee ;
- ajout de scores budget, vol, meteo, destination et adequation profil / activite ;
- creation de `score_potentiel_satisfaction` et `niveau_risque_satisfaction`.

### v2.2-final - Dataset final

`dataset_final.csv` est la version retenue dans le notebook final. Elle contient `3000` lignes et `24` colonnes. Elle est derivee de `v2.2-minimal`, avec des noms de colonnes alignes avec la documentation finale.

## Reproduction

Pour regenerer les versions :

```powershell
python scripts/version_data.py
python scripts/enrich_dataset.py
python scripts/build_signal_enrichment_dataset.py
```

Le manifeste `data/versions/manifest.json` trace :

- les chemins des fichiers ;
- les lignes et colonnes ;
- les transformations ;
- les noms de colonnes ;
- les empreintes SHA-256 ;
- les rapports associes.

## Gouvernance

Toute nouvelle version doit documenter :

- la source utilisee ;
- les transformations appliquees ;
- le nombre de lignes et colonnes ;
- les suppressions ou corrections effectuees ;
- l'impact attendu sur la modelisation ;
- la validation metier ou technique associee.

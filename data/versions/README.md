# Versioning des donnees

Ce dossier contient les versions successives du dataset utilisees dans le projet IA.

| Version | Role | Fichier |
| --- | --- | --- |
| v1.0 | Dataset brut fourni | `v1_0_raw/travel_planning_dataset_v1_0.csv` |
| v1.1 | Nettoyage colonnes, espaces et formats | `v1_1_cleaning/travel_planning_dataset_v1_1.csv` |
| v1.2 | Suppression des incoherences critiques | `v1_2_incoherences/travel_planning_dataset_v1_2.csv` |
| v2.0 | Feature engineering | `v2_0_feature_engineering/travel_planning_dataset_v2_0.csv` |
| v2.1 | Enrichissement eventuel | `v2_1_enrichment/README.md` |

Le fichier `manifest.json` contient les metadonnees, les transformations et les empreintes SHA-256.

Pour regenerer les versions :

```bash
python scripts/version_data.py
```

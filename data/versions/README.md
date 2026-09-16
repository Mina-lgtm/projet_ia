# Versioning des donnees TravelMind

Ce dossier contient les versions successives du dataset utilisees dans le projet.

| Version | Role | Fichier principal |
| --- | --- | --- |
| `v1.0` | Dataset brut fourni | `v1_0_raw/travel_planning_dataset_v1_0.csv` |
| `v1.1` | Nettoyage colonnes, espaces et formats | `v1_1_cleaning/travel_planning_dataset_v1_1.csv` |
| `v1.2` | Suppression des incoherences critiques | `v1_2_incoherences/travel_planning_dataset_v1_2.csv` |
| `v2.0` | Feature engineering | `v2_0_feature_engineering/travel_planning_dataset_v2_0.csv` |
| `v2.1` | Enrichissement externe optionnel | `v2_1_enrichment/travel_planning_dataset_v2_1.csv` |
| `v2.2` | Enrichissement signal metier et augmentation synthetique | `v2_2_signal_enrichment/travel_planning_dataset_v2_2.csv` |
| `v2.2-final` | Dataset final retenu pour la modelisation | `v2_2_signal_enrichment/dataset_final.csv` |

Le fichier `manifest.json` contient les metadonnees, les transformations, les colonnes et les empreintes SHA-256.

Pour regenerer les versions structurelles :

```powershell
python scripts/version_data.py
python scripts/enrich_dataset.py
python scripts/build_signal_enrichment_dataset.py
```

`dataset_final.csv` est le fichier utilise par le notebook final.

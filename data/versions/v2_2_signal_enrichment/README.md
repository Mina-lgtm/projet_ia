# Dataset v2.2 - enrichissement signal metier

Cette version est une experience separee destinee a tester si des variables avant depart plus structurees ameliorent la prediction de la satisfaction.

## Fichiers

| Fichier | Role |
| --- | --- |
| `travel_planning_dataset_v2_2.csv` | Version complete enrichie |
| `travel_planning_dataset_v2_2_light.csv` | Variante allegee |
| `travel_planning_dataset_v2_2_minimal.csv` | Variante minimale |
| `dataset_final.csv` | Dataset final retenu dans le notebook |
| `signal_enrichment_report.json` | Rapport de generation du dataset |

## Construction

La version v2.2 atteint `3000` lignes :

- `1378` lignes issues du dataset nettoye ;
- `1622` lignes synthetiques generees par duplication controlee ;
- perturbation limitee du budget, du prix du vol et de la duree ;
- ajout de scores metier sans utiliser directement la cible comme feature.

## Colonnes principales ajoutees

- `reste_budget_apres_vol`
- `budget_apres_vol_par_jour`
- `score_budget_destination`
- `score_prix_vol_coherent`
- `score_adequation_activite_profil`
- `score_meteo_prevue`
- `score_contexte_destination`
- `score_potentiel_satisfaction`
- `niveau_risque_satisfaction`

## Statut

Cette version reste experimentale et synthetique. Elle sert a tester l'hypothese suivante : avec des variables metier plus informatives et une cible plus coherente sur les lignes synthetiques, le modele peut mieux apprendre. Elle ne remplace pas une collecte de donnees reelles.

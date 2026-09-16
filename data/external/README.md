# Données externes d'enrichissement

Ce dossier est réservé aux données externes ou internes réelles pouvant enrichir TravelMind.

Principe retenu :

- ne pas inventer de données externes ;
- ajouter uniquement des variables connues avant le départ pour le modèle pré-voyage ;
- documenter la source, la date d'extraction et les droits d'usage ;
- valider le RGPD si une donnée client réelle est ajoutée ;
- conserver le dataset brut séparé des fichiers enrichis.

## Fichiers attendus

Les templates se trouvent dans `data/external/templates/`.

| Fichier à créer | Clés de jointure | Exemple de valeur ajoutée |
| --- | --- | --- |
| `hotel_quality.csv` | `destination`, `type_hebergement` | Qualité prévisible de l'hébergement |
| `flight_features.csv` | `destination` | Durée de vol, distance, nombre d'escales |
| `weather_history.csv` | `destination`, `saison` | Contexte météo historique |
| `destination_reviews.csv` | `destination` | Attractivité et avis destination |
| `customer_history.csv` | `client_id` | Historique client, uniquement si données réelles et validation RGPD |

## Commande

```powershell
python scripts/enrich_dataset.py
```

Le script génère :

- `data/versions/v2_1_enrichment/travel_planning_dataset_v2_1.csv`
- `data/versions/v2_1_enrichment/enrichment_report.json`


# Enrichissement météo et tarifaire

## Objectif

L'enrichissement vise à ajouter des variables disponibles avant le voyage afin de mieux contextualiser la satisfaction client.

## Météo réelle intégrée

Une source météo réelle a été ajoutée via Open-Meteo.

Fichiers créés :

- `scripts/build_weather_history.py`
- `data/external/weather_history.csv`
- `data/external/weather_history_metadata.json`

Variables ajoutées :

- `temperature_moyenne_saison`
- `pluie_moyenne_mm`
- `jours_pluie_moyen`
- `vent_max_moyen_kmh`
- `nb_jours_observes`
- `latitude`
- `longitude`
- `source`
- `periode_reference`

La jointure est réalisée sur `destination` et `saison`.

## Qualité de l'air réelle intégrée

Une source qualité de l'air réelle a été ajoutée via Open-Meteo.

Fichiers créés :

- `scripts/build_air_quality_history.py`
- `data/external/air_quality_history.csv`
- `data/external/air_quality_history_metadata.json`

Variables ajoutées :

- `pm10_moyen`
- `pm2_5_moyen`
- `european_aqi_moyen`
- `uv_index_moyen`
- `heures_observees_air`
- `source_air_quality`
- `periode_reference_air_quality`

La jointure est réalisée sur `destination` et `saison`.

## Dataset enrichi

Fichiers générés :

- `data/versions/v2_1_enrichment/travel_planning_dataset_v2_1.csv`
- `data/versions/v2_1_enrichment/enrichment_report.json`

## Données tarifaires

Les prix réels de vols, d'hôtels ou de coût de vie n'ont pas été inventés.

Ils doivent provenir d'une source autorisée, par exemple :

- API de prix de vols ;
- API ou export partenaire hôtelier ;
- API de coût de vie ;
- export interne validé par le métier.

Le projet contient un modèle de fichier :

- `data/external/templates/tariff_market_context_template.csv`

Fichier attendu si une source tarifaire réelle est disponible :

- `data/external/tariff_market_context.csv`

Colonnes attendues :

- `destination`
- `cout_vie_indice`
- `prix_hotel_moyen_nuit_eur`
- `prix_vol_moyen_reference_eur`
- `source_tarifaire`
- `periode_reference_tarifaire`

## Décision de gouvernance

La météo est intégrée car elle est disponible via une API ouverte, reproductible et sans donnée personnelle.

Les tarifs ne sont pas intégrés sans source réelle vérifiable. Cette décision évite d'introduire de fausses données qui pourraient améliorer artificiellement les résultats du modèle.

# v2.1 - Enrichissement des données

Cette version ajoute des sources disponibles avant le voyage afin d'améliorer le contexte métier du dataset.

## Source réellement intégrée

- `data/external/weather_history.csv`
- Source : Open-Meteo Historical Weather API
- Jointure : `destination` + `saison`
- Couverture : 32 combinaisons, soit 8 destinations x 4 saisons
- Lignes enrichies : 1378 / 1378

Colonnes ajoutées :

- `temperature_moyenne_saison`
- `pluie_moyenne_mm`
- `jours_pluie_moyen`
- `vent_max_moyen_kmh`
- `nb_jours_observes`
- `latitude`
- `longitude`
- `source`
- `periode_reference`

## Source qualité de l'air intégrée

- `data/external/air_quality_history.csv`
- Source : Open-Meteo Air Quality API
- Jointure : `destination` + `saison`
- Couverture : 32 combinaisons, soit 8 destinations x 4 saisons
- Lignes enrichies : 1378 / 1378

Colonnes ajoutées :

- `pm10_moyen`
- `pm2_5_moyen`
- `european_aqi_moyen`
- `uv_index_moyen`
- `heures_observees_air`
- `source_air_quality`
- `periode_reference_air_quality`

## Sources tarifaires

Les données tarifaires réelles de type prix d'hôtel, prix de vol ou coût de vie ne sont pas inventées.
Elles nécessitent une source autorisée, par exemple une API partenaire ou un export métier.

Un modèle de fichier est disponible :

- `data/external/templates/tariff_market_context_template.csv`

Le fichier attendu est :

- `data/external/tariff_market_context.csv`

Tant que ce fichier n'existe pas, l'enrichissement tarifaire est indiqué comme `missing_file` dans `enrichment_report.json`.

## Commandes

Générer la météo réelle :

```powershell
python scripts/build_weather_history.py
```

Générer la qualité de l'air réelle :

```powershell
python scripts/build_air_quality_history.py
```

Générer le dataset enrichi :

```powershell
python scripts/enrich_dataset.py
```

## Gouvernance

Aucune donnée fictive n'est ajoutée dans cette version. Toute nouvelle source doit préciser son origine, sa date d'extraction, ses droits d'usage et son éventuel impact RGPD.

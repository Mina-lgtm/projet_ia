---
noteId: "36785c30757f11f19eaa8faa5f4f3382"
tags: []

---

# README Monitoring TravelMind

## Objectif

Ce document d?crit les contr?les de monitoring mis en place pour le mod?le TravelMind industrialis? dans l'API.

Le mod?le servi est `LogisticRegression` et pr?dit une cible binaire :

- `non_satisfait_1_2_3` ;
- `satisfait_4_5`.

Le monitoring sert ? :

- suivre les pr?dictions r?alis?es par l'API ;
- mesurer le niveau de confiance des pr?dictions ;
- d?tecter si les nouvelles donn?es saisies s'?loignent du jeu d'entra?nement ;
- d?clencher une revue humaine ou pr?parer un r?entra?nement si n?cessaire.

## Fichiers concern?s

| ?l?ment | Chemin | R?le |
| --- | --- | --- |
| Module de monitoring | `app/monitoring.py` | Calcule les indicateurs, la d?rive et les alertes. |
| Logs de pr?diction | `logs/predictions/predictions.jsonl` | Stocke chaque appel ? `/predict` au format JSONL. |
| M?tadonn?es mod?le | `models/model_pre_voyage_metadata.json` | Contient les m?triques et le profil statistique du jeu d'entra?nement. |
| R?gles m?tier | `configs/business_rules.json` | Centralise les bornes API, cat?gories autoris?es, r?gles de feature engineering et seuils de monitoring. |
| Seuils qualit? mod?le | `configs/model_quality_gate.json` | D?finit les seuils minimaux attendus en CI/CD. |
| API | `app/main.py` | Expose les endpoints de pr?diction et monitoring. |

## Endpoints disponibles

| Endpoint | R?le |
| --- | --- |
| `GET /monitoring/summary` | R?sume les pr?dictions journalis?es. |
| `GET /monitoring/drift` | Compare les entr?es API au profil d'entra?nement. |
| `GET /monitoring/alerts` | Synth?tise les alertes et propose une action. |

## Contr?les mis en place

### Configuration centralis?e

Les r?gles m?tier et les seuils de monitoring sont lus depuis `configs/business_rules.json`.

Ce fichier permet de modifier sans toucher au notebook :

- les bornes API : `duree_jours`, `budget_total`, `prix_vol` ;
- les cat?gories ferm?es : `client_type`, `destination`, `saison`, `type_hebergement`, `meteo_prevue`, `activite_principale` ;
- les r?gles de feature engineering : s?jour long, m?t?o risqu?e, h?bergement luxe ;
- les seuils de drift, de confiance et de volume minimum.

### Journalisation des pr?dictions

Chaque appel ? `/predict` est enregistr? dans `logs/predictions/predictions.jsonl`.

Le log contient notamment :

- la date de pr?diction ;
- l'objectif du mod?le ;
- le nom du mod?le ;
- les donn?es saisies ;
- la classe pr?dite ;
- le libell? m?tier de la classe ;
- les probabilit?s par classe ;
- la confiance, c'est-?-dire la probabilit? maximale ;
- l'indicateur `low_confidence` ;
- les m?triques du mod?le.

### Distribution des pr?dictions

Le monitoring calcule la r?partition des classes pr?dites :

- `non_satisfait_1_2_3` ;
- `satisfait_4_5`.

Cela permet de v?rifier si le mod?le reste ?quilibr? dans ses pr?dictions ou s'il se met ? concentrer toutes les pr?dictions dans une seule classe.

### Faible confiance

Le mod?le binaire retourne une probabilit? pour chaque classe. La confiance correspond ? la probabilit? maximale.

Une pr?diction est marqu?e `low_confidence = true` lorsque cette confiance est inf?rieure au seuil configur? dans `configs/business_rules.json`.

| Indicateur | Seuil actuel | Interpr?tation |
| --- | ---: | --- |
| Faible confiance par pr?diction | `< 0.50` | La pr?diction doit ?tre relue avec prudence. |
| Taux faible confiance warning | `>= 40 %` | Beaucoup de pr?dictions sont peu s?res. |
| Taux faible confiance critique | `>= 60 %` | Le mod?le doit faire l'objet d'une revue prioritaire. |

### Volume minimum de monitoring

Le seuil minimal est configur? dans `configs/business_rules.json`. La valeur actuelle est :

```text
20 pr?dictions
```

Avant ce volume, les conclusions sur la d?rive restent fragiles. Le syst?me renvoie donc un `sample_size_warning`.

## D?finition du drift

Dans ce projet, un drift signifie que les donn?es re?ues par l'API ne ressemblent plus aux donn?es utilis?es pour entra?ner le mod?le.

Il s'agit ici d'un **data drift** : on compare les distributions des entr?es API avec le profil du jeu d'entra?nement.

Le projet ne mesure pas encore directement le **performance drift**, car cela n?cessiterait de r?cup?rer plus tard la vraie satisfaction client apr?s le s?jour.

## Drift num?rique

Pour les variables num?riques, le drift est calcul? avec un ?cart de moyenne normalis? :

```text
abs(moyenne_actuelle - moyenne_train) / std_train
```

| Niveau | Seuil | Interpr?tation |
| --- | ---: | --- |
| OK | `< 1.0` | Les valeurs restent proches du profil d'entra?nement. |
| Warning | `>= 1.0` | La moyenne actuelle commence ? s'?loigner du train. |
| Critique | `>= 2.0` | La variable est fortement diff?rente du train. |

## Drift cat?goriel

Pour les variables cat?gorielles, le drift est calcul? avec la distance de variation totale entre deux distributions :

```text
0.5 * somme(abs(proportion_actuelle - proportion_train))
```

| Niveau | Seuil | Interpr?tation |
| --- | ---: | --- |
| OK | `< 0.20` | La distribution reste proche du train. |
| Warning | `>= 0.20` | La r?partition des cat?gories change. |
| Critique | `>= 0.35` | La distribution est fortement diff?rente du train. |

Le monitoring identifie aussi les cat?gories inconnues qui n'?taient pas pr?sentes dans le jeu d'entra?nement.

## D?cisions d?clench?es

| D?cision | Quand ? | Action recommand?e |
| --- | --- | --- |
| `collect_predictions` | Aucun log ou volume insuffisant | Collecter davantage de pr?dictions avant de conclure. |
| `monitor_and_review` | Alerte warning ou faible confiance ?lev?e | Revue humaine des cas concern?s. |
| `review_and_prepare_retraining` | Alerte critique avec volume suffisant | Pr?parer un r?entra?nement apr?s validation m?tier. |
| `no_action` | Pas d'alerte significative | Continuer le suivi p?riodique. |

## Limites du monitoring actuel

- La d?rive mesure les entr?es, pas encore la satisfaction r?elle observ?e apr?s voyage.
- Les d?cisions de r?entra?nement doivent rester valid?es par le m?tier et l'?quipe technique.
- Le mod?le reste un prototype supervis? : il ne doit pas d?clencher automatiquement une d?cision commerciale sans contr?le humain.

## Commandes utiles

```powershell
python train.py
python -m pytest -q
python -m uvicorn app.main:app --reload --port 8001
```

---
noteId: "36785c30757f11f19eaa8faa5f4f3382"
tags: []

---

# README Monitoring TravelMind

## Objectif

Ce document décrit les contrôles de monitoring mis en place pour le modèle pré-voyage TravelMind industrialisé dans l'API.

Le monitoring sert à :

- suivre les prédictions réalisées par l'API ;
- mesurer le niveau de confiance du modèle ;
- détecter si les nouvelles données saisies s'éloignent du jeu d'entraînement ;
- déclencher une revue humaine ou préparer un réentraînement si nécessaire.

## Fichiers concernés

| Élément | Chemin | Rôle |
| --- | --- | --- |
| Module de monitoring | `app/monitoring.py` | Calcule les indicateurs, la dérive et les alertes. |
| Logs de prédiction | `logs/predictions/predictions.jsonl` | Stocke chaque appel à `/predict` au format JSONL. |
| Métadonnées modèle | `models/model_pre_voyage_metadata.json` | Contient le profil statistique du jeu d'entraînement. |
| API | `app/main.py` | Expose les endpoints de monitoring. |

## Endpoints disponibles

| Endpoint | Rôle |
| --- | --- |
| `GET /monitoring/summary` | Résume les prédictions journalisées. |
| `GET /monitoring/drift` | Compare les entrées API au profil d'entraînement. |
| `GET /monitoring/alerts` | Synthétise les alertes et propose une action. |

## Contrôles mis en place

### Journalisation des prédictions

Chaque appel à `/predict` est enregistré dans `logs/predictions/predictions.jsonl`.

Le log contient notamment :

- la date de prédiction ;
- l'objectif du modèle ;
- le nom du modèle ;
- les données saisies ;
- la classe prédite ;
- les probabilités par classe ;
- le niveau de confiance ;
- les métriques du modèle.

### Distribution des prédictions

Le monitoring calcule la répartition des classes prédites :

- `insatisfait_1_2` ;
- `neutre_3` ;
- `satisfait_4_5`.

Cela permet de vérifier si le modèle prédit toujours les classes de manière cohérente ou s'il se met à prédire presque toujours la même classe.

### Niveau de confiance

Le niveau de confiance correspond à la probabilité maximale retournée par le modèle.

Exemple :

```json
[
  {"classe": 0, "probabilite": 0.38},
  {"classe": 1, "probabilite": 0.26},
  {"classe": 2, "probabilite": 0.36}
]
```

Ici, la confiance est `0.38`.

Une prédiction est considérée comme peu fiable si :

```text
confidence < 0.50
```

### Alertes de faible confiance

| Indicateur | Seuil | Interprétation |
| --- | ---: | --- |
| Faible confiance par prédiction | `< 0.50` | La prédiction doit être relue avec prudence. |
| Taux de faible confiance warning | `>= 40 %` | Beaucoup de prédictions sont incertaines. |
| Taux de faible confiance critique | `>= 60 %` | Le modèle doit faire l'objet d'une revue prioritaire. |

### Volume minimum de monitoring

Le projet utilise un seuil minimal de :

```text
20 prédictions
```

Avant ce volume, les conclusions sur la dérive restent fragiles. Le système renvoie donc un `sample_size_warning`.

## Définition du drift

Dans ce projet, un drift signifie que les données reçues par l'API ne ressemblent plus aux données utilisées pour entraîner le modèle.

Il s'agit ici d'un **data drift** : on compare les distributions des entrées API avec le profil du jeu d'entraînement.

Le projet ne mesure pas encore directement le **performance drift**, car cela nécessiterait de récupérer plus tard la vraie satisfaction client après le séjour.

## Drift numérique

Pour les variables numériques, le drift est calculé avec un écart de moyenne normalisé :

```text
abs(moyenne_actuelle - moyenne_train) / std_train
```

| Niveau | Seuil | Interprétation |
| --- | ---: | --- |
| OK | `< 1.0` | Les valeurs restent proches du profil d'entraînement. |
| Warning | `>= 1.0` | La moyenne actuelle commence à s'éloigner du train. |
| Critique | `>= 2.0` | La variable est fortement différente du train. |

Exemple : si les budgets saisis dans l'API deviennent beaucoup plus élevés que ceux observés à l'entraînement, `budget_total` peut passer en drift.

## Drift catégoriel

Pour les variables catégorielles, le drift est calculé avec la distance de variation totale entre deux distributions :

- distribution observée pendant l'entraînement ;
- distribution observée dans les appels API.

| Niveau | Seuil | Interprétation |
| --- | ---: | --- |
| OK | `< 0.20` | La distribution reste proche du train. |
| Warning | `>= 0.20` | La répartition des catégories change. |
| Critique | `>= 0.35` | La distribution est fortement différente du train. |

Le monitoring identifie aussi les catégories inconnues qui n'étaient pas présentes dans le jeu d'entraînement.

Exemple : si une nouvelle destination est saisie dans l'API alors qu'elle n'existe pas dans le dataset d'origine, elle apparaîtra comme catégorie inconnue.

## Décisions déclenchées

| Situation | Décision API | Action recommandée |
| --- | --- | --- |
| Aucune donnée | `collect_predictions` | Collecter des appels `/predict`. |
| Volume faible | `monitor_and_review` | Attendre plus de prédictions avant de conclure. |
| Faible confiance warning | `monitor_and_review` | Renforcer la revue humaine. |
| Drift warning | `monitor_and_review` | Surveiller les variables concernées. |
| Drift critique avec volume suffisant | `review_and_prepare_retraining` | Préparer un réentraînement après validation métier et technique. |
| Aucun signal significatif | `no_action` | Continuer le suivi périodique. |

## Limites du monitoring actuel

- Les logs sont stockés localement en fichier JSONL.
- Le monitoring ne mesure pas encore la satisfaction réelle après séjour.
- Le drift est indicatif si le volume de prédictions est faible.
- Le réentraînement n'est pas automatique.
- Toute décision de réentraînement doit être validée par les parties prenantes métier et techniques.

## Commandes utiles

Lancer l'API :

```powershell
uvicorn app.main:app --reload --port 8001
```

Consulter les endpoints :

```text
http://localhost:8001/monitoring/summary
http://localhost:8001/monitoring/drift
http://localhost:8001/monitoring/alerts
```

Lire les derniers logs :

```powershell
Get-Content logs/predictions/predictions.jsonl -Tail 5
```

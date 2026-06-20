---
noteId: "d1dcff906ce811f19b2a0fa0ad503336"
tags: []

---

# Stratégie de monitoring et de réentraînement

## Objectif

Le modèle industrialisé est le modèle pré-voyage. Il sert à produire un score indicatif de satisfaction probable avant le départ. Le réentraînement ne doit pas être automatique : il doit être déclenché uniquement après analyse des alertes, validation métier et disponibilité de nouvelles données annotées.

## Sources de monitoring

| Source | Chemin / endpoint | Rôle |
| --- | --- | --- |
| Logs de prédiction | `logs/predictions/predictions.jsonl` | Tracer les entrées, prédictions, probabilités et faibles confiances |
| Résumé monitoring | `/monitoring/summary` | Suivre volume, distribution des prédictions et confiance moyenne |
| Dérive données | `/monitoring/drift` | Comparer les entrées API au profil d'entraînement |
| Alertes consolidées | `/monitoring/alerts` | Transformer les métriques en décision opérationnelle |

## Seuils retenus

| Indicateur | Warning | Critical | Action |
| --- | ---: | ---: | --- |
| Volume minimal | `< 20` prédictions | Non applicable | Ne pas conclure, collecter davantage de logs |
| Faible confiance | `>= 40 %` | `>= 60 %` | Revue humaine des prédictions |
| Dérive numérique | écart moyen normalisé `>= 1.0` | `>= 2.0` | Analyse des variables concernées |
| Dérive catégorielle | distance de distribution `>= 0.20` | `>= 0.35` | Analyse des segments surreprésentés |

## Décisions possibles

| Décision API | Signification | Action recommandée |
| --- | --- | --- |
| `collect_predictions` | Aucun log disponible | Générer des appels `/predict` avant analyse |
| `monitor_and_review` | Alerte ou volume insuffisant | Continuer la collecte et faire une revue humaine |
| `review_and_prepare_retraining` | Alerte critique avec volume suffisant | Préparer un réentraînement après validation métier |
| `no_action` | Pas d'alerte significative | Continuer le suivi périodique |

## Conditions de réentraînement

Un réentraînement peut être envisagé lorsque les conditions suivantes sont réunies :

- au moins `20` prédictions sont journalisées ;
- une dérive critique ou un taux critique de faible confiance est observé ;
- les cas concernés sont validés par le métier ;
- de nouvelles données annotées avec `satisfaction_client` sont disponibles ;
- les contraintes RGPD, éthiques et qualité sont vérifiées.

## Processus recommandé

1. Consulter `/monitoring/alerts`.
2. Si la décision est `review_and_prepare_retraining`, analyser les variables en alerte.
3. Vérifier que les nouvelles données sont fiables, cohérentes et annotées.
4. Relancer `python train.py` sur le dataset mis à jour.
5. Comparer les métriques avec le modèle précédent.
6. Valider le modèle avec le métier avant remplacement.
7. Redémarrer l'API pour charger le nouvel artefact.

## Limites

La dérive est indicative : elle compare les distributions des entrées API au profil d'entraînement, mais elle ne mesure pas directement la performance réelle. La performance réelle nécessite les retours clients après séjour et donc une cible `satisfaction_client` observée.

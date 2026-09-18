---
noteId: "d1dcff906ce811f19b2a0fa0ad503336"
tags: []

---

# Strat?gie de monitoring et de r?entra?nement

## Objectif

Le mod?le industrialis? est `LogisticRegression`. Il pr?dit avant le d?part si un s?jour a une probabilit? d'?tre satisfaisant (`satisfait_4_5`) ou non satisfaisant/interm?diaire (`non_satisfait_1_2_3`).

Le r?entra?nement ne doit pas ?tre automatique : il doit ?tre d?clench? uniquement apr?s analyse des alertes, validation m?tier et disponibilit? de nouvelles donn?es annot?es.

## Sources de monitoring

| Source | Chemin / endpoint | R?le |
| --- | --- | --- |
| Logs de pr?diction | `logs/predictions/predictions.jsonl` | Tracer les entr?es, classes pr?dites, probabilit?s et confiance |
| R?sum? monitoring | `/monitoring/summary` | Suivre volume, distribution des pr?dictions et confiance moyenne |
| D?rive donn?es | `/monitoring/drift` | Comparer les entr?es API au profil d'entra?nement |
| Alertes consolid?es | `/monitoring/alerts` | Transformer les m?triques en d?cision op?rationnelle |

## Seuils retenus

| Indicateur | Warning | Critical | Action |
| --- | ---: | ---: | --- |
| Volume minimal | `< 20` pr?dictions | Non applicable | Ne pas conclure, collecter davantage de logs |
| Faible confiance | `>= 40 %` | `>= 60 %` | Revue humaine des pr?dictions peu s?res |
| D?rive num?rique | ?cart moyen normalis? `>= 1.0` | `>= 2.0` | Analyse des variables concern?es |
| D?rive cat?gorielle | distance de distribution `>= 0.20` | `>= 0.35` | Analyse des segments surrepr?sent?s |
| Quality gate mod?le | seuils dans `configs/model_quality_gate.json` | CI en erreur | Corriger le pipeline ou justifier la d?gradation |

## D?cisions possibles

| D?cision API | Signification | Action recommand?e |
| --- | --- | --- |
| `collect_predictions` | Aucun log disponible ou volume insuffisant | G?n?rer des appels `/predict` avant analyse |
| `monitor_and_review` | Alerte warning ou confiance faible ?lev?e | Continuer la collecte et faire une revue humaine |
| `review_and_prepare_retraining` | Alerte critique avec volume suffisant | Pr?parer un r?entra?nement apr?s validation m?tier |
| `no_action` | Pas d'alerte significative | Continuer le suivi p?riodique |

## Conditions de r?entra?nement

Un r?entra?nement peut ?tre envisag? lorsque les conditions suivantes sont r?unies :

- au moins `20` pr?dictions sont journalis?es ;
- une d?rive critique ou un taux critique de faible confiance est observ? ;
- les cas concern?s sont valid?s par le m?tier ;
- de nouvelles donn?es annot?es avec `satisfaction_client` sont disponibles ;
- les contraintes RGPD, ?thiques et qualit? sont v?rifi?es.

## Processus recommand?

1. Consulter `/monitoring/alerts`.
2. Si la d?cision est `review_and_prepare_retraining`, analyser les variables en alerte.
3. V?rifier que les nouvelles donn?es sont fiables, coh?rentes et annot?es.
4. Relancer `python train.py` sur le dataset mis ? jour.
5. Comparer les m?triques avec le mod?le pr?c?dent : `accuracy`, `balanced_accuracy`, `macro_f1`, `roc_auc`, `precision_satisfait`, `recall_satisfait`.
6. V?rifier la quality gate `configs/model_quality_gate.json`.
7. Valider le mod?le avec le m?tier avant remplacement.
8. Red?marrer l'API pour charger le nouvel artefact.

## ?valuation continue et CI/CD

Le projet int?gre un contr?le qualit? automatique et conditionnel dans GitHub Actions :

1. les fichiers modifi?s sont d?tect?s ;
2. les tests API, mod?le et monitoring sont ex?cut?s si le code ou la configuration change ;
3. le mod?le est r?entra?n? en CI si les donn?es, le pipeline ou les r?gles m?tier changent ;
4. les m?triques export?es dans les m?tadonn?es sont compar?es aux seuils de `configs/model_quality_gate.json` ;
5. la CI ?choue si les m?triques minimales ou le volume train/test ne sont pas respect?s.

Ce contr?le limite le risque de d?gradation silencieuse du mod?le lors d'une modification du nettoyage, du feature engineering ou des hyperparam?tres.

## P?riodicit? de revue

| Fr?quence | Contr?le | Acteur responsable | Sortie attendue |
| --- | --- | --- | --- |
| ? chaque push / pull request | Contr?les CI/CD adapt?s aux fichiers modifi?s | ?quipe data / technique | Validation, blocage ou saut des ?tapes lourdes |
| Hebdomadaire en phase pilote | Lecture de `/monitoring/summary` et `/monitoring/alerts` | Data scientist + m?tier | Liste des cas peu confiants ? revoir |
| Mensuelle | Revue des seuils, d?rives, distribution des pr?dictions | Commanditaire + data scientist | Maintien ou ajustement des indicateurs |
| Trimestrielle ou apr?s alerte critique | Analyse des nouvelles donn?es annot?es | Data scientist + m?tier + DPO si besoin | D?cision de r?entra?nement ou conservation du mod?le |

## Limites

La d?rive est indicative : elle compare les distributions des entr?es API au profil d'entra?nement, mais elle ne mesure pas directement la performance r?elle. La performance r?elle n?cessite les retours clients apr?s s?jour et donc une cible `satisfaction_client` observ?e.

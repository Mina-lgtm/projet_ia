# Plan de correction suite aux retours jury

## Orientation retenue

Le projet est recentr? sur une pr?diction pr?-voyage sous forme de score de satisfaction `1 ? 5`, plut?t qu'une classification en trois classes.

Ce changement rend la finalit? plus lisible :

- sortie attendue : score de satisfaction estim? avant d?part ;
- mod?les compar?s : baseline moyenne, r?gression lin?aire, Ridge et Random Forest ;
- m?triques principales : `MAE`, `RMSE`, `R2` ;
- usage : signal indicatif, non d?cision automatique.

## R?sultats actuels apr?s nettoyage strict

| Indicateur | Valeur | Lecture |
| --- | ---: | --- |
| `MAE` | `1.0636` | Erreur moyenne d'environ 1 point sur l'?chelle 1 ? 5. |
| `RMSE` | `1.2522` | Les erreurs importantes restent pr?sentes. |
| `R2` | `-0.0001` | Le mod?le explique quasiment aucune variance de satisfaction. |
| `baseline_mae` | `1.0636` | La baseline moyenne est le meilleur r?sultat statistique actuel. |
| `mae_gain_vs_baseline` | `0.0000` | Aucun gain par rapport ? une pr?diction na?ve. |

Conclusion : le passage en r?gression clarifie la lecture, mais confirme que les variables pr?-voyage actuelles ne suffisent pas pour produire une aide ? la d?cision fiable.

## Corrections attendues par comp?tence

### C3 - Pr?paration des donn?es

- Synth?tiser les traitements au lieu de d?tailler toutes les pistes explor?es.
- Conserver uniquement les contr?les utiles ? la finalit? : cible valide, incoh?rences budg?taires, valeurs manquantes, valeurs n?gatives, variables post-voyage exclues.
- Ajouter une conclusion claire : la pr?paration permet un pipeline reproductible, mais ne cr?e pas de signal m?tier suppl?mentaire.

### C4 - Choix du mod?le

- Pr?senter une convergence simple : classification test?e puis remplac?e par r?gression pour pr?dire directement le score.
- Expliquer que la baseline devient le meilleur r?sultat apr?s nettoyage strict.
- Indiquer que les mod?les plus complexes n'apportent pas de gain m?tier robuste.

### C5 - Entra?nement et ?valuation

- Remplacer les m?triques classification par les m?triques r?gression : `MAE`, `RMSE`, `R2`.
- Supprimer ou mettre en annexe les matrices de confusion, devenues non pertinentes pour la r?gression.
- Ajouter une conclusion chiffr?e : performance ?quivalente ? la baseline, donc mod?le non pr?t pour production d?cisionnelle.

### C7 - Architecture cible

- Repr?senter le flux logique : donn?es -> nettoyage -> entra?nement -> artefacts -> API -> interface -> logs -> monitoring -> r?entra?nement futur.
- Clarifier que l'architecture est coh?rente pour un prototype industrialisable, pas pour une production compl?te.

### C8 - Performance et impacts

- Ajouter une conclusion ferme : la solution ne doit pas ?tre mise en production comme outil d'aide ? la d?cision automatis?e.
- Limiter l'usage actuel ? un prototype de d?monstration, de monitoring et de structuration MLOps.
- Conserver les mesures carbone comme preuve de sobri?t?, mais ne pas les confondre avec la performance m?tier.

## Message final ? d?fendre

TravelMind montre une d?marche IA compl?te et industrialisable. Cependant, les donn?es pr?-voyage disponibles contiennent trop peu de signal pour pr?dire correctement la satisfaction. Le mod?le de r?gression donne une lecture plus directe, mais les r?sultats restent au niveau d'une baseline. La priorit? avant production est donc l'enrichissement des donn?es r?elles pr?-voyage et la validation m?tier.

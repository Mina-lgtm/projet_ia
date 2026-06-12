# Documentation des experiences de modelisation

## 1. Objectif du document

Ce document synthetise les experiences de modelisation realisees dans le projet
IA de planification de voyages.

L'objectif est de garder une trace claire :

- des hypotheses testees ;
- des jeux de variables utilises ;
- des modeles entraines ;
- des metriques d'evaluation ;
- des resultats obtenus ;
- des conclusions metier tirees de chaque experience.

Les resultats presentes correspondent aux notebooks :

- `notebooks/essaie_sans_enrichissement.ipynb` ;
- `notebooks/essaie_avec_enrichissement.ipynb`.

Les scores ont ete recalcules apres l'ajout des dernieres variables
d'enrichissement et de l'experience `SMOTENC`.

## 2. Cible du modele

La cible principale est :

```text
satisfaction_client
```

Elle correspond a une note de satisfaction de 1 a 5.

Le probleme principal est donc formule comme une classification multi-classes :

| Classe | Signification |
| --- | --- |
| 1 | Satisfaction tres faible |
| 2 | Satisfaction faible |
| 3 | Satisfaction moyenne |
| 4 | Satisfaction bonne |
| 5 | Satisfaction tres bonne |

Une experience secondaire transforme aussi cette cible en classification binaire :

| Classe binaire | Definition |
| --- | --- |
| 0 | Satisfaction 1, 2 ou 3 |
| 1 | Satisfaction 4 ou 5 |

## 3. Variables incluses et exclues du modele

D'apres le document `Examen_cas d'usage.pdf`, l'objectif metier principal est
de construire une IA de planification personnalisee utilisable avant le depart.
Le modele principal doit donc utiliser uniquement des informations disponibles
au moment de la recommandation ou de l'organisation du sejour.

Les variables exclues de `X` sont :

| Variable | Raison d'exclusion |
| --- | --- |
| `satisfaction_client` | Cible a predire |
| `trip_id` | Identifiant technique, sans valeur predictive metier |
| `imprevus` | Evenement constate pendant ou apres le sejour |
| `reorganisation_necessaire` | Resultat operationnel connu pendant ou apres le sejour |
| `respect_budget` | Resultat budgetaire connu apres execution du sejour |
| `retour_client` | Avis client final, disponible apres le sejour |

Cette exclusion evite une fuite de donnees : le modele ne doit pas apprendre a
partir d'informations futures. Ces variables restent utiles pour une analyse
retrospective ou pour des modeles secondaires, mais pas comme entrees du modele
principal de prediction de satisfaction avant depart.

## 4. Preparation commune des donnees

Avant la modelisation, les deux notebooks appliquent une preparation commune :

1. chargement du dataset brut ;
2. verification des incoherences metier ;
3. suppression des lignes avec `satisfaction_client` invalide ;
4. suppression des lignes ou `prix_vol > budget_total` ;
5. traitement des valeurs manquantes ;
6. controle post-imputation de `prix_vol <= budget_total` ;
7. traitement des valeurs aberrantes avec la methode IQR ;
8. creation de variables de feature engineering ;
9. separation train/test avec stratification ;
10. transformation des variables dans un pipeline.

Les transformations du pipeline sont :

- variables numeriques : imputation par mediane puis standardisation ;
- variables categorielles : imputation par `inconnu` puis encodage One-Hot.

L'imputation, la normalisation et l'encodage sont integres au pipeline afin que
les parametres soient appris uniquement sur le jeu d'entrainement.

## 5. Dataset sans enrichissement

Le notebook sans enrichissement utilise uniquement :

- les variables du dataset nettoye ;
- les variables creees par feature engineering.

Nombre de variables utilisees :

| Type de variable | Nombre |
| --- | ---: |
| Numeriques | 12 |
| Categorielles | 6 |
| Total | 18 |

Exemples de variables utilisees :

- `budget_total` ;
- `duree_jours` ;
- `prix_vol` ;
- `budget_par_jour` ;
- `part_vol_budget` ;
- `budget_hors_vol` ;
- `sejour_long` ;
- `meteo_risque` ;
- `saison_haute` ;
- `client_business` ;
- `hebergement_luxe` ;
- `client_type` ;
- `destination` ;
- `saison` ;
- `type_hebergement` ;
- `meteo_prevue` ;
- `activite_principale`.

## 6. Dataset avec enrichissement

Le notebook avec enrichissement ajoute des variables supplementaires afin de
tester si un contexte metier plus riche ameliore les performances.

Nombre de variables utilisees :

| Type de variable | Nombre |
| --- | ---: |
| Numeriques | 30 |
| Categorielles | 12 |
| Total | 42 |

Les variables ajoutees couvrent principalement :

- le transport ;
- le confort ;
- le budget local ;
- l'adequation entre destination et activite ;
- la complexite du sejour.

Exemples de variables enrichies :

| Variable | Objectif |
| --- | --- |
| `duree_vol_heures` | Estimer la fatigue liee au transport |
| `nombre_escales_moyen` | Mesurer la complexite du trajet |
| `decalage_horaire_heures_abs` | Representer l'impact potentiel du decalage horaire |
| `note_moyenne_hebergement_destination` | Approximer le niveau attendu de qualite hoteliere |
| `indice_cout_journalier_destination` | Tenir compte du cout local de la destination |
| `pouvoir_achat_destination` | Comparer le budget quotidien au cout local |
| `activite_destination_adaptee` | Verifier si l'activite principale est coherente avec la destination |
| `temps_vol_par_jour` | Mesurer la pression du transport sur la duree du sejour |
| `sejour_court_vol_long` | Identifier les sejours courts avec trajet lourd |
| `transport_complexe` | Identifier les trajets longs ou avec escale |
| `budget_transport_tendu` | Detecter les sejours ou le vol pese fortement dans le budget |
| `score_confort_global` | Combiner hebergement, transport et decalage horaire |

## 7. Modeles testes

### Classification multi-classes

Les modeles testes pour predire directement `satisfaction_client` sont :

| Modele | Role |
| --- | --- |
| `DummyClassifier` | Reference naive, predit la classe majoritaire |
| `LogisticRegression` | Modele lineaire interpretable |
| `RandomForestClassifier` | Modele non lineaire a base d'arbres |
| `ExtraTreesClassifier` | Variante d'arbres plus aleatoire |

### Classification binaire

Pour la cible `satisfaction_elevee`, les modeles testes sont :

| Modele | Role |
| --- | --- |
| `DummyClassifier` | Reference naive |
| `LogisticRegression` | Modele lineaire interpretable |
| `RandomForestClassifier` | Modele non lineaire |

### Regression

Une experience separee teste :

| Modele | Role |
| --- | --- |
| `LinearRegression` | Verifier si la satisfaction peut etre approximee comme une variable continue |

### Augmentation de donnees

Une experience separee teste :

| Methode | Role |
| --- | --- |
| `SMOTENC` | Augmenter les classes minoritaires dans un dataset mixte numerique/categoriel |

`SMOTENC` est applique uniquement sur le jeu d'entrainement.
Le jeu de test reste inchange.

## 8. Metriques utilisees

### Classification multi-classes

| Metrique | Interpretation |
| --- | --- |
| `accuracy` | Proportion totale de predictions correctes |
| `balanced_accuracy` | Accuracy corrigee du desequilibre des classes |
| `macro_f1` | Moyenne des F1-scores par classe |

Le critere principal est `macro_f1`, car toutes les classes de satisfaction
doivent etre prises en compte.

### Classification binaire

| Metrique | Interpretation |
| --- | --- |
| `accuracy` | Proportion totale de predictions correctes |
| `balanced_accuracy` | Equilibre entre les deux classes |
| `precision_classe_1` | Fiabilite des predictions de satisfaction elevee |
| `recall_classe_1` | Capacite a detecter les sejours vraiment satisfaisants |
| `f1_classe_1` | Compromis precision/rappel sur la satisfaction elevee |
| `roc_auc` | Capacite globale a separer les deux classes |

### Regression

| Metrique | Interpretation |
| --- | --- |
| `MAE` | Erreur moyenne en points de satisfaction |
| `RMSE` | Erreur quadratique, penalise davantage les grosses erreurs |
| `R2` | Part de variance expliquee par le modele |

## 9. Experience 1 - Classification multi-classes sans enrichissement

Objectif :

Tester si le dataset nettoye suffit a predire `satisfaction_client`.

Resultats :

| Modele | Accuracy | Balanced accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| `ExtraTrees` | 0.2148 | 0.2378 | 0.2143 |
| `LogisticRegression` | 0.2042 | 0.2135 | 0.2041 |
| `RandomForest` | 0.1972 | 0.2037 | 0.1903 |
| `Dummy_majority` | 0.2887 | 0.2000 | 0.0896 |

Interpretation :

- `Dummy_majority` obtient la meilleure accuracy, mais ce score est trompeur.
- Son `macro_f1` est tres faible car il ignore les classes minoritaires.
- Le meilleur modele reel est `ExtraTrees`, avec `macro_f1 = 0.2143`.
- Le score reste faible, ce qui montre que le dataset initial contient peu de
  signal predictif disponible avant depart pour expliquer la satisfaction.

Conclusion :

Le dataset nettoye seul ne suffit pas pour produire un modele fiable.

## 10. Experience 2 - Classification multi-classes avec enrichissement

Objectif :

Tester si l'ajout de variables metier supplementaires ameliore la prediction.

Resultats :

| Modele | Accuracy | Balanced accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| `RandomForest` | 0.2535 | 0.2477 | 0.2402 |
| `ExtraTrees` | 0.2394 | 0.2555 | 0.2370 |
| `LogisticRegression` | 0.2077 | 0.2155 | 0.2055 |
| `Dummy_majority` | 0.2887 | 0.2000 | 0.0896 |

Interpretation :

- L'enrichissement ameliore les modeles non lineaires.
- `RandomForest` devient le meilleur modele selon `macro_f1`.
- Le gain par rapport au meilleur modele sans enrichissement est :

```text
0.2402 - 0.2143 = +0.0259
```

Conclusion :

L'enrichissement apporte un signal supplementaire, mais le gain reste limite.
Le modele enrichi reste un prototype exploratoire, pas un modele exploitable en
production.

## 11. Experience 3 - Augmentation avec SMOTENC sans enrichissement

Objectif :

Verifier si le desequilibre des classes explique les faibles performances.

Distribution des classes sur le train :

| Classe | Avant SMOTENC | Apres SMOTENC |
| --- | ---: | ---: |
| 1 | 201 | 328 |
| 2 | 328 | 328 |
| 3 | 273 | 328 |
| 4 | 197 | 328 |
| 5 | 133 | 328 |

Resultats :

| Modele | Accuracy | Balanced accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| `RandomForest_SMOTENC` | 0.2218 | 0.2144 | 0.2122 |
| `ExtraTrees_SMOTENC` | 0.2042 | 0.1993 | 0.1981 |
| `LogisticRegression_SMOTENC` | 0.2113 | 0.1916 | 0.1928 |

Interpretation :

- `SMOTENC` equilibre bien les classes dans le jeu d'entrainement.
- Les scores ne progressent pas par rapport a `ExtraTrees` sans augmentation.
- Le meilleur score sans augmentation reste `macro_f1 = 0.2143`.
- Le meilleur score avec `SMOTENC` est `macro_f1 = 0.2122`.

Conclusion :

Sans enrichissement, l'augmentation de donnees n'apporte pas d'amelioration
significative.

## 12. Experience 4 - Augmentation avec SMOTENC avec enrichissement

Objectif :

Tester si l'augmentation aide davantage lorsque les variables enrichies sont
disponibles.

Distribution des classes sur le train :

| Classe | Avant SMOTENC | Apres SMOTENC |
| --- | ---: | ---: |
| 1 | 201 | 328 |
| 2 | 328 | 328 |
| 3 | 273 | 328 |
| 4 | 197 | 328 |
| 5 | 133 | 328 |

Resultats :

| Modele | Accuracy | Balanced accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| `RandomForest_SMOTENC` | 0.2641 | 0.2391 | 0.2340 |
| `ExtraTrees_SMOTENC` | 0.2500 | 0.2271 | 0.2226 |
| `LogisticRegression_SMOTENC` | 0.2324 | 0.2103 | 0.2100 |

Interpretation :

- `SMOTENC` augmente legerement l'accuracy du `RandomForest`.
- En revanche, le `macro_f1` baisse par rapport au `RandomForest` enrichi sans
  augmentation.
- Le meilleur score enrichi sans augmentation est `macro_f1 = 0.2402`.
- Le meilleur score enrichi avec `SMOTENC` est `macro_f1 = 0.2340`.

Conclusion :

L'augmentation n'est pas retenue comme meilleure approche. Elle montre que le
probleme ne vient pas uniquement du desequilibre des classes.

## 13. Experience 5 - Classification binaire sans enrichissement

Objectif :

Verifier si une cible simplifiee est plus facile a predire.

Cible :

```text
satisfaction_elevee = 1 si satisfaction_client >= 4, sinon 0
```

Distribution :

| Classe | Effectif | Proportion |
| --- | ---: | ---: |
| 0 = satisfaction 1 a 3 | 1003 | 0.7083 |
| 1 = satisfaction 4 a 5 | 413 | 0.2917 |

Resultats :

| Modele | Accuracy | Balanced accuracy | Precision classe 1 | Recall classe 1 | F1 classe 1 | ROC AUC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `LogisticRegression` | 0.5000 | 0.5159 | 0.3046 | 0.5542 | 0.3932 | 0.5425 |
| `RandomForest` | 0.5669 | 0.5278 | 0.3214 | 0.4337 | 0.3692 | 0.5413 |
| `Dummy_majority` | 0.7077 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 |

Interpretation :

- `Dummy_majority` a une accuracy elevee car la classe 0 est majoritaire.
- Il ne detecte aucun sejour a satisfaction elevee.
- `LogisticRegression` obtient le meilleur `f1_classe_1`.
- Les scores restent modestes.

Conclusion :

La cible binaire est plus lisible, mais elle ne rend pas le modele suffisamment
performant.

## 14. Experience 6 - Classification binaire avec enrichissement

Objectif :

Verifier si les variables enrichies aident a detecter les sejours a forte
satisfaction.

Distribution :

| Classe | Effectif | Proportion |
| --- | ---: | ---: |
| 0 = satisfaction 1 a 3 | 1003 | 0.7083 |
| 1 = satisfaction 4 a 5 | 413 | 0.2917 |

Resultats :

| Modele | Accuracy | Balanced accuracy | Precision classe 1 | Recall classe 1 | F1 classe 1 | ROC AUC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `LogisticRegression` | 0.5317 | 0.5312 | 0.3188 | 0.5301 | 0.3982 | 0.5549 |
| `RandomForest` | 0.5810 | 0.5484 | 0.3421 | 0.4699 | 0.3959 | 0.5616 |
| `Dummy_majority` | 0.7077 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 |

Interpretation :

- L'enrichissement ameliore legerement les scores binaires.
- `RandomForest` obtient la meilleure `balanced_accuracy` et le meilleur
  `ROC AUC`.
- `LogisticRegression` obtient le meilleur `f1_classe_1`, de tres peu.
- Les performances restent insuffisantes pour une decision automatique fiable.

Conclusion :

L'enrichissement aide legerement, mais la separation entre satisfaction faible
et satisfaction elevee reste difficile.

## 15. Experience 7 - Regression lineaire sans enrichissement

Objectif :

Tester si `satisfaction_client` peut etre approximee comme une variable
numerique continue.

Resultats :

| Modele | MAE | RMSE | R2 |
| --- | ---: | ---: | ---: |
| `LinearRegression` | 1.0533 | 1.2603 | 0.0013 |

Evaluation apres arrondi en classes :

| Modele | Accuracy | Balanced accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| `LinearRegression arrondie` | 0.2465 | 0.2029 | 0.1007 |

Interpretation :

- Le modele se trompe en moyenne d'environ 1 point de satisfaction.
- Le `R2` est proche de 0.
- La regression lineaire explique quasiment aucune variance de la satisfaction.
- Apres arrondi, le modele predit surtout la classe 3.

Conclusion :

La regression lineaire n'est pas adaptee comme modele principal.

## 16. Experience 8 - Regression lineaire avec enrichissement

Objectif :

Verifier si les variables enrichies ameliorent la regression lineaire.

Resultats :

| Modele | MAE | RMSE | R2 |
| --- | ---: | ---: | ---: |
| `LinearRegression` | 1.0569 | 1.2661 | -0.0079 |

Evaluation apres arrondi en classes :

| Modele | Accuracy | Balanced accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| `LinearRegression arrondie` | 0.2500 | 0.2018 | 0.1187 |

Interpretation :

- L'enrichissement n'ameliore pas la regression lineaire.
- Le `R2` devient negatif, ce qui indique que le modele fait moins bien qu'une
  prediction moyenne simple.
- La satisfaction ne se comporte pas comme une variable continue facilement
  explicable par une relation lineaire.

Conclusion :

La regression lineaire doit rester une experience secondaire, non retenue pour
la solution finale.

## 17. Synthese comparative

| Experience | Meilleur modele | Macro F1 / score cle |
| --- | --- | ---: |
| Multi-classes sans enrichissement | `ExtraTrees` | 0.2143 |
| Multi-classes avec enrichissement | `RandomForest` | 0.2402 |
| SMOTENC sans enrichissement | `RandomForest_SMOTENC` | 0.2122 |
| SMOTENC avec enrichissement | `RandomForest_SMOTENC` | 0.2340 |
| Binaire sans enrichissement | `LogisticRegression` | F1 classe 1 = 0.3932 |
| Binaire avec enrichissement | `LogisticRegression` | F1 classe 1 = 0.3982 |
| Regression sans enrichissement | `LinearRegression` | R2 = 0.0013 |
| Regression avec enrichissement | `LinearRegression` | R2 = -0.0079 |

## 18. Conclusion generale

Les experiences montrent que :

- le pipeline technique fonctionne ;
- `imprevus`, `reorganisation_necessaire`, `respect_budget` et `retour_client`
  sont exclus des entrees du modele principal ;
- cette exclusion est coherente avec l'objectif metier de prediction avant
  depart et evite une fuite de donnees ;
- le dataset nettoye seul contient peu de signal predictif ;
- l'enrichissement metier ameliore legerement les performances multi-classes ;
- `SMOTENC` n'apporte pas d'amelioration decisive ;
- la classification binaire est plus lisible, mais reste peu performante ;
- la regression lineaire n'est pas adaptee ;
- le meilleur modele actuel est `RandomForest` avec enrichissement, sans
  augmentation de donnees.

Le meilleur score multi-classes obtenu est :

```text
RandomForest avec enrichissement
macro_f1 = 0.2402
```

Ce score reste trop faible pour une utilisation operationnelle fiable.

Le projet doit donc etre considere comme un prototype exploratoire. Pour aller
plus loin, il faudrait enrichir le dataset avec des donnees plus proches de
l'experience reelle du client.

## 19. Interpretation de la Mutual Information

L'analyse de la Mutual Information confirme les resultats obtenus par les
modeles. Les variables disponibles avant le sejour presentent un pouvoir
explicatif tres limite vis-a-vis de `satisfaction_client`. Les scores de
Mutual Information sont faibles pour l'ensemble des variables, ce qui indique
une dependance reduite entre les caracteristiques initiales du voyage et la
satisfaction finale.

Cette observation est coherente avec les performances modestes des modeles de
classification et de regression. Si les variables d'entree contiennent peu
d'information, un modele plus complexe ne peut pas inventer le signal manquant.

Les resultats suggerent que la satisfaction client depend davantage
d'evenements survenant pendant ou apres le sejour :

- apparition d'imprevus ;
- respect ou non du budget ;
- besoin de reorganisation ;
- qualite reelle de l'experience client ;
- ressenti exprime dans les commentaires.

Ces variables contiennent davantage de signal, mais elles ne sont pas
utilisables dans le modele principal de prediction avant depart, car elles sont
connues trop tard. Les utiliser en entree creerait une fuite de donnees.

La conclusion metier est donc la suivante :

- sans variables post-sejour, le signal disponible est faible ;
- la Mutual Information proche de zero confirme statistiquement ce manque de
  signal ;
- les modeles proches du hasard sont une consequence logique de cette limite ;
- les variables issues du retour client ou du deroulement reel du sejour
  peuvent fortement ameliorer les scores, mais uniquement dans une analyse
  retrospective ;
- le modele principal doit rester base sur les donnees disponibles avant
  depart, meme si les performances sont modestes.

Des modeles plus avances comme `XGBoost`, `CatBoost` ou `LightGBM` peuvent etre
testes pour completer la comparaison. Toutefois, l'amelioration attendue reste
limitee avec les donnees actuelles, car le probleme principal vient du manque
de signal dans les variables pre-voyage, et non uniquement du choix de
l'algorithme.

## 20. Plan d'action propose

Au regard des resultats, la suite du projet doit etre structuree en deux axes
distincts afin de rester coherente avec le besoin metier et avec les limites
observees dans les donnees.

### Axe 1 - Objectif pre-voyage

Le premier axe consiste a conserver l'experience de modelisation pre-voyage
comme modele principal, car il correspond au cas d'usage initial : aider
l'agence a planifier un sejour avant le depart.

Dans cet objectif, les entrees du modele doivent uniquement contenir des
variables disponibles au moment de la recommandation :

- profil client ;
- budget ;
- destination ;
- saison ;
- duree du sejour ;
- hebergement souhaite ;
- prix du vol ;
- meteo prevue ;
- activite principale ;
- variables de feature engineering calculables avant depart.

Les variables `imprevus`, `reorganisation_necessaire`, `respect_budget` et
`retour_client` restent exclues de `X`, car elles sont connues pendant ou apres
le sejour.

L'objectif de cette partie n'est pas de masquer les faibles performances, mais
de les expliquer rigoureusement. Les resultats montrent que, malgre :

- le nettoyage des incoherences ;
- le traitement des valeurs manquantes ;
- le traitement des outliers ;
- le feature engineering ;
- l'enrichissement metier ;
- la comparaison de plusieurs modeles ;
- l'augmentation de donnees avec `SMOTENC` ;
- la classification binaire ;
- la regression lineaire ;

les performances restent modestes. Cette limite est coherente avec l'analyse
de la Mutual Information : les variables pre-voyage contiennent peu de signal
pour predire la satisfaction finale.

Cette conclusion est importante pour le projet. Elle montre que le probleme ne
vient pas uniquement du choix de l'algorithme, mais principalement de la nature
des donnees disponibles avant le depart.

### Axe 2 - Objectif post-voyage

Le second axe consiste a proposer une modelisation post-voyage, avec un objectif
different. Il ne s'agit plus de predire la satisfaction avant le depart, mais
d'expliquer la satisfaction apres le sejour et d'alimenter une boucle
d'amelioration continue.

Dans cet objectif retrospectif, les variables suivantes peuvent etre integrees
aux entrees du modele :

- `imprevus` ;
- `reorganisation_necessaire` ;
- `respect_budget` ;
- indicateurs extraits de `retour_client`, par exemple un score de sentiment.

Ces variables sont pertinentes dans ce second cadre, car elles decrivent le
deroulement reel du sejour et le ressenti client. Elles permettent d'identifier
les facteurs qui expliquent le mieux la satisfaction ou l'insatisfaction.

Le modele post-voyage peut donc servir a :

- analyser les causes d'insatisfaction ;
- identifier les situations a risque ;
- mesurer l'impact des imprevus sur la satisfaction ;
- comprendre le role du respect du budget ;
- ameliorer les recommandations futures ;
- alimenter un processus qualite pour l'agence.

### Synthese du plan d'action

La strategie retenue est donc la suivante :

1. conserver le modele pre-voyage comme modele principal conforme au cas
   d'usage initial ;
2. documenter clairement ses limites et expliquer pourquoi les performances
   restent faibles ;
3. ne pas utiliser les variables post-voyage dans ce modele afin d'eviter toute
   fuite de donnees ;
4. creer une experience separee post-voyage pour expliquer la satisfaction
   client apres realisation du sejour ;
5. utiliser les enseignements du modele post-voyage pour enrichir
   progressivement les donnees disponibles avant depart.

Cette approche transforme les faibles performances du modele pre-voyage en
resultat exploitable : le projet demontre que la satisfaction client depend
fortement de facteurs observes pendant ou apres le sejour. L'enjeu metier n'est
donc pas seulement de changer d'algorithme, mais d'ameliorer la collecte de
donnees et la qualite des signaux disponibles avant la planification.

## 21. Experience post-voyage

Une experience separee est creee dans le notebook
`notebooks/objectif_2_post_voyage.ipynb`.

### Objectif

L'objectif n'est plus de predire la satisfaction avant le depart, mais de
l'expliquer apres la realisation du sejour. Cette approche correspond a une
analyse retrospective et a une logique d'amelioration continue.

### Variables utilisees

Contrairement au modele pre-voyage, cette experience inclut les variables
observees pendant ou apres le sejour :

| Variable | Role dans l'objectif post-voyage |
| --- | --- |
| `imprevus` | Decrire l'evenement reel survenu pendant le sejour |
| `reorganisation_necessaire` | Mesurer si le sejour a necessite une adaptation operationnelle |
| `respect_budget` | Indiquer si le budget a ete respecte |
| `sentiment_retour` | Resumer le ressenti client a partir du commentaire |
| `retour_client_vide` | Identifier l'absence de commentaire exploitable |

Le texte brut `retour_client` n'est pas donne directement au modele. Il est
transforme en indicateurs simples afin de conserver une experience legere et
explicable.

### Premier resultat

Le premier test post-voyage utilise 1418 lignes et 27 variables d'entree :

| Type de variable | Nombre |
| --- | ---: |
| Numeriques | 20 |
| Categorielles | 7 |
| Total | 27 |

Les premiers resultats obtenus sont :

| Modele | Accuracy | Balanced accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| `RandomForest` | 0.4331 | 0.4327 | 0.4222 |
| `LogisticRegression` | 0.3979 | 0.4057 | 0.3983 |
| `ExtraTrees` | 0.3521 | 0.3646 | 0.3537 |
| `Dummy_majority` | 0.2887 | 0.2000 | 0.0896 |

### Interpretation

Les performances progressent nettement par rapport au modele pre-voyage. Le
meilleur `macro_f1` passe de `0.2402` avec l'objectif pre-voyage enrichi a
`0.4222` avec l'objectif post-voyage.

Cette amelioration confirme l'hypothese issue de la Mutual Information : les
variables post-voyage contiennent davantage de signal pour expliquer la
satisfaction client. En particulier, les imprevus, le respect du budget, la
reorganisation du sejour et le ressenti client sont plus proches de
l'experience reellement vecue par le client.

Cette experience ne remplace pas le modele pre-voyage. Elle repond a un autre
besoin metier :

- comprendre les causes d'insatisfaction ;
- piloter la qualite operationnelle ;
- prioriser les actions correctives ;
- alimenter les futures donnees disponibles avant depart ;
- renforcer la boucle d'amelioration continue.

La conclusion est donc double :

- le modele pre-voyage reste le modele conforme au cas d'usage de planification,
  mais ses performances sont limitees par le manque de signal ;
- le modele post-voyage est plus performant, mais il doit etre presente comme
  un modele explicatif retrospectif, non comme un outil de prediction avant
  depart.

## 22. Recommandations pour la suite

Les prochaines ameliorations prioritaires sont :

1. ajouter des donnees reelles de qualite hoteliere ;
2. ajouter la duree exacte des vols et le nombre reel d'escales ;
3. ajouter des donnees meteo reelles au moment du sejour ;
4. exploiter les avis clients avec une analyse NLP ;
5. ajouter un historique client ;
6. ajouter des indicateurs de qualite de service ;
7. valider avec le metier si la cible `satisfaction_client` est suffisamment
   fiable ;
8. tester des modeles plus adaptes apres enrichissement reel des donnees.

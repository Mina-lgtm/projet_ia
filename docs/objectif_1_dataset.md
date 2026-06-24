# Objectif 1 - Identification du jeu de donnees

## 1. Objectif de l'etape

L'objectif de cette etape est d'identifier et de justifier un jeu de donnees
capable de repondre aux besoins metiers et aux cas d'usage du projet TravelMind.

Le contexte metier est celui d'une agence de voyages haut de gamme qui souhaite
personnaliser la planification des sejours, anticiper les risques et ameliorer
ses propositions grace aux retours clients.

Le jeu de donnees etudie est :

```text
data/Examen_travel_planning_dataset.csv
```

Il contient des informations sur des sejours passes : profils clients, budgets,
destinations, saisons, durees, hebergements, vols, meteo, activites, imprevus,
satisfaction et respect du budget.

## 2. Datasheet du jeu de donnees

Cette datasheet synthetise les informations essentielles sur le dataset afin de
justifier son usage dans le projet TravelMind.

### Identification

| Element | Description |
| --- | --- |
| Nom du fichier | `Examen_travel_planning_dataset.csv` |
| Emplacement | `data/Examen_travel_planning_dataset.csv` |
| Format | CSV |
| Domaine metier | Planification de voyages haut de gamme |
| Volume | 1500 lignes, 15 colonnes |
| Acces | Disponible localement dans le projet |
| Nature des donnees | Donnees synthetiques et anonymisees |
| Usage principal | Analyse et prediction liees a la personnalisation des sejours |

### Description generale

Chaque ligne represente un sejour passe. Le dataset permet d'analyser comment un
profil client, une destination, une saison, une duree, un budget, un hebergement,
un vol et des imprevus peuvent influencer la satisfaction finale et la qualite du
sejour.

### Variables principales

| Colonne | Type metier | Utilite pour le projet |
| --- | --- | --- |
| `trip_id` | Identifiant | Suivi technique, a exclure du modele |
| `client_type` | Categorie client | Adapter les propositions au profil du voyageur |
| `budget_total` | Numerique | Tenir compte de la contrainte budgetaire globale |
| `destination` | Categorie | Comparer les destinations possibles |
| `saison` | Categorie | Tenir compte de la periode du voyage |
| `duree_jours` | Numerique | Evaluer l'impact de la duree du sejour |
| `type_hebergement` | Categorie | Evaluer l'impact du logement sur l'experience |
| `prix_vol` | Numerique | Mesurer l'impact du prix du billet d'avion sur le budget total |
| `meteo_prevue` | Categorie | Anticiper les risques lies a la meteo |
| `activite_principale` | Categorie | Relier le sejour aux centres d'interet du client |
| `satisfaction_client` | Numerique | Cible principale recommandee pour evaluer la qualite du sejour |
| `imprevus` | Categorie | Cible ou variable d'analyse pour comprendre les incidents |
| `reorganisation_necessaire` | Binaire | Cible secondaire pour anticiper les sejours a reorganiser |
| `respect_budget` | Binaire | Cible secondaire ou contrainte de controle budgetaire |
| `retour_client` | Texte | Source future pour l'analyse NLP des avis clients |

### Cibles IA envisagees

Plusieurs cibles sont possibles, mais elles n'ont pas le meme role. Pour un
premier modele coherent avec le contexte, une seule cible principale doit etre
retenue.

| Cible | Priorite | Type de probleme | Interet metier |
| --- | --- | --- | --- |
| `satisfaction_client` | Principale recommandee | Regression ou classification ordinale | Predire la qualite attendue d'un sejour et guider la personnalisation |
| `reorganisation_necessaire` | Secondaire | Classification binaire | Anticiper les sejours qui risquent d'etre reorganises |
| `respect_budget` | Secondaire | Classification binaire | Controler le risque de non-respect du budget |
| `imprevus` | Secondaire ou future | Classification multiclasses | Anticiper le type d'incident possible |
| `retour_client` | Future | Analyse de texte | Exploiter les avis clients pour ameliorer les propositions |

### Cible principale retenue

La cible principale recommandee est :

```text
satisfaction_client
```

Ce choix est le plus coherent avec le contexte, car la solution attendue est
centree sur la personnalisation et la satisfaction client.

Le modele peut predire une satisfaction attendue pour plusieurs options de
sejour, puis aider a recommander l'option qui maximise la satisfaction tout en
respectant les contraintes de budget, de duree, de saison et de risque.

### Pourquoi ne pas choisir `destination` comme cible principale ?

La destination est un element a recommander, mais la predire directement comme
cible principale reviendrait surtout a reproduire les destinations observees
dans l'historique. Cela ne garantit pas que la destination recommandee soit la
meilleure pour le client.

Une approche plus pertinente consiste a predire la satisfaction attendue pour
plusieurs destinations possibles, puis a recommander celle qui obtient le
meilleur score sous contraintes metier.

### Qualite et points de vigilance

| Point controle | Observation |
| --- | --- |
| Fichier accessible | Oui |
| Format lisible | Oui, CSV |
| Volume du dataset | 1500 lignes, suffisant pour un prototype et une premiere experimentation IA |
| Valeurs manquantes | Presentes sur plusieurs colonnes |
| Variables categorielles | Plusieurs colonnes a encoder |
| Variables numeriques | Budget, duree, prix du vol, satisfaction |
| Echelle de satisfaction | Le contexte indique une echelle `1 a 5`, mais le fichier observe contient des valeurs de `0 a 7` |
| Confidentialite | Donnees synthetiques et anonymisees, utilisables dans le cadre de la certification |

### Usage prevu

Le dataset est prevu pour :

- analyser les facteurs qui influencent la satisfaction client ;
- entrainer un premier modele de prediction de satisfaction ;
- comparer plusieurs options de sejour ;
- utiliser `respect_budget` et `reorganisation_necessaire` comme indicateurs
  secondaires de risque ;
- construire une API de prediction une fois le modele final choisi.

### Usages non prevus a ce stade

Le dataset n'est pas encore utilise pour :

- prendre automatiquement des decisions commerciales ;
- remplacer un conseiller voyage ;
- garantir une recommandation finale sans validation humaine ;
- analyser finement le texte des retours clients.

Ces usages pourraient etre envisages plus tard, apres validation metier,
nettoyage des donnees et evaluation fiable du modele.

## 3. Besoins metiers identifies

L'agence de voyages souhaite proposer une planification haut de gamme plus
personnalisee, plus fiable et plus reactive face aux imprevus.

Les besoins metiers identifies sont :

- recommander des destinations adaptees au profil du voyageur ;
- tenir compte du budget, des centres d'interet, de la saison et de la duree ;
- planifier les elements logistiques : vol, hebergement et organisation du
  sejour ;
- anticiper les imprevus comme la meteo, les retards, les annulations ou les
  problemes de bagages ;
- identifier les voyages qui risquent de necessiter une reorganisation ;
- ameliorer la satisfaction client ;
- exploiter les retours clients pour ameliorer les futures propositions ;
- fournir un outil d'aide a la decision aux conseillers voyage.

Ces besoins sont coherents avec les donnees disponibles, car le fichier contient
a la fois des variables de contexte avant sejour et des indicateurs de resultat
apres sejour.

## 4. Cas d'usage decrits

### Cas d'usage 1 - Recommandation personnalisee de sejour

Le modele predit la satisfaction attendue pour differentes options de sejour.

Variable cible principale :

```text
satisfaction_client
```

Exemple d'utilisation :

Pour un client de type `couple`, avec un budget donne, une saison, une duree et
des activites preferees, le modele peut comparer plusieurs destinations ou types
d'hebergement et estimer la satisfaction attendue.

Interet metier :

- personnaliser les propositions ;
- prioriser les sejours les plus susceptibles de satisfaire le client ;
- ameliorer la qualite du conseil ;
- aligner la solution IA avec l'objectif central de satisfaction client.

### Cas d'usage 2 - Anticipation des reorganisation et imprevus

Le modele peut aider a estimer si un sejour risque de necessiter une
reorganisation.

Variable cible possible :

```text
reorganisation_necessaire
```

Autre cible possible :

```text
imprevus
```

Exemple d'utilisation :

Avant le depart, l'agence identifie les voyages sensibles selon la destination,
la saison, la meteo prevue, le type d'hebergement ou le type d'activite.

Interet metier :

- prioriser les dossiers a risque ;
- preparer des alternatives ;
- reduire les urgences operationnelles ;
- ameliorer l'experience client.

### Cas d'usage 3 - Controle du respect du budget

Le modele peut apprendre a predire si un voyage respectera le budget prevu.

Variable cible possible :

```text
respect_budget
```

Exemple d'utilisation :

Un conseiller renseigne le profil du client, la destination, la saison, la duree,
le type d'hebergement et le prix du vol. Le modele indique si le sejour presente
un risque de non-respect du budget.

Interet metier :

- anticiper les depassements ;
- proposer des ajustements avant validation ;
- securiser la relation client ;
- eviter les mauvaises surprises.

### Cas d'usage 4 - Amelioration continue avec les retours clients

Le texte libre des retours clients peut etre exploite dans une phase future.

Variable exploitable :

```text
retour_client
```

Exemple d'utilisation :

Les commentaires clients peuvent etre analyses pour extraire des themes
recurrents : satisfaction, deception, probleme logistique, qualite de
l'hebergement ou meteo.

Interet metier :

- comprendre les causes d'insatisfaction ;
- enrichir le modele avec des signaux qualitatifs ;
- ameliorer progressivement les offres.

## 5. Donnees disponibles dans le fichier

Le fichier CSV a ete verifie localement.

| Element | Valeur observee |
| --- | --- |
| Chemin | `data/Examen_travel_planning_dataset.csv` |
| Format | CSV |
| Encodage lu correctement | UTF-8 |
| Taille du fichier | 161255 octets |
| Nombre de lignes | 1500 |
| Nombre de colonnes | 15 |
| Acces local | Verifie |

Les colonnes ont ete verifiees lors de la lecture du fichier. Leur description
detaillee est presentee une seule fois dans la datasheet, section "Variables
principales", afin d'eviter les repetitions.

## 6. Choix de la cible principale

Compte tenu du contexte, la cible la plus pertinente pour le premier modele est
`satisfaction_client`.

### Justification metier

Le projet demande une solution centree sur la satisfaction client. L'objectif
n'est pas seulement de respecter un budget ou d'eviter une reorganisation, mais
de proposer un sejour personnalise et de qualite.

`satisfaction_client` mesure directement le resultat metier recherche :
l'experience finale du client.

### Justification IA

Cette cible permet de construire un modele capable d'estimer la satisfaction
attendue pour une proposition de sejour. Le conseiller peut ensuite comparer
plusieurs options et choisir celle qui maximise la satisfaction tout en
respectant les contraintes.

### Role des autres cibles

Les autres cibles restent importantes, mais elles sont secondaires :

- `respect_budget` sert a controler le risque budgetaire ;
- `reorganisation_necessaire` sert a anticiper les dossiers instables ;
- `imprevus` peut servir a predire le type d'incident ;
- `retour_client` peut enrichir le systeme plus tard avec de l'analyse de texte.

## 7. Donnees pertinentes pour alimenter le modele IA

Pour un premier modele de prediction de satisfaction, les donnees a priori
pertinentes sont les informations disponibles avant ou pendant la planification
du sejour :

- `client_type` ;
- `budget_total` ;
- `destination` ;
- `saison` ;
- `duree_jours` ;
- `type_hebergement` ;
- `prix_vol` ;
- `meteo_prevue` ;
- `activite_principale`.

La variable cible principale est :

```text
satisfaction_client
```

Ces donnees sont pertinentes car elles decrivent les principaux leviers de
personnalisation : profil du client, budget, destination, saison, duree,
hebergement, transport, meteo et centre d'interet.

### Prevention de la fuite de donnees

Pour un modele qui doit aider a planifier un sejour avant sa realisation, il ne
faut pas utiliser comme variables explicatives des informations connues seulement
apres le voyage.

Les colonnes suivantes doivent donc etre traitees avec prudence :

- `imprevus` ;
- `reorganisation_necessaire` ;
- `respect_budget` ;
- `retour_client`.

Elles peuvent servir a l'analyse, a des modeles secondaires ou a l'evaluation,
mais pas comme variables d'entree du premier modele de satisfaction si elles ne
sont pas connues au moment de la recommandation.

## 8. Donnees necessaires a minima

Pour alimenter un modele minimal de prediction de satisfaction, toutes les
colonnes ne sont pas indispensables.

Les donnees minimales recommandees sont :

| Donnee minimale | Pourquoi elle est necessaire |
| --- | --- |
| `client_type` | Adapter la recommandation au profil du voyageur |
| `budget_total` | Respecter la contrainte budgetaire |
| `destination` | Comparer les options de sejour |
| `saison` | Tenir compte de la periode du voyage |
| `duree_jours` | Adapter la proposition a la duree disponible |
| `type_hebergement` | Evaluer l'impact du logement sur l'experience |
| `prix_vol` | Integrer le cout du transport |
| `activite_principale` | Representer le centre d'interet principal |
| `satisfaction_client` | Variable cible pour entrainer le modele |

Les autres colonnes enrichissent le projet, mais peuvent etre traitees dans un
second temps.

## 9. Pertinence et representativite du dataset

Le dataset est pertinent pour le projet car il couvre plusieurs dimensions
metier importantes :

- profils clients : `business`, `solo`, `senior`, `couple`, `famille` ;
- destinations variees : New York, Rome, Lisbonne, Bali, Paris, Dubai, Tokyo,
  Sydney ;
- saisons : automne, ete, printemps, hiver ;
- types d'hebergement : villa, appartement, hotel, resort ;
- meteo prevue : ensoleille, pluie, variable, nuageux ;
- activites : culture, plage, business, gastronomie, randonnee ;
- imprevus : meteo, retard de vol, bagages, annulation, aucun.

Repartition observee de quelques variables :

| Variable | Repartition observee |
| --- | --- |
| `client_type` | 5 profils clients differents |
| `destination` | 8 destinations differentes |
| `saison` | 4 saisons representees |
| `respect_budget` | 1041 valeurs `1`, 459 valeurs `0` |
| `reorganisation_necessaire` | 830 valeurs `1`, 670 valeurs `0` |

Le dataset est suffisamment diversifie pour construire un premier cas d'usage IA
centre sur la personnalisation des sejours.

## 10. Verification de coherence initiale

Une premiere verification du fichier a ete realisee.

Valeurs numeriques observees :

| Colonne | Minimum | Maximum | Moyenne |
| --- | ---: | ---: | ---: |
| `budget_total` | 380.0 | 41000.0 | 7194.04 |
| `duree_jours` | 2 | 42 | 10.45 |
| `prix_vol` | 35.0 | 5200.0 | 1125.81 |
| `satisfaction_client` | 0.0 | 7.0 | 2.78 |

Distribution observee de `satisfaction_client` :

| Valeur | Nombre de lignes |
| --- | ---: |
| Valeur manquante | 25 |
| `0.0` | 1 |
| `1.0` | 258 |
| `2.0` | 427 |
| `3.0` | 353 |
| `4.0` | 258 |
| `5.0` | 174 |
| `6.0` | 3 |
| `7.0` | 1 |

Valeurs manquantes observees :

| Colonne | Valeurs manquantes |
| --- | ---: |
| `budget_total` | 40 |
| `type_hebergement` | 36 |
| `prix_vol` | 53 |
| `meteo_prevue` | 39 |
| `activite_principale` | 48 |
| `satisfaction_client` | 25 |
| `imprevus` | 53 |
| `retour_client` | 25 |

### Point de coherence sur la satisfaction

Le contexte du projet indique que `satisfaction_client` est un score de `1 a 5`.
Le fichier observe contient cependant quelques valeurs hors de cette echelle :
`0.0`, `6.0` et `7.0`.

Ce point doit etre documente et traite avant l'entrainement :

- soit en corrigeant ou filtrant les valeurs hors echelle ;
- soit en justifiant une echelle differente si elle est confirmee par le metier ;
- soit en regroupant les scores dans des classes de satisfaction.

## 11. Existence, disponibilite et acces des donnees

L'existence du fichier a ete verifiee localement.

Le fichier est disponible dans le projet a l'emplacement :

```text
data/Examen_travel_planning_dataset.csv
```

L'acces a ete verifie par lecture du fichier CSV. Les colonnes, le nombre de
lignes, les valeurs manquantes et les distributions principales ont ete
inspectes.

Le fichier est donc :

- existant ;
- accessible localement ;
- lisible en CSV ;
- exploitable avec Python ;
- adapte a une premiere phase d'analyse IA.

Les donnees sont synthetiques et anonymisees. Elles sont utilisables librement
dans le cadre de la certification. Si le projet etait enrichi avec des donnees
reelles, une verification RGPD et confidentialite serait necessaire.

## 12. Limites identifiees

Malgre sa pertinence, le dataset presente plusieurs limites :

- certaines colonnes contiennent des valeurs manquantes ;
- le volume reste modere avec 1500 lignes ;
- le fichier est un dataset synthetique de projet ;
- la colonne `retour_client` est textuelle et demandera un traitement specifique ;
- la colonne `satisfaction_client` presente un ecart entre l'echelle annoncee
  dans le contexte et certaines valeurs observees ;
- il faut eviter d'utiliser des variables post-voyage comme entrees du modele si
  l'objectif est de recommander un sejour avant sa realisation.

Ces limites ne bloquent pas l'objectif 1, mais elles devront etre traitees aux
etapes suivantes : nettoyage, preparation, entrainement et evaluation.

## 13. Solutions alternatives en cas d'indisponibilite

Si le fichier CSV devient indisponible, incomplet ou inaccessible, plusieurs
solutions alternatives peuvent etre envisagees.

### Alternative 1 - Recuperer les donnees depuis le systeme metier

Sources possibles :

- historique de reservations ;
- CRM client ;
- outils de gestion des voyages ;
- factures et devis ;
- retours clients ;
- historiques d'incidents.

Cette option est la plus pertinente si l'objectif est de construire un modele
proche de la realite operationnelle.

### Alternative 2 - Utiliser des sources externes

Sources possibles :

- API de prix de vols ;
- API hotelieres ;
- API meteorologiques ;
- donnees publiques touristiques ;
- historiques de prix par destination ;
- plateformes d'avis clients.

Ces donnees peuvent enrichir le modele si le dataset local manque de contexte.
Elles doivent etre documentees et utilisees dans le respect des exigences RGPD
et reglementaires.

### Alternative 3 - Creer ou completer un dataset synthetique

Si aucune donnee reelle n'est disponible, il est possible de creer un dataset
synthetique controle.

Cette option est utile pour :

- prototyper rapidement ;
- tester la chaine IA ;
- simuler plusieurs scenarios metiers.

Elle est moins fiable qu'un historique reel et doit etre clairement documentee.

### Alternative 4 - Reduire le perimetre du cas d'usage

Si certaines colonnes sont indisponibles, le cas d'usage peut etre simplifie.

Exemples :

- predire la satisfaction sans exploiter les commentaires texte ;
- predire uniquement le respect du budget avec `budget_total`, `prix_vol` et
  `duree_jours` ;
- construire un modele descriptif plutot qu'un modele predictif.

## 14. Conclusion sur l'objectif 1

Le jeu de donnees `Examen_travel_planning_dataset.csv` est representatif et
adapte a une premiere reponse aux besoins metiers du projet.

Il permet de traiter plusieurs cas d'usage coherents :

- recommandation personnalisee de sejours ;
- prediction de la satisfaction client ;
- anticipation des reorganisation et imprevus ;
- controle du respect du budget ;
- amelioration continue avec les retours clients.

La cible principale recommandee est `satisfaction_client`, car elle correspond
directement a l'objectif central du projet : concevoir une solution IA centree
sur la qualite de l'experience et la satisfaction client.

Les donnees disponibles sont pertinentes pour alimenter un premier modele IA.
Les donnees necessaires a minima sont identifiees, l'existence et l'acces au
fichier ont ete verifies, et des alternatives sont prevues si les donnees
deviennent indisponibles ou insuffisantes.

La prochaine etape consiste a nettoyer le dataset, traiter les valeurs manquantes
et confirmer la gestion de l'echelle de `satisfaction_client`.


# Modélisation


Les corrélations individuelles étaient faibles.

Donc ton signal est probablement :

non linéaire ;
composé d'interactions entre variables ;
mieux capturé par les arbres.

Ton problème ressemble fortement à un problème tabulaire classique où :

les effets sont non linéaires ;
les variables interagissent entre elles ;
la satisfaction dépend de combinaisons de facteurs.

Dans ce contexte :

✅ Random Forest
✅ XGBoost
✅ LightGBM
✅ CatBoost

sont souvent les meilleurs choix.

La régression linéaire sert surtout de baseline.
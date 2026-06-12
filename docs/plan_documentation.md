# Plan de documentation du projet IA

Ce plan est deduit de l'analyse du notebook exemple
`NBE-E-Commerce-IA.ipynb` et adapte au projet de planification de voyages haut
de gamme.

Le notebook exemple suit une logique complete :

1. contexte et besoin metier ;
2. journal de bord et choix de conception ;
3. dataset et dictionnaire de donnees ;
4. exploration des donnees ;
5. preparation et transformation ;
6. choix du modele ;
7. entrainement et evaluation ;
8. interpretation des performances ;
9. prototype applicatif ;
10. risques, biais et limites ;
11. amelioration continue ;
12. conclusion et annexes.

## 1. Documentation generale du projet

Fichier conseille :

```text
docs/etat_projet.md
```

Objectif :

- expliquer l'etat actuel du projet ;
- documenter les choix techniques ;
- garder une trace des decisions ;
- resumer l'environnement, Docker, Git, API et notebook.

Etat actuel :

- deja cree ;
- a maintenir au fur et a mesure de l'avancement.

## 2. Besoin metier et cas d'usage

Fichier conseille :

```text
docs/01_besoin_metier_cas_usage.md
```

Contenu attendu :

- contexte de l'agence de voyages haut de gamme ;
- objectifs metiers ;
- acteurs concernes : conseiller, client, equipe operationnelle ;
- cas d'usage principaux ;
- valeur attendue de la solution IA ;
- contraintes metier : budget, saison, duree, imprevus, satisfaction.

Etat actuel :

- partiellement couvert dans `docs/objectif_1_dataset.md`.

## 3. Identification et justification du dataset

Fichier conseille :

```text
docs/objectif_1_dataset.md
```

Contenu attendu :

- datasheet du dataset ;
- besoins metiers identifies ;
- cas d'usage ;
- donnees disponibles ;
- donnees pertinentes ;
- donnees necessaires a minima ;
- verification de l'existence et de l'acces ;
- limites et alternatives ;
- justification de la cible principale.

Etat actuel :

- deja cree ;
- cible principale actuelle : `satisfaction_client`.

## 4. Exploration des donnees

Fichier conseille :

```text
docs/02_exploration_donnees.md
```

Notebook associe :

```text
notebooks/01_exploration.ipynb
```

Contenu attendu :

- dimensions du dataset ;
- types des variables ;
- valeurs manquantes ;
- doublons ;
- distributions numeriques ;
- distributions categorielles ;
- analyse de `satisfaction_client` ;
- relation entre satisfaction et profil client ;
- relation entre satisfaction et destination ;
- relation entre satisfaction et saison ;
- relation entre satisfaction et imprevus ;
- premiers constats metier.

Etat actuel :

- notebook cree ;
- documentation d'analyse exploratoire a produire apres execution stable du
  notebook.

## 5. Preparation et nettoyage des donnees

Fichier conseille :

```text
docs/03_preparation_donnees.md
```

Contenu attendu :

- traitement des valeurs manquantes ;
- traitement des valeurs hors echelle de `satisfaction_client` ;
- encodage des variables categorielles ;
- normalisation ou standardisation si necessaire ;
- prevention de la fuite de donnees ;
- separation des variables connues avant voyage et apres voyage ;
- justification des colonnes conservees ou exclues.

Point important :

Pour predire `satisfaction_client`, les colonnes post-voyage comme
`retour_client`, `respect_budget`, `reorganisation_necessaire` et `imprevus`
doivent etre utilisees avec prudence afin d'eviter la fuite de donnees.

## 6. Choix du modele IA

Fichier conseille :

```text
docs/04_choix_modele.md
```

Contenu attendu :

- formulation du probleme IA ;
- choix entre regression, classification ordinale ou classification multiclasses ;
- modeles envisages ;
- modele baseline ;
- justification du modele retenu ;
- criteres de choix : interpretabilite, performance, robustesse, industrialisation ;
- limites des modeles non retenus.

Recommandation initiale :

- cible principale : `satisfaction_client` ;
- premiere approche possible : classification des scores de satisfaction ;
- modele baseline possible : regression logistique ou arbre de decision ;
- modele plus avance possible : random forest, gradient boosting ou histogram
  gradient boosting.

## 7. Entrainement et evaluation

Fichier conseille :

```text
docs/05_entrainement_evaluation.md
```

Contenu attendu :

- separation train/test ;
- choix des metriques ;
- entrainement du modele baseline ;
- comparaison de plusieurs modeles ;
- matrice de confusion si classification ;
- erreur moyenne si regression ;
- analyse par segment client ;
- analyse des erreurs ;
- conclusion sur la performance.

Exemples de metriques :

- accuracy, precision, recall, F1 si classification ;
- MAE, RMSE, R2 si regression ;
- score par type de client ou destination pour verifier les ecarts de
  performance.

## 8. Interpretation et valeur metier

Fichier conseille :

```text
docs/06_interpretation_resultats.md
```

Contenu attendu :

- importance des variables ;
- facteurs influencant la satisfaction ;
- limites d'interpretation ;
- exemples de recommandations ;
- lien entre predictions et actions conseiller ;
- analyse des erreurs significatives.

Objectif :

Transformer les resultats du modele en enseignements metier exploitables.

## 9. Prototype API et industrialisation

Fichier conseille :

```text
docs/07_api_docker_industrialisation.md
```

Contenu attendu :

- architecture API ;
- role de FastAPI ;
- endpoint `/health` ;
- endpoint `/predict` cible ;
- format attendu des donnees d'entree ;
- format de sortie ;
- role de Docker ;
- port `8001` ;
- procedure de lancement ;
- limites de l'API actuelle ;
- adaptations necessaires pour le modele final.

Etat actuel :

- API demo deja creee ;
- Docker deja configure ;
- endpoint `/predict` encore base sur le dataset Iris.

## 10. Risques, biais, RGPD et limites

Fichier conseille :

```text
docs/08_risques_biais_rgpd.md
```

Contenu attendu :

- risques de biais par type de client ;
- risques de biais par destination ;
- limites du dataset synthetique ;
- risques de fuite de donnees ;
- contraintes RGPD si ajout de donnees reelles ;
- risque de sur-automatisation ;
- necessite de validation humaine ;
- limites de generalisation.

Point important :

Le dataset actuel est synthetique et anonymise. Les risques RGPD sont limites
dans ce cadre, mais ils deviennent importants si le projet est enrichi avec des
donnees clients reelles.

## 11. Amelioration continue et MLOps

Fichier conseille :

```text
docs/09_amelioration_continue_mlops.md
```

Contenu attendu :

- donnees supplementaires utiles ;
- API meteo ;
- donnees tarifaires ;
- donnees d'avis clients ;
- monitoring des performances ;
- detection du drift ;
- reeentrainement du modele ;
- tests continus ;
- suivi de la satisfaction post-recommandation ;
- versionnement des modeles.

Objectif :

Montrer que la solution peut evoluer vers une solution industrialisable.

## 12. Conclusion generale

Fichier conseille :

```text
docs/10_conclusion_generale.md
```

Contenu attendu :

- bilan du projet ;
- reponse au besoin metier ;
- valeur apportee par l'IA ;
- limites actuelles ;
- recommandations pour passer du prototype a une solution robuste ;
- prochaines etapes.

## 13. Annexes

Fichier conseille :

```text
docs/annexes.md
```

Contenu possible :

- dictionnaire de donnees complet ;
- commandes utiles ;
- captures ou resultats d'execution ;
- exemples de payload API ;
- choix non retenus ;
- journal des problemes techniques ;
- liens vers notebooks et fichiers importants.

## Priorite de redaction

Ordre recommande :

1. finaliser `docs/objectif_1_dataset.md` ;
2. produire `docs/02_exploration_donnees.md` apres analyse du notebook ;
3. produire `docs/03_preparation_donnees.md` ;
4. produire `docs/04_choix_modele.md` ;
5. produire `docs/05_entrainement_evaluation.md` ;
6. mettre a jour `docs/07_api_docker_industrialisation.md` quand le modele final
   sera integre a l'API ;
7. terminer par risques, MLOps, conclusion et annexes.

## Correspondance avec le notebook exemple

| Notebook exemple e-commerce | Adaptation projet voyages |
| --- | --- |
| Compréhension du besoin | Besoin metier agence haut de gamme |
| Creation dataset | Datasheet du dataset voyages |
| Exploration des donnees | EDA du dataset travel planning |
| Preparation et transformation | Nettoyage, encodage, anti-fuite |
| Choix du modele | Modele de satisfaction client |
| Entrainement et evaluation | Baseline puis comparaison de modeles |
| Performance et interpretation | Facteurs de satisfaction et limites |
| Prototype Flask | API FastAPI + Docker |
| Risques, biais, ethique | Biais client, RGPD, donnees synthetiques |
| Amelioration continue | Sources externes, monitoring, retrain |
| Conclusion | Bilan et passage a l'industrialisation |

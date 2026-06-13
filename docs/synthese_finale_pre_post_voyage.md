# Synthese finale - Modelisation pre-voyage et post-voyage

## 1. Objectif du document

Ce document synthetise le notebook final :

```text
notebooks/00_notebook_final_pre_post_voyage.ipynb
```

Il sert de point de passage entre la phase d'exploration/modelisation et la
phase suivante du projet : industrialisation, entrainement reproductible,
export du modele et API.

## 2. Donnees utilisees

Dataset :

```text
data/Examen_travel_planning_dataset.csv
```

Volume initial :

| Etape | Nombre de lignes | Lignes supprimees |
| --- | ---: | ---: |
| Dataset brut | 1500 | 0 |
| Cible `satisfaction_client` valide | 1470 | 30 |
| Coherence initiale `prix_vol <= budget_total` | 1418 | 52 |
| Controle budget apres traitement des outliers | 1414 | 4 |

Volume final utilise dans le notebook propre :

```text
1414 lignes
```

## 3. Traitements appliques

### Nettoyage

- normalisation des variables textuelles ;
- conversion des colonnes numeriques ;
- suppression des lignes avec cible manquante ou hors echelle 1-5 ;
- suppression des lignes ou `prix_vol > budget_total` ;
- imputation des valeurs manquantes ;
- traitement des outliers par methode IQR avec remplacement par la mediane ;
- controle metier final apres traitement des outliers.

### Feature engineering

Variables creees :

- `budget_par_jour` ;
- `part_vol_budget` ;
- `sejour_long` ;
- `meteo_risque` ;
- `randonnee_meteo_risque` ;
- `client_business` ;
- `hebergement_luxe` ;
- variables d'enrichissement destination ;
- variables explicatives post-voyage liees aux imprevus, au budget et a la
  reorganisation.

Variables supprimees des entrees du modele pour simplifier le signal et limiter
les redondances :

- `budget_hors_vol` ;
- `saison_haute` ;
- `cout_vie_destination` ;
- `type_destination` ;
- `decalage_horaire_categorie` ;
- `risque_meteo_destination` ;
- `annulation_et_reorganisation` ;
- `retard_et_budget_non_respecte` ;
- `imprevu_transport_et_sejour_court` ;
- `budget_tendu_et_hebergement_luxe`.

## 4. Modele pre-voyage

Objectif : predire `satisfaction_client` avant le depart.

Variables exclues pour eviter la fuite de donnees :

- `imprevus` ;
- `reorganisation_necessaire` ;
- `respect_budget` ;
- `retour_client` ;
- variables derivees des imprevus et du retour client.

Resultats :

| Modele | Accuracy | Balanced accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| `ExtraTrees_pre` | 0.2438 | 0.2390 | 0.2340 |
| `RandomForest_pre` | 0.2297 | 0.2138 | 0.2135 |
| `LogisticRegression_pre` | 0.1873 | 0.1929 | 0.1856 |
| `Dummy_majority_pre` | 0.2898 | 0.2000 | 0.0899 |

Conclusion :

Le modele pre-voyage est conforme au cas d'usage de planification, mais ses
performances sont faibles. Les variables disponibles avant le sejour ne
contiennent pas assez de signal pour predire finement la satisfaction.

## 5. Modele post-voyage

Objectif : expliquer la satisfaction apres le sejour.

Variables incluses :

- `imprevus` ;
- `reorganisation_necessaire` ;
- `respect_budget` ;
- variables explicatives derivees des imprevus, du budget et de la
  reorganisation.

Variable exclue :

- `retour_client`, car le texte libre est trop proche de la satisfaction finale.

La cible est regroupee en 3 classes :

| Classe | Signification |
| --- | --- |
| 0 | notes 1-2, insatisfait |
| 1 | note 3, neutre |
| 2 | notes 4-5, satisfait |

Resultats :

| Modele | Accuracy | Balanced accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| `ExtraTrees_3_classes_SMOTE` | 0.4523 | 0.4066 | 0.4054 |
| `RandomForest_3_classes_SMOTE` | 0.4841 | 0.4148 | 0.4007 |
| `ExtraTrees_3_classes` | 0.4346 | 0.3955 | 0.3939 |
| `RandomForest_3_classes` | 0.4700 | 0.4062 | 0.3921 |
| `RandomForest_3_classes_optimise_500` | 0.4558 | 0.3999 | 0.3888 |
| `XGBoost_3_classes_optimise` | 0.4488 | 0.3836 | 0.3731 |
| `LogisticRegression_3_classes` | 0.3816 | 0.3695 | 0.3669 |
| `LogisticRegression_3_classes_SMOTE` | 0.3710 | 0.3586 | 0.3561 |
| `Dummy_majority_3_classes` | 0.4664 | 0.3333 | 0.2120 |

Modele retenu dans le notebook final :

```text
ExtraTrees_3_classes
```

Justification :

- meilleur `macro_f1` parmi les modeles simples sans sur-echantillonnage ;
- pipeline plus simple a industrialiser et coherent avec l'API ;
- SMOTE donne un leger gain de `macro_f1`, mais reste classe comme test
  complementaire non retenu a ce stade.

## 6. Validation croisee du modele retenu

La validation croisee a ete ajoutee au notebook final pour verifier la stabilite
du modele `ExtraTrees_3_classes` sur plusieurs decoupages.

| Metrique | Moyenne | Ecart type |
| --- | ---: | ---: |
| `accuracy` | 0.4477 | 0.0314 |
| `balanced_accuracy` | 0.4004 | 0.0235 |
| `macro_f1` | 0.3988 | 0.0261 |

Interpretation :

- le score moyen en validation croisee reste proche du score train/test ;
- l'ecart type montre une variabilite moderee selon les decoupages ;
- le modele est exploitable comme prototype, mais les performances restent
  modestes et devront etre surveillees en production.

## 7. Diagnostic du modele retenu

Matrice de confusion :

| Classe reelle \\ Classe predite | `predit_insatisfait_1_2` | `predit_neutre_3` | `predit_satisfait_4_5` |
| --- | ---: | ---: | ---: |
| `reel_insatisfait_1_2` | 75 | 24 | 33 |
| `reel_neutre_3` | 32 | 15 | 21 |
| `reel_satisfait_4_5` | 32 | 18 | 33 |

Lecture :

- la diagonale correspond aux bonnes predictions ;
- les erreurs se concentrent surtout entre les classes voisines ;
- la classe `neutre_3` est la plus difficile a distinguer.

Rapport de classification :

| Classe | Precision | Recall | F1-score | Support |
| --- | ---: | ---: | ---: | ---: |
| `insatisfait_1_2` | 0.5396 | 0.5682 | 0.5535 | 132 |
| `neutre_3` | 0.2632 | 0.2206 | 0.2400 | 68 |
| `satisfait_4_5` | 0.3793 | 0.3976 | 0.3882 | 83 |
| `macro avg` | 0.3940 | 0.3955 | 0.3939 | 283 |

Interpretation :

- la classe `insatisfait_1_2` est la mieux identifiee ;
- la classe `neutre_3` reste difficile a predire ;
- les classes voisines restent confondues, ce qui confirme que la satisfaction
  est un signal partiellement ambigu.

## 8. Decision finale

Le projet conserve deux lectures :

| Axe | Decision |
| --- | --- |
| Pre-voyage | utile pour le cadrage metier, mais non performant avec les donnees actuelles |
| Post-voyage | meilleure piste pour expliquer la satisfaction et piloter l'amelioration continue |

Le modele a preparer pour l'etape suivante est :

```text
ExtraTrees_3_classes
```

## 9. Etape suivante recommandee

Pour passer a l'industrialisation :

1. creer un script `train.py` reproductible ;
2. separer les fonctions de nettoyage et feature engineering dans `src/` ou
   `app/` ;
3. exporter le pipeline entraine avec `joblib` ;
4. creer un endpoint FastAPI de prediction post-voyage ;
5. ajouter des tests unitaires sur les transformations ;
6. documenter les limites du modele dans la fiche finale.

## 10. Documents de reference

- `docs/etat_projet.md`
- `docs/objectif_1_dataset.md`
- `docs/experiences_modelisation.md`
- `notebooks/Exam.ipynb`
- `notebooks/objectif_2_post_voyage.ipynb`
- `notebooks/00_notebook_final_pre_post_voyage.ipynb`

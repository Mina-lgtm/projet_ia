# Expérience dataset_final_balanced_hyperopt

Objectif : tester une optimisation des hyperparamètres sur la classification binaire équilibrée.

- Dataset : `data\versions\v2_2_signal_enrichment\dataset_final.csv`
- Rapport : `data\versions\v2_2_signal_enrichment\hyperparameter_optimization_report.json`
- Méthode : `RandomizedSearchCV avec validation croisee stratifiee 5 folds, scoring=f1.`

## Meilleur modèle après optimisation

- Modèle : `LogisticRegression_balanced_optimized`
- F1 : `0.5995`
- ROC AUC : `0.732`
- Balanced accuracy : `0.7057`

## Gains vs meilleur modèle initial

- Gain F1 : `0.0023`
- Gain ROC AUC : `0.0017`
- Gain balanced accuracy : `0.0017`

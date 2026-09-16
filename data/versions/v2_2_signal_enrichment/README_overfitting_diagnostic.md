# Diagnostic overfitting - dataset_final_balanced_hyperopt

- Dataset : `data\versions\v2_2_signal_enrichment\dataset_final.csv`
- Rapport : `data\versions\v2_2_signal_enrichment\overfitting_diagnostic_report.json`
- Modèle : `LogisticRegression_balanced_optimized`

## Résultats holdout

- F1 train : `0.6231`
- F1 test : `0.5995`
- Écart F1 train-test : `0.0236`
- ROC AUC train : `0.7822`
- ROC AUC test : `0.732`

## Conclusion

Pas de signe fort d overfitting : les performances train et test restent proches.

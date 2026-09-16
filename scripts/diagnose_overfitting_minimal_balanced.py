from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))
from app.modeling import RANDOM_STATE, build_preprocessor, prepare_training_dataset

DATASET_PATH = Path('data/versions/v2_2_signal_enrichment/travel_planning_dataset_v2_2_minimal.csv')
REPORT_PATH = Path('data/versions/v2_2_signal_enrichment/overfitting_diagnostic_report.json')
README_PATH = Path('data/versions/v2_2_signal_enrichment/README_overfitting_diagnostic.md')

# Best params from hyperparameter_optimization_report.json
model = LogisticRegression(
    C=0.1653693718282443,
    penalty='l2',
    solver='lbfgs',
    max_iter=2000,
    class_weight='balanced',
    random_state=RANDOM_STATE,
)

df = pd.read_csv(DATASET_PATH)
X, y_score, _ = prepare_training_dataset(df)
y = (y_score >= 4).astype(int)
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=RANDOM_STATE,
    stratify=y,
)
preprocess, _, _ = build_preprocessor(X_train)
pipeline = Pipeline([
    ('preprocess', preprocess),
    ('model', model),
])
pipeline.fit(X_train, y_train)


def compute_metrics(split_name, x_values, y_values):
    predictions = pipeline.predict(x_values)
    probabilities = pipeline.predict_proba(x_values)[:, 1]
    return {
        'jeu': split_name,
        'accuracy': round(float(accuracy_score(y_values, predictions)), 4),
        'balanced_accuracy': round(float(balanced_accuracy_score(y_values, predictions)), 4),
        'precision_1': round(float(precision_score(y_values, predictions, zero_division=0)), 4),
        'recall_1': round(float(recall_score(y_values, predictions, zero_division=0)), 4),
        'f1_1': round(float(f1_score(y_values, predictions, zero_division=0)), 4),
        'roc_auc': round(float(roc_auc_score(y_values, probabilities)), 4),
    }

train_metrics = compute_metrics('train', X_train, y_train)
test_metrics = compute_metrics('test', X_test, y_test)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
cv_pipeline = Pipeline([
    ('preprocess', build_preprocessor(X)[0]),
    ('model', model),
])
cv_results = cross_validate(
    cv_pipeline,
    X,
    y,
    cv=cv,
    scoring=['f1', 'balanced_accuracy', 'roc_auc', 'accuracy'],
    n_jobs=-1,
    return_train_score=True,
)
cv_summary = {}
for key, values in cv_results.items():
    if key.startswith('train_') or key.startswith('test_'):
        cv_summary[key] = {
            'mean': round(float(np.mean(values)), 4),
            'std': round(float(np.std(values)), 4),
        }

gaps = {
    'f1_train_test_gap': round(float(train_metrics['f1_1'] - test_metrics['f1_1']), 4),
    'balanced_accuracy_train_test_gap': round(float(train_metrics['balanced_accuracy'] - test_metrics['balanced_accuracy']), 4),
    'roc_auc_train_test_gap': round(float(train_metrics['roc_auc'] - test_metrics['roc_auc']), 4),
    'cv_f1_train_test_gap': round(float(cv_summary['train_f1']['mean'] - cv_summary['test_f1']['mean']), 4),
    'cv_balanced_accuracy_train_test_gap': round(float(cv_summary['train_balanced_accuracy']['mean'] - cv_summary['test_balanced_accuracy']['mean']), 4),
    'cv_roc_auc_train_test_gap': round(float(cv_summary['train_roc_auc']['mean'] - cv_summary['test_roc_auc']['mean']), 4),
}

if gaps['f1_train_test_gap'] > 0.10 or gaps['cv_f1_train_test_gap'] > 0.10:
    conclusion = 'Risque d overfitting significatif : ecart F1 train/test superieur a 0.10.'
elif gaps['f1_train_test_gap'] > 0.05 or gaps['cv_f1_train_test_gap'] > 0.05:
    conclusion = 'Risque d overfitting modere : ecart F1 train/test entre 0.05 et 0.10.'
else:
    conclusion = 'Pas de signe fort d overfitting : les performances train et test restent proches.'

report = {
    'created_at_utc': datetime.now(timezone.utc).isoformat(),
    'experiment_version': 'v2.2-minimal_balanced_hyperopt_overfitting_diagnostic',
    'dataset': str(DATASET_PATH).replace('\\', '/'),
    'rows': int(df.shape[0]),
    'columns': int(df.shape[1]),
    'model': 'LogisticRegression_balanced_optimized',
    'hyperparameters': {
        'C': 0.1653693718282443,
        'penalty': 'l2',
        'solver': 'lbfgs',
        'class_weight': 'balanced',
        'max_iter': 2000,
    },
    'holdout_metrics': [train_metrics, test_metrics],
    'cross_validation_summary': cv_summary,
    'gaps': gaps,
    'conclusion': conclusion,
}
REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

readme_lines = [
    '# Diagnostic overfitting - v2.2-minimal_balanced_hyperopt',
    '',
    f'- Dataset : `{DATASET_PATH}`',
    f'- Rapport : `{REPORT_PATH}`',
    '- Modèle : `LogisticRegression_balanced_optimized`',
    '',
    '## Résultats holdout',
    '',
    f"- F1 train : `{train_metrics['f1_1']}`",
    f"- F1 test : `{test_metrics['f1_1']}`",
    f"- Écart F1 train-test : `{gaps['f1_train_test_gap']}`",
    f"- ROC AUC train : `{train_metrics['roc_auc']}`",
    f"- ROC AUC test : `{test_metrics['roc_auc']}`",
    '',
    '## Conclusion',
    '',
    conclusion,
    '',
]
README_PATH.write_text('\n'.join(readme_lines), encoding='utf-8')

manifest_path = Path('data/versions/manifest.json')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
entry = {
    'version': 'v2.2-minimal_balanced_hyperopt_overfitting',
    'label': 'diagnostic overfitting du modele optimise',
    'source_version': 'v2.2-minimal_balanced_hyperopt',
    'status': 'experiment',
    'path': str(DATASET_PATH).replace('\\', '/'),
    'transformations': [
        'aucune modification du dataset',
        'comparaison des metriques train/test',
        'validation croisee stratifiee 5 folds avec train_score',
    ],
    'rows': int(df.shape[0]),
    'columns': int(df.shape[1]),
    'sha256': hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
    'size_bytes': DATASET_PATH.stat().st_size,
    'report': str(REPORT_PATH).replace('\\', '/'),
}
manifest['versions'] = [v for v in manifest.get('versions', []) if v.get('version') != 'v2.2-minimal_balanced_hyperopt_overfitting'] + [entry]
manifest['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print('HOLDOUT')
print(pd.DataFrame([train_metrics, test_metrics]).to_string(index=False))
print('\nCV SUMMARY')
print(json.dumps(cv_summary, ensure_ascii=False, indent=2))
print('\nGAPS')
print(json.dumps(gaps, ensure_ascii=False, indent=2))
print('\nCONCLUSION')
print(conclusion)

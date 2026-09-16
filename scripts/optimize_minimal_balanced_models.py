from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
import sys

import numpy as np
import pandas as pd
from scipy.stats import randint, loguniform
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))
from app.modeling import RANDOM_STATE, build_preprocessor, prepare_training_dataset

DATASET_PATH = Path('data/versions/v2_2_signal_enrichment/travel_planning_dataset_v2_2_minimal.csv')
OUTPUT_REPORT = Path('data/versions/v2_2_signal_enrichment/hyperparameter_optimization_report.json')
OUTPUT_README = Path('data/versions/v2_2_signal_enrichment/README_hyperparameter_optimization.md')

SCORING = 'f1'
CV_SPLITS = 5
N_ITER_LOGREG = 25
N_ITER_RF = 30


def metrics_row(model_name, pipeline, x_test, y_test, extra=None):
    predictions = pipeline.predict(x_test)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    cm = confusion_matrix(y_test, predictions, labels=[0, 1])
    row = {
        'modele': model_name,
        'accuracy': round(float(accuracy_score(y_test, predictions)), 4),
        'balanced_accuracy': round(float(balanced_accuracy_score(y_test, predictions)), 4),
        'precision_1': round(float(precision_score(y_test, predictions, zero_division=0)), 4),
        'recall_1': round(float(recall_score(y_test, predictions, zero_division=0)), 4),
        'f1_1': round(float(f1_score(y_test, predictions, zero_division=0)), 4),
        'roc_auc': round(float(roc_auc_score(y_test, probabilities)), 4),
        'confusion_matrix': {
            'tn': int(cm[0, 0]),
            'fp': int(cm[0, 1]),
            'fn': int(cm[1, 0]),
            'tp': int(cm[1, 1]),
        },
    }
    if extra:
        row.update(extra)
    return row


def main():
    df = pd.read_csv(DATASET_PATH)
    x, y_score, _ = prepare_training_dataset(df)
    y = (y_score >= 4).astype(int)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    preprocess, _, _ = build_preprocessor(x_train)
    cv = StratifiedKFold(n_splits=CV_SPLITS, shuffle=True, random_state=RANDOM_STATE)

    baseline_models = {
        'Dummy_majority_binary': DummyClassifier(strategy='most_frequent'),
        'LogisticRegression_balanced_initial': LogisticRegression(
            max_iter=1000,
            class_weight='balanced',
            random_state=RANDOM_STATE,
        ),
        'RandomForest_balanced_initial': RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=8,
            class_weight='balanced',
            random_state=RANDOM_STATE,
            n_jobs=1,
        ),
    }

    initial_results = []
    for model_name, model in baseline_models.items():
        pipeline = Pipeline([
            ('preprocess', clone(preprocess)),
            ('model', model),
        ])
        pipeline.fit(x_train, y_train)
        initial_results.append(metrics_row(model_name, pipeline, x_test, y_test))

    logreg_pipeline = Pipeline([
        ('preprocess', clone(preprocess)),
        ('model', LogisticRegression(max_iter=2000, class_weight='balanced', random_state=RANDOM_STATE)),
    ])
    logreg_param_distributions = [
        {
            'model__solver': ['liblinear'],
            'model__penalty': ['l1', 'l2'],
            'model__C': loguniform(0.01, 100),
        },
        {
            'model__solver': ['lbfgs'],
            'model__penalty': ['l2'],
            'model__C': loguniform(0.01, 100),
        },
        {
            'model__solver': ['saga'],
            'model__penalty': ['l1', 'l2'],
            'model__C': loguniform(0.01, 100),
        },
    ]
    logreg_search = RandomizedSearchCV(
        estimator=logreg_pipeline,
        param_distributions=logreg_param_distributions,
        n_iter=N_ITER_LOGREG,
        scoring=SCORING,
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        refit=True,
        error_score='raise',
    )
    logreg_search.fit(x_train, y_train)

    rf_pipeline = Pipeline([
        ('preprocess', clone(preprocess)),
        ('model', RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=1)),
    ])
    rf_param_distributions = {
        'model__n_estimators': [100, 200, 300, 500],
        'model__max_depth': [3, 5, 8, 10, 12, None],
        'model__min_samples_leaf': randint(2, 21),
        'model__min_samples_split': randint(2, 31),
        'model__max_features': ['sqrt', 'log2', None],
        'model__class_weight': ['balanced', 'balanced_subsample'],
    }
    rf_search = RandomizedSearchCV(
        estimator=rf_pipeline,
        param_distributions=rf_param_distributions,
        n_iter=N_ITER_RF,
        scoring=SCORING,
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        refit=True,
        error_score='raise',
    )
    rf_search.fit(x_train, y_train)

    optimized_results = [
        metrics_row(
            'LogisticRegression_balanced_optimized',
            logreg_search.best_estimator_,
            x_test,
            y_test,
            {
                'cv_best_f1': round(float(logreg_search.best_score_), 4),
                'best_params': logreg_search.best_params_,
            },
        ),
        metrics_row(
            'RandomForest_balanced_optimized',
            rf_search.best_estimator_,
            x_test,
            y_test,
            {
                'cv_best_f1': round(float(rf_search.best_score_), 4),
                'best_params': rf_search.best_params_,
            },
        ),
    ]

    all_results = (
        pd.DataFrame(initial_results + optimized_results)
        .sort_values(['f1_1', 'roc_auc'], ascending=[False, False])
        .reset_index(drop=True)
    )
    best_initial = (
        pd.DataFrame(initial_results)
        .sort_values(['f1_1', 'roc_auc'], ascending=[False, False])
        .iloc[0]
        .to_dict()
    )
    best_optimized = all_results.iloc[0].to_dict()

    report = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'experiment_version': 'v2.2-minimal_balanced_hyperopt',
        'dataset': str(DATASET_PATH).replace('\\', '/'),
        'rows': int(df.shape[0]),
        'columns': int(df.shape[1]),
        'target': 'satisfaction_binaire_4_5',
        'target_definition': '0 = satisfaction 1, 2 ou 3 ; 1 = satisfaction 4 ou 5',
        'method': 'RandomizedSearchCV avec validation croisee stratifiee 5 folds, scoring=f1.',
        'search_space': {
            'LogisticRegression': {
                'C': 'loguniform(0.01, 100)',
                'penalty': ['l1', 'l2'],
                'solver': ['liblinear', 'lbfgs', 'saga'],
                'class_weight': 'balanced',
                'n_iter': N_ITER_LOGREG,
            },
            'RandomForest': {
                'n_estimators': [100, 200, 300, 500],
                'max_depth': [3, 5, 8, 10, 12, None],
                'min_samples_leaf': 'randint(2, 21)',
                'min_samples_split': 'randint(2, 31)',
                'max_features': ['sqrt', 'log2', None],
                'class_weight': ['balanced', 'balanced_subsample'],
                'n_iter': N_ITER_RF,
            },
        },
        'initial_results': initial_results,
        'optimized_results': optimized_results,
        'all_results_sorted': all_results.to_dict(orient='records'),
        'best_initial_model': best_initial,
        'best_model_after_optimization': best_optimized,
        'gains_vs_best_initial': {
            'f1_gain': round(float(best_optimized['f1_1'] - best_initial['f1_1']), 4),
            'roc_auc_gain': round(float(best_optimized['roc_auc'] - best_initial['roc_auc']), 4),
            'balanced_accuracy_gain': round(float(best_optimized['balanced_accuracy'] - best_initial['balanced_accuracy']), 4),
        },
        'interpretation': (
            'L optimisation teste plusieurs hyperparametres tout en gardant le pretraitement dans un pipeline. '
            'Le modele optimise est retenu uniquement si le gain sur F1 et balanced accuracy est significatif et coherent.'
        ),
    }
    OUTPUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    readme_lines = [
        '# Expérience v2.2-minimal_balanced_hyperopt',
        '',
        'Objectif : tester une optimisation des hyperparamètres sur la classification binaire équilibrée.',
        '',
        f'- Dataset : `{DATASET_PATH}`',
        f'- Rapport : `{OUTPUT_REPORT}`',
        f'- Méthode : `{report["method"]}`',
        '',
        '## Meilleur modèle après optimisation',
        '',
        f"- Modèle : `{best_optimized['modele']}`",
        f"- F1 : `{best_optimized['f1_1']}`",
        f"- ROC AUC : `{best_optimized['roc_auc']}`",
        f"- Balanced accuracy : `{best_optimized['balanced_accuracy']}`",
        '',
        '## Gains vs meilleur modèle initial',
        '',
        f"- Gain F1 : `{report['gains_vs_best_initial']['f1_gain']}`",
        f"- Gain ROC AUC : `{report['gains_vs_best_initial']['roc_auc_gain']}`",
        f"- Gain balanced accuracy : `{report['gains_vs_best_initial']['balanced_accuracy_gain']}`",
        '',
    ]
    OUTPUT_README.write_text('\n'.join(readme_lines), encoding='utf-8')

    manifest_path = Path('data/versions/manifest.json')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    entry = {
        'version': 'v2.2-minimal_balanced_hyperopt',
        'label': 'optimisation hyperparametres classification binaire equilibree',
        'source_version': 'v2.2-minimal_balanced',
        'status': 'experiment',
        'path': str(DATASET_PATH).replace('\\', '/'),
        'transformations': [
            'aucune modification du dataset',
            'RandomizedSearchCV sur LogisticRegression',
            'RandomizedSearchCV sur RandomForest',
            'validation croisee stratifiee 5 folds avec scoring f1',
        ],
        'rows': int(df.shape[0]),
        'columns': int(df.shape[1]),
        'sha256': hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
        'size_bytes': DATASET_PATH.stat().st_size,
        'report': str(OUTPUT_REPORT).replace('\\', '/'),
    }
    manifest['versions'] = [v for v in manifest.get('versions', []) if v.get('version') != 'v2.2-minimal_balanced_hyperopt'] + [entry]
    manifest['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print('RESULTATS INITIAUX')
    print(pd.DataFrame(initial_results).sort_values(['f1_1', 'roc_auc'], ascending=[False, False]).to_string(index=False))
    print('\nRESULTATS OPTIMISES')
    print(pd.DataFrame(optimized_results).sort_values(['f1_1', 'roc_auc'], ascending=[False, False]).to_string(index=False))
    print('\nTOUS RESULTATS')
    print(all_results.drop(columns=['confusion_matrix', 'best_params'], errors='ignore').to_string(index=False))
    print('\nGAINS')
    print(json.dumps(report['gains_vs_best_initial'], ensure_ascii=False, indent=2))
    print('\nBEST PARAMS LOGREG')
    print(json.dumps(logreg_search.best_params_, ensure_ascii=False, indent=2, default=str))
    print('\nBEST PARAMS RF')
    print(json.dumps(rf_search.best_params_, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()

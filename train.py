from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from app.modeling import (
    prepare_training_dataset,
    save_training_artifacts,
    train_and_select_model,
)


DEFAULT_DATA_PATH = Path("data/versions/v2_2_signal_enrichment/dataset_final.csv")
DEFAULT_MODEL_PATH = Path("models/model_pre_voyage.pkl")
DEFAULT_METADATA_PATH = Path("models/model_pre_voyage_metadata.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Entraine et exporte le modele TravelMind LogisticRegression binaire.",
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"Chemin du dataset CSV. Defaut: {DEFAULT_DATA_PATH}",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Chemin de sortie du modele. Defaut: {DEFAULT_MODEL_PATH}",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help=f"Chemin de sortie des metadonnees. Defaut: {DEFAULT_METADATA_PATH}",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Part du dataset utilisee pour le test stratifie.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    df_raw = pd.read_csv(args.data_path)
    x, y, cleaning_report = prepare_training_dataset(df_raw)
    result = train_and_select_model(
        x=x,
        y=y,
        cleaning_report=cleaning_report,
        test_size=args.test_size,
    )
    save_training_artifacts(
        result=result,
        model_path=args.model_path,
        metadata_path=args.metadata_path,
    )

    print("Entrainement classification binaire TravelMind termine")
    print(f"Dataset : {args.data_path}")
    print(f"Modele retenu : {result.model_name}")
    print(f"Accuracy : {result.metrics['accuracy']:.4f}")
    print(f"Balanced accuracy : {result.metrics['balanced_accuracy']:.4f}")
    print(f"Macro F1 : {result.metrics['macro_f1']:.4f}")
    print(f"Recall satisfait : {result.metrics['recall_satisfait']:.4f}")
    print(f"ROC AUC : {result.metrics.get('roc_auc', float('nan')):.4f}")
    print(f"Modele exporte : {args.model_path}")
    print(f"Metadonnees exportees : {args.metadata_path}")


if __name__ == "__main__":
    main()

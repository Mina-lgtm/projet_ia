from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from app.modeling import (
    prepare_training_dataset,
    save_training_artifacts,
    train_and_select_model,
)


DEFAULT_DATA_PATH = Path("data/Examen_travel_planning_dataset.csv")
DEFAULT_MODEL_PATH = Path("models/model_pre_voyage.pkl")
DEFAULT_METADATA_PATH = Path("models/model_pre_voyage_metadata.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Entraîne et exporte le modèle pré-voyage industrialisable.",
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"Chemin du dataset CSV. Défaut: {DEFAULT_DATA_PATH}",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Chemin de sortie du modèle. Défaut: {DEFAULT_MODEL_PATH}",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help=f"Chemin de sortie des métadonnées. Défaut: {DEFAULT_METADATA_PATH}",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Part du dataset utilisée pour le test stratifié.",
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

    print("Entraînement pré-voyage terminé")
    print(f"Modèle retenu : {result.model_name}")
    print(f"macro_f1 : {result.metrics['macro_f1']:.4f}")
    print(f"balanced_accuracy : {result.metrics['balanced_accuracy']:.4f}")
    print(f"accuracy : {result.metrics['accuracy']:.4f}")
    print(f"Modèle exporté : {args.model_path}")
    print(f"Métadonnées exportées : {args.metadata_path}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.modeling import add_base_features, clean_dataset


SOURCE_DATASET = PROJECT_ROOT / "data" / "Examen_travel_planning_dataset.csv"
VERSIONS_DIR = PROJECT_ROOT / "data" / "versions"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def clean_columns_spaces_formats(df_source: pd.DataFrame) -> pd.DataFrame:
    df = df_source.copy()
    df.columns = [str(column).strip().lower() for column in df.columns]

    for column in df.select_dtypes(include=["object", "string"]).columns:
        cleaned_column = (
            df[column]
            .astype("string")
            .str.strip()
            .str.lower()
            .replace({"": np.nan, "nan": np.nan})
        )
        df[column] = cleaned_column.mask(cleaned_column.isna(), np.nan).astype(object)

    numeric_columns = [
        "trip_id",
        "budget_total",
        "duree_jours",
        "prix_vol",
        "satisfaction_client",
        "reorganisation_necessaire",
        "respect_budget",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def dataset_entry(
    *,
    version: str,
    label: str,
    path: Path | None,
    source_version: str | None,
    transformations: list[str],
    status: str,
    dataframe: pd.DataFrame | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "version": version,
        "label": label,
        "source_version": source_version,
        "status": status,
        "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/") if path else None,
        "transformations": transformations,
    }

    if dataframe is not None:
        entry.update({
            "rows": int(dataframe.shape[0]),
            "columns": int(dataframe.shape[1]),
            "column_names": dataframe.columns.tolist(),
        })

    if path is not None and path.exists() and path.is_file():
        entry["sha256"] = sha256_file(path)
        entry["size_bytes"] = path.stat().st_size

    return entry


def main() -> None:
    if not SOURCE_DATASET.exists():
        raise FileNotFoundError(f"Dataset source introuvable: {SOURCE_DATASET}")

    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = pd.read_csv(SOURCE_DATASET)

    v10_path = VERSIONS_DIR / "v1_0_raw" / "travel_planning_dataset_v1_0.csv"
    v10_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_DATASET, v10_path)

    v11_df = clean_columns_spaces_formats(raw_df)
    v11_path = VERSIONS_DIR / "v1_1_cleaning" / "travel_planning_dataset_v1_1.csv"
    write_csv(v11_df, v11_path)

    v12_df, cleaning_report = clean_dataset(raw_df)
    v12_path = VERSIONS_DIR / "v1_2_incoherences" / "travel_planning_dataset_v1_2.csv"
    write_csv(v12_df, v12_path)

    v20_df = add_base_features(v12_df)
    v20_path = VERSIONS_DIR / "v2_0_feature_engineering" / "travel_planning_dataset_v2_0.csv"
    write_csv(v20_df, v20_path)

    v21_dir = VERSIONS_DIR / "v2_1_enrichment"
    v21_dir.mkdir(parents=True, exist_ok=True)
    v21_readme = v21_dir / "README.md"
    v21_readme.write_text(
        "# v2.1 - Enrichissement eventuel\n\n"
        "Cette version est reservee aux enrichissements futurs : API meteo, donnees tarifaires, "
        "duree de vol, avis clients complementaires ou nouvelles donnees metier.\n\n"
        "Aucun fichier CSV v2.1 n'est genere tant qu'une source d'enrichissement validee "
        "n'est pas disponible.\n",
        encoding="utf-8",
    )

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset": str(SOURCE_DATASET.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "versioning_strategy": "Git pour le dataset leger ; DVC/LakeFS recommandes si les donnees deviennent lourdes ou multi-sources.",
        "cleaning_report_v1_2": cleaning_report,
        "versions": [
            dataset_entry(
                version="v1.0",
                label="dataset brut fourni",
                path=v10_path,
                source_version=None,
                transformations=["copie conforme du fichier fourni"],
                status="created",
                dataframe=raw_df,
            ),
            dataset_entry(
                version="v1.1",
                label="nettoyage des colonnes, espaces et formats",
                path=v11_path,
                source_version="v1.0",
                transformations=[
                    "normalisation des noms de colonnes",
                    "suppression des espaces en debut et fin de chaine",
                    "passage des valeurs texte en minuscules",
                    "conversion des colonnes numeriques attendues",
                    "conversion des chaines vides en valeurs manquantes",
                ],
                status="created",
                dataframe=v11_df,
            ),
            dataset_entry(
                version="v1.2",
                label="suppression des incoherences critiques",
                path=v12_path,
                source_version="v1.1",
                transformations=[
                    "suppression des lignes sans cible satisfaction_client valide entre 1 et 5",
                    "suppression des cas prix_vol > budget_total",
                    "suppression des cas reorganisation_necessaire = 1 avec imprevus = aucun",
                    "remplissage de imprevus manquant par aucun",
                    "remplissage de retour_client manquant par chaine vide",
                ],
                status="created",
                dataframe=v12_df,
            ),
            dataset_entry(
                version="v2.0",
                label="feature engineering",
                path=v20_path,
                source_version="v1.2",
                transformations=[
                    "creation des ratios budget_par_jour et part_vol_budget",
                    "creation des indicateurs sejour_long, meteo_risque, client_business et hebergement_luxe",
                    "enrichissement interne destination : region_destination, distance_vol_categorie, destination_luxe",
                    "creation des indicateurs post-voyage explicatifs pour analyse qualite",
                ],
                status="created",
                dataframe=v20_df,
            ),
            dataset_entry(
                version="v2.1",
                label="enrichissement eventuel ou nouvelles donnees",
                path=v21_readme,
                source_version="v2.0",
                transformations=[
                    "version reservee aux enrichissements futurs valides par le metier",
                    "aucune source externe ajoutee a ce stade",
                ],
                status="reserved",
                dataframe=None,
            ),
        ],
    }

    manifest_path = VERSIONS_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    readme_path = VERSIONS_DIR / "README.md"
    readme_path.write_text(
        "# Versioning des donnees\n\n"
        "Ce dossier contient les versions successives du dataset utilisees dans le projet IA.\n\n"
        "| Version | Role | Fichier |\n"
        "| --- | --- | --- |\n"
        "| v1.0 | Dataset brut fourni | `v1_0_raw/travel_planning_dataset_v1_0.csv` |\n"
        "| v1.1 | Nettoyage colonnes, espaces et formats | `v1_1_cleaning/travel_planning_dataset_v1_1.csv` |\n"
        "| v1.2 | Suppression des incoherences critiques | `v1_2_incoherences/travel_planning_dataset_v1_2.csv` |\n"
        "| v2.0 | Feature engineering | `v2_0_feature_engineering/travel_planning_dataset_v2_0.csv` |\n"
        "| v2.1 | Enrichissement eventuel | `v2_1_enrichment/README.md` |\n\n"
        "Le fichier `manifest.json` contient les metadonnees, les transformations et les empreintes SHA-256.\n\n"
        "Pour regenerer les versions :\n\n"
        "```bash\n"
        "python scripts/version_data.py\n"
        "```\n",
        encoding="utf-8",
    )

    print(f"Versions generees dans: {VERSIONS_DIR.relative_to(PROJECT_ROOT)}")
    print(f"Manifest: {manifest_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

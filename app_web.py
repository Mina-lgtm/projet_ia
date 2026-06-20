from __future__ import annotations

import json
from io import StringIO
from typing import Any

import httpx
import pandas as pd
import streamlit as st


DEFAULT_API_URL = "http://localhost:8001"
REQUIRED_COLUMNS = [
    "client_type",
    "budget_total",
    "destination",
    "saison",
    "duree_jours",
    "type_hebergement",
    "prix_vol",
    "meteo_prevue",
    "activite_principale",
]


def call_api(
    method: str,
    endpoint: str,
    api_url: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{api_url.rstrip('/')}{endpoint}"
    with httpx.Client(timeout=15.0) as client:
        if method == "GET":
            response = client.get(url)
        else:
            response = client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def display_api_error(error: Exception) -> None:
    if isinstance(error, httpx.ConnectError):
        st.error("API indisponible. Lance d'abord : `uvicorn app.main:app --reload --port 8001`.")
        return
    if isinstance(error, httpx.HTTPStatusError):
        try:
            detail = error.response.json()
        except json.JSONDecodeError:
            detail = error.response.text
        st.error(f"Erreur API {error.response.status_code}")
        st.json(detail)
        return
    st.error(str(error))


def build_manual_payload() -> dict[str, Any]:
    col_left, col_right = st.columns(2)

    with col_left:
        client_type = st.selectbox(
            "Type de client",
            ["couple", "famille", "solo", "business", "senior"],
        )
        destination = st.selectbox(
            "Destination",
            ["rome", "paris", "lisbonne", "new york", "dubaï", "tokyo", "bali", "sydney"],
        )
        saison = st.selectbox(
            "Saison",
            ["printemps", "été", "automne", "hiver"],
        )
        duree_jours = st.number_input(
            "Durée du séjour (jours)",
            min_value=1,
            max_value=365,
            value=7,
            step=1,
        )
        meteo_prevue = st.selectbox(
            "Météo prévue",
            ["ensoleillé", "nuageux", "pluie", "variable"],
        )

    with col_right:
        budget_total = st.number_input(
            "Budget total (€)",
            min_value=1.0,
            value=4200.0,
            step=100.0,
        )
        prix_vol = st.number_input(
            "Prix du vol (€)",
            min_value=0.0,
            value=650.0,
            step=50.0,
        )
        type_hebergement = st.selectbox(
            "Type d'hébergement",
            ["hôtel", "resort", "appartement", "villa"],
        )
        activite_principale = st.selectbox(
            "Activité principale",
            ["culture", "plage", "gastronomie", "randonnée", "business"],
        )

    return {
        "client_type": client_type,
        "budget_total": float(budget_total),
        "destination": destination,
        "saison": saison,
        "duree_jours": int(duree_jours),
        "type_hebergement": type_hebergement,
        "prix_vol": float(prix_vol),
        "meteo_prevue": meteo_prevue,
        "activite_principale": activite_principale,
    }


def display_prediction(result: dict[str, Any]) -> None:
    st.subheader("Résultat de prédiction")
    st.metric("Classe prédite", result.get("libelle_prediction", "inconnu"))
    st.write(f"Modèle utilisé : `{result.get('model_name', 'inconnu')}`")

    probabilities = result.get("probabilities") or []
    if probabilities:
        proba_df = pd.DataFrame(probabilities)
        st.bar_chart(
            proba_df.set_index("libelle")["probabilite"],
            use_container_width=True,
        )
        st.dataframe(proba_df, use_container_width=True)

    metrics = result.get("model_metrics") or {}
    if metrics:
        st.subheader("Métriques globales du modèle")
        st.dataframe(
            pd.DataFrame([metrics]).round(4),
            use_container_width=True,
        )


def render_manual_prediction(api_url: str) -> None:
    st.header("Tester un voyage")
    payload = build_manual_payload()

    if st.button("Prédire la satisfaction", type="primary"):
        try:
            result = call_api("POST", "/predict", api_url, payload)
        except Exception as error:
            display_api_error(error)
        else:
            display_prediction(result)


def render_csv_prediction(api_url: str) -> None:
    st.header("Tester plusieurs voyages par CSV")
    st.write("Le fichier CSV doit contenir les colonnes suivantes :")
    st.code(", ".join(REQUIRED_COLUMNS))

    uploaded_file = st.file_uploader("Charger un CSV de voyages", type=["csv"])
    if uploaded_file is None:
        return

    df = pd.read_csv(uploaded_file)
    st.subheader("Aperçu du fichier")
    st.dataframe(df.head(10), use_container_width=True)

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        st.error(f"Colonnes manquantes : {missing_columns}")
        return

    if st.button("Lancer les prédictions du CSV", type="primary"):
        rows = []
        errors = []
        progress = st.progress(0)

        for index, row in df.iterrows():
            payload = {column: row[column] for column in REQUIRED_COLUMNS}
            try:
                result = call_api("POST", "/predict", api_url, payload)
            except Exception as error:
                errors.append({"ligne": int(index), "erreur": str(error)})
            else:
                rows.append({
                    "ligne": int(index),
                    **payload,
                    "classe_predite": result.get("classe_predite"),
                    "libelle_prediction": result.get("libelle_prediction"),
                    "confidence": max(
                        [
                            probability.get("probabilite", 0)
                            for probability in result.get("probabilities", [])
                        ],
                        default=None,
                    ),
                })
            progress.progress((index + 1) / len(df))

        if rows:
            result_df = pd.DataFrame(rows)
            st.subheader("Résultats")
            st.dataframe(result_df, use_container_width=True)
            csv_buffer = StringIO()
            result_df.to_csv(csv_buffer, index=False)
            st.download_button(
                "Télécharger les résultats CSV",
                data=csv_buffer.getvalue(),
                file_name="predictions_voyages.csv",
                mime="text/csv",
            )

        if errors:
            st.warning("Certaines lignes n'ont pas pu être prédites.")
            st.dataframe(pd.DataFrame(errors), use_container_width=True)


def render_monitoring(api_url: str) -> None:
    st.header("Monitoring")
    endpoint = st.selectbox(
        "Vue monitoring",
        [
            "/monitoring/summary",
            "/monitoring/drift",
            "/monitoring/alerts",
        ],
    )

    if st.button("Actualiser le monitoring"):
        try:
            result = call_api("GET", endpoint, api_url)
        except Exception as error:
            display_api_error(error)
        else:
            st.json(result)


def render_api_status(api_url: str) -> None:
    try:
        health = call_api("GET", "/health", api_url)
    except Exception:
        st.sidebar.error("API indisponible")
        st.sidebar.write("Commande :")
        st.sidebar.code("uvicorn app.main:app --reload --port 8001")
    else:
        st.sidebar.success(f"API disponible : {health}")


def main() -> None:
    st.set_page_config(
        page_title="Projet IA Voyages",
        page_icon="✈️",
        layout="wide",
    )

    st.title("Interface de test — modèle pré-voyage")
    st.write(
        "Cette interface permet de tester l'API FastAPI, de saisir un voyage, "
        "d'importer un CSV et de consulter le monitoring."
    )

    api_url = st.sidebar.text_input("URL de l'API FastAPI", value=DEFAULT_API_URL)
    render_api_status(api_url)

    tab_manual, tab_csv, tab_monitoring = st.tabs(
        ["Prédiction unitaire", "Prédiction CSV", "Monitoring"],
    )

    with tab_manual:
        render_manual_prediction(api_url)

    with tab_csv:
        render_csv_prediction(api_url)

    with tab_monitoring:
        render_monitoring(api_url)


if __name__ == "__main__":
    main()

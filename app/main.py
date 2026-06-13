from fastapi import FastAPI


app = FastAPI(
    title="Examen IA API",
    description="API minimale conservee pendant la finalisation du notebook.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

from __future__ import annotations

from fastapi import FastAPI

from pydantic import BaseModel, Field

from src.ml.predict import load_risk_model, predict_convoy_risk_proba



app = FastAPI(
    title="Digital Twin Logistico – API Rischio Convoglio",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict:
    """Endpoint di health-check semplice."""
    return {"status": "ok"}

class PredictRequest(BaseModel):
    """Schema della richiesta per /predict_risk."""

    total_minutes: int = Field(120, gt=0, description="Durata totale simulazione (minuti)")
    timestep_minutes: int = Field(10, gt=0, description="Durata di ogni passo (minuti)")
    n_convoys: int = Field(5, gt=0, description="Numero di convogli da valutare")


class ConvoyRisk(BaseModel):
    """Rappresenta il rischio stimato per un singolo convoglio."""

    convoy_id: int
    risk_proba: float


class PredictResponse(BaseModel):
    """Schema della risposta per /predict_risk."""

    total_minutes: int
    timestep_minutes: int
    n_convoys: int
    results: list[ConvoyRisk]


@app.post("/predict_risk", response_model=PredictResponse)
def predict_risk(request: PredictRequest) -> PredictResponse:
    """Calcola la probabilità di rischio per ogni convoglio."""
    # Carichiamo il modello (in una versione più avanzata potremmo farlo solo una volta)
    model = load_risk_model("models/risk_model.pkl")

    df_result = predict_convoy_risk_proba(
        model,
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
    )

    results = [
        ConvoyRisk(convoy_id=int(row["convoy_id"]), risk_proba=float(row["risk_proba"]))
        for _, row in df_result.iterrows()
    ]

    response = PredictResponse(
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        results=results,
    )

    return response
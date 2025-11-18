from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.ml.predict import load_risk_model, predict_convoy_risk_proba
from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk


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
    convoy_id: int
    risk_proba: float
    is_high_risk: bool
class PredictResponse(BaseModel):
    total_minutes: int
    timestep_minutes: int
    n_convoys: int
    risk_threshold_used: float
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

    results = []
    for _, row in df_result.iterrows():
        prob = float(row["risk_proba"])
        results.append(
            ConvoyRisk(
                convoy_id=int(row["convoy_id"]),
                risk_proba=prob,
                is_high_risk=is_high_risk(prob),
            )
        )

    response = PredictResponse(
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        risk_threshold_used=RISK_THRESHOLD_DEFAULT,
        results=results,
    )

    return response
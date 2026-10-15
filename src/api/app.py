from __future__ import annotations

from fastapi import FastAPI

from src.api.logistics import router as logistics_router
from pydantic import BaseModel, Field

from src.ml.predict import load_risk_model, predict_convoy_risk_proba
from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk
from src.sim.simulator import run_simulation
from src.sim.metrics import compute_basic_kpis, load_events_csv
from src.sim.config import SimConfig
from src.ml.model_info import get_model_version
from src.api.api_audit import log_predict_call

app = FastAPI(
    title="Digital Twin Logistico – API nativa e prototipo storico",
    version="1.0.0",
)


app.include_router(logistics_router)


@app.get("/health")
def health_check() -> dict:
    """Endpoint di health-check semplice."""
    return {"status": "ok"}


class PredictRequest(BaseModel):
    """Schema della richiesta per /predict (rischio convoglio)."""

    schema_version: str = Field(
        "1.0",
        description=(
            "Versione dello schema di richiesta. Permette di "
            "evolvere l'API in futuro."
        ),
    )
    total_minutes: int = Field(
        120, gt=0, description="Durata totale simulazione (minuti)"
    )
    timestep_minutes: int = Field(10, gt=0, description="Durata di ogni passo (minuti)")
    n_convoys: int = Field(5, gt=0, description="Numero di convogli da valutare")


class ConvoyRisk(BaseModel):
    convoy_id: int
    risk_proba: float
    is_high_risk: bool


class PredictResponse(BaseModel):
    """Schema della risposta per /predict."""

    schema_version: str
    model_version: str | None = None
    total_minutes: int
    timestep_minutes: int
    n_convoys: int
    risk_threshold_used: float
    results: list[ConvoyRisk]


class SimulateRequest(BaseModel):
    """Parametri per eseguire una simulazione singola."""

    schema_version: str = Field(
        "1.0",
        description="Versione dello schema di richiesta per /simulate.",
    )
    total_minutes: int = Field(
        120, gt=0, description="Durata totale simulazione (minuti)"
    )
    timestep_minutes: int = Field(10, gt=0, description="Durata di ogni passo (minuti)")
    n_convoys: int = Field(5, gt=0, description="Numero di convogli simulati")
    depot_capacity: int = Field(2, gt=0, description="Capacità del deposito")
    simulation_name: str = Field("api_run", description="Nome logico della simulazione")


class SimulationKPI(BaseModel):
    """KPI riassuntivi della simulazione."""

    n_convoys: int
    n_completed_convoys: int
    n_not_completed_convoys: int
    avg_completion_minute: float | None = None
    min_completion_minute: float | None = None
    max_completion_minute: float | None = None


class SimulateResponse(BaseModel):
    """Risposta di /simulate."""

    schema_version: str
    simulation_name: str
    total_minutes: int
    timestep_minutes: int
    n_convoys: int
    depot_capacity: int
    final_minute: int
    events_csv_path: str | None = None
    kpi: SimulationKPI


@app.post("/predict_risk", response_model=PredictResponse, tags=["risk"])
@app.post("/predict", response_model=PredictResponse, tags=["risk"])
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

    model_version = get_model_version("models/risk_model.pkl")

    response = PredictResponse(
        schema_version="1.0",
        model_version=model_version,
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        risk_threshold_used=RISK_THRESHOLD_DEFAULT,
        results=results,
    )

    # Audit di base: logghiamo la chiamata (senza PII)
    try:
        log_predict_call(request.model_dump(), response.model_dump())
    except Exception as exc:  # noqa: BLE001
        # Non vogliamo che un problema di logging blocchi l'API
        print(f"[WARN] Impossibile loggare la chiamata /predict: {exc}")

    return response


@app.post("/simulate", response_model=SimulateResponse, tags=["simulation"])
def simulate(request: SimulateRequest) -> SimulateResponse:
    """Esegue una simulazione singola e restituisce un riassunto.

    Usa run_simulation(...) per generare gli eventi e calcola alcuni KPI base.
    """
    # Costruiamo un SimConfig a partire dalla richiesta
    config = SimConfig(
        simulation_name=request.simulation_name,
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        depot_capacity=request.depot_capacity,
    )

    # Eseguiamo la simulazione; salviamo gli eventi in CSV
    events, summary = run_simulation(config, save_to_csv=True)

    # Prendiamo eventuale percorso del CSV dagli summary
    events_csv_path: str | None = summary.get("events_csv_path")

    # Calcoliamo KPI base usando il modulo metrics
    if events_csv_path:
        df_events = load_events_csv(events_csv_path)
    else:
        # Se per qualche motivo il path non c'è, costruiamo un DataFrame dagli eventi in
        # memoria
        import pandas as pd

        df_events = pd.DataFrame(events)

    kpi_dict = compute_basic_kpis(df_events)

    kpi = SimulationKPI(
        n_convoys=int(kpi_dict.get("n_convoys", summary.get("n_convoys", 0))),
        n_completed_convoys=int(
            kpi_dict.get("n_completed_convoys", summary.get("n_completed_convoys", 0))
        ),
        n_not_completed_convoys=int(
            kpi_dict.get(
                "n_not_completed_convoys", summary.get("n_not_completed_convoys", 0)
            )
        ),
        avg_completion_minute=kpi_dict.get("avg_completion_minute"),
        min_completion_minute=kpi_dict.get("min_completion_minute"),
        max_completion_minute=kpi_dict.get("max_completion_minute"),
    )

    response = SimulateResponse(
        schema_version="1.0",
        simulation_name=summary.get("simulation_name", request.simulation_name),
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        depot_capacity=request.depot_capacity,
        final_minute=int(summary.get("final_minute", request.total_minutes)),
        events_csv_path=events_csv_path,
        kpi=kpi,
    )

    return response

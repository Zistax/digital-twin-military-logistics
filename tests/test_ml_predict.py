import numpy as np

from src.ml.predict import prepare_convoy_features, predict_convoy_risk_proba


class DummyModel:
    """Modello fittizio per testare la pipeline di prediction.

    Implementa solo predict_proba con una logica semplice e controllabile.
    """

    def predict_proba(self, X):
        # X è un DataFrame o array; ritorniamo sempre:
        # - prob classe 0 = 0.7
        # - prob classe 1 = 0.3
        n_samples = len(X)
        proba = np.tile([0.7, 0.3], (n_samples, 1))
        return proba


def test_prepare_convoy_features_basic():
    df = prepare_convoy_features(total_minutes=120, timestep_minutes=10, n_convoys=3)

    assert list(df.columns) == ["convoy_id", "total_minutes", "timestep_minutes"]
    assert len(df) == 3
    assert df["convoy_id"].tolist() == [1, 2, 3]
    assert df["total_minutes"].tolist() == [120, 120, 120]
    assert df["timestep_minutes"].tolist() == [10, 10, 10]


def test_predict_convoy_risk_proba_with_dummy_model():
    model = DummyModel()
    df_result = predict_convoy_risk_proba(
        model,
        total_minutes=120,
        timestep_minutes=10,
        n_convoys=4,
    )

    # Dovremmo avere 4 righe, una per convoglio
    assert len(df_result) == 4
    assert list(df_result.columns) == ["convoy_id", "risk_proba"]

    # La DummyModel restituisce sempre prob classe 1 = 0.3
    assert np.allclose(df_result["risk_proba"].values, 0.3)

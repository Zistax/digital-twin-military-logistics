from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk


def test_is_high_risk_respects_threshold():
    thr = RISK_THRESHOLD_DEFAULT

    # Valore chiaramente sotto soglia
    assert is_high_risk(thr - 0.1) is False

    # Valore uguale alla soglia
    assert is_high_risk(thr) is True

    # Valore sopra la soglia
    assert is_high_risk(thr + 0.1) is True

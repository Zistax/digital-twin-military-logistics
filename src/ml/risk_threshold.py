"""Utility per la soglia di rischio predefinita.

Questo modulo centralizza la definizione di una soglia "default" per decidere
se un convoglio è considerato "ad alto rischio" oppure no.
"""

# Soglia di rischio predefinita.
# SOSTITUISCI 0.5 con il valore scelto nel notebook (es. 0.4, 0.6, ecc.).
RISK_THRESHOLD_DEFAULT: float = 0.3


def is_high_risk(prob: float, threshold: float | None = None) -> bool:
    """Ritorna True se la probabilità `prob` è >= soglia.

    Se threshold è None, usa RISK_THRESHOLD_DEFAULT.
    """
    if threshold is None:
        threshold = RISK_THRESHOLD_DEFAULT
    return prob >= threshold

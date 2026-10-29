"""Integración con una API externa de tasas de cambio (COP por cada USD)."""
import os
import time

import httpx

URL = "https://open.er-api.com/v6/latest/USD"  # API pública, sin clave
FALLBACK = float(os.getenv("FALLBACK_COP_PER_USD", "4000"))  # valor de respaldo aproximado
CACHE_SECONDS = 3600  # la tasa se guarda 1 hora para no llamar a la API en cada petición

_cache = {"rate": None, "at": 0.0}


def get_usd_rate() -> tuple[float, str]:
    """Devuelve (pesos por dólar, origen). Origen: 'live' o 'fallback'."""
    now = time.time()
    if _cache["rate"] is not None and now - _cache["at"] < CACHE_SECONDS:
        return _cache["rate"], "live"
    try:
        response = httpx.get(URL, timeout=5)
        response.raise_for_status()
        rate = float(response.json()["rates"]["COP"])
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        # Si la API externa falla, la app NO se cae: usa el valor de respaldo.
        return FALLBACK, "fallback"
    _cache["rate"] = rate
    _cache["at"] = now
    return rate, "live"

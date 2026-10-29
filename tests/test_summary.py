import os

# Base de datos de prueba aparte, definida ANTES de importar la app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import services  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    services._cache.update(rate=None, at=0.0)  # limpia la tasa guardada


def auth_headers(email: str = "a@b.com") -> dict:
    client.post("/auth/register", json={"email": email, "password": "clave12345"})
    r = client.post("/auth/login", data={"username": email, "password": "clave12345"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def add(h, category, amount, day):
    body = {"description": "x", "category": category, "amount_cop": amount, "date": day}
    client.post("/expenses", json=body, headers=h)


def test_summary_totals_and_month_filter(monkeypatch):
    # Se "finge" la tasa para que la prueba no dependa de internet
    monkeypatch.setattr("app.main.get_usd_rate", lambda: (4000.0, "live"))
    h = auth_headers()
    add(h, "comida", 20000, "2026-10-01")
    add(h, "comida", 10000, "2026-10-15")
    add(h, "transporte", 8000, "2026-10-20")
    add(h, "comida", 50000, "2026-09-30")  # otro mes: no debe contarse

    data = client.get("/summary?month=2026-10", headers=h).json()
    assert data["total_cop"] == 38000
    assert data["total_usd"] == 9.5
    assert data["rate_source"] == "live"
    totals = {c["category"]: c["total_cop"] for c in data["by_category"]}
    assert totals == {"comida": 30000, "transporte": 8000}


def test_summary_only_counts_own_expenses(monkeypatch):
    monkeypatch.setattr("app.main.get_usd_rate", lambda: (4000.0, "live"))
    h1 = auth_headers("a@b.com")
    h2 = auth_headers("c@d.com")
    add(h1, "comida", 20000, "2026-10-01")
    data = client.get("/summary?month=2026-10", headers=h2).json()
    assert data["total_cop"] == 0


def test_summary_rejects_invalid_month():
    h = auth_headers()
    assert client.get("/summary?month=2026-13", headers=h).status_code == 422


def test_summary_requires_token():
    assert client.get("/summary").status_code == 401


def test_rate_uses_api_value(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"rates": {"COP": 3900.5}}

    monkeypatch.setattr(services.httpx, "get", lambda *a, **k: FakeResponse())
    assert services.get_usd_rate() == (3900.5, "live")


def test_rate_falls_back_when_api_fails(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("sin internet")

    monkeypatch.setattr(services.httpx, "get", boom)
    rate, source = services.get_usd_rate()
    assert source == "fallback"
    assert rate == services.FALLBACK

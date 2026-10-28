import os

# Base de datos de prueba aparte, definida ANTES de importar la app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

GASTO = {"description": "Almuerzo", "category": "comida", "amount_cop": 18000, "date": "2026-10-01"}


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def auth_headers(email: str) -> dict:
    """Registra un usuario, inicia sesión y devuelve el encabezado con su token."""
    client.post("/auth/register", json={"email": email, "password": "clave12345"})
    r = client.post("/auth/login", data={"username": email, "password": "clave12345"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_and_list_expenses():
    h = auth_headers("a@b.com")
    r = client.post("/expenses", json=GASTO, headers=h)
    assert r.status_code == 201
    assert r.json()["description"] == "Almuerzo"
    r = client.get("/expenses", headers=h)
    assert len(r.json()) == 1


def test_user_cannot_see_other_users_expenses():
    h1 = auth_headers("a@b.com")
    h2 = auth_headers("c@d.com")
    client.post("/expenses", json=GASTO, headers=h1)
    assert client.get("/expenses", headers=h2).json() == []


def test_user_cannot_edit_or_delete_other_users_expense():
    h1 = auth_headers("a@b.com")
    h2 = auth_headers("c@d.com")
    expense_id = client.post("/expenses", json=GASTO, headers=h1).json()["id"]
    assert client.put(f"/expenses/{expense_id}", json=GASTO, headers=h2).status_code == 404
    assert client.delete(f"/expenses/{expense_id}", headers=h2).status_code == 404


def test_update_and_delete_own_expense():
    h = auth_headers("a@b.com")
    expense_id = client.post("/expenses", json=GASTO, headers=h).json()["id"]
    nuevo = {**GASTO, "amount_cop": 25000}
    r = client.put(f"/expenses/{expense_id}", json=nuevo, headers=h)
    assert r.status_code == 200
    assert r.json()["amount_cop"] == 25000
    assert client.delete(f"/expenses/{expense_id}", headers=h).status_code == 204
    assert client.get("/expenses", headers=h).json() == []


def test_invalid_amount_is_rejected():
    h = auth_headers("a@b.com")
    r = client.post("/expenses", json={**GASTO, "amount_cop": -5}, headers=h)
    assert r.status_code == 422


def test_expenses_require_token():
    assert client.get("/expenses").status_code == 401

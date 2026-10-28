import os

# Base de datos de prueba aparte, definida ANTES de importar la app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_register_and_login():
    r = client.post("/auth/register", json={"email": "a@b.com", "password": "clave12345"})
    assert r.status_code == 201
    r = client.post("/auth/login", data={"username": "a@b.com", "password": "clave12345"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.json()["email"] == "a@b.com"


def test_wrong_password():
    client.post("/auth/register", json={"email": "a@b.com", "password": "clave12345"})
    r = client.post("/auth/login", data={"username": "a@b.com", "password": "otra-clave"})
    assert r.status_code == 401


def test_duplicate_email():
    body = {"email": "a@b.com", "password": "clave12345"}
    client.post("/auth/register", json=body)
    assert client.post("/auth/register", json=body).status_code == 409


def test_me_requires_token():
    assert client.get("/me").status_code == 401

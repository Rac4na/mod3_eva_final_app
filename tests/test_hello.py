from fastapi.testclient import TestClient

from app.main import GREETING_NAME, app

client = TestClient(app)


def test_hello_ok():
    response = client.get("/hello")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == f"Hola, {GREETING_NAME}!"
    assert body["framework"] == "fastapi"


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_redirects_to_docs():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_root_reaches_docs():
    # Siguiendo la redireccion se llega a la documentacion servida por FastAPI.
    response = client.get("/")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()

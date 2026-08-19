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

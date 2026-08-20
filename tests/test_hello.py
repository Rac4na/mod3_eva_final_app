from fastapi.testclient import TestClient

from app.main import GREETING_NAME, SECRETO_ENV, app

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


# El secreto llega como variable de entorno, asi que estas pruebas corren en
# cualquier sitio: no hacen falta credenciales de Azure ni mocks del SDK. Es la
# ventaja de dejar que Container Apps resuelva el Key Vault por su cuenta.
def test_secreto_devuelve_el_valor_inyectado(monkeypatch):
    monkeypatch.setenv(SECRETO_ENV, "valor-de-prueba")
    response = client.get("/secreto")
    assert response.status_code == 200
    body = response.json()
    assert body["secreto"] == "valor-de-prueba"
    assert body["origen"] == "azure-key-vault"


def test_secreto_da_503_si_no_esta_configurado(monkeypatch):
    monkeypatch.delenv(SECRETO_ENV, raising=False)
    response = client.get("/secreto")
    assert response.status_code == 503
    assert SECRETO_ENV in response.json()["detail"]


def test_secreto_da_503_si_esta_vacio(monkeypatch):
    # Un secreto mal configurado llega como cadena vacia, no como ausente.
    monkeypatch.setenv(SECRETO_ENV, "")
    response = client.get("/secreto")
    assert response.status_code == 503

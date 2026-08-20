import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

GREETING_NAME = os.getenv("GREETING_NAME", "Daybid")

app = FastAPI(
    title="Hello Microservice",
    description="Microservicio de ejemplo con endpoint /hello (FastAPI)",
    version="1.0.0",
)


# Sin esto la raiz devuelve 404 y parece que el despliegue falla, cuando en
# realidad es la respuesta correcta de una API que no publica nada en /.
# include_in_schema la oculta del OpenAPI: es una comodidad, no parte del API.
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/hello")
def hello():
    return {
        "message": f"Hola, {GREETING_NAME}!",
        "framework": "fastapi",
    }


@app.get("/health")
def health():
    return {"status": "ok"}

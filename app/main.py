import os

from fastapi import FastAPI

GREETING_NAME = os.getenv("GREETING_NAME", "Daybid")

app = FastAPI(
    title="Hello Microservice",
    description="Microservicio de ejemplo con endpoint /hello (FastAPI)",
    version="1.0.0",
)


@app.get("/hello")
def hello():
    return {
        "message": f"Hola, {GREETING_NAME}!",
        "framework": "fastapi",
    }


@app.get("/health")
def health():
    return {"status": "ok"}

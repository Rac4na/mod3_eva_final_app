import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

GREETING_NAME = os.getenv("GREETING_NAME", "Daybid")

# La variable la inyecta Azure Container Apps resolviendo un secreto del Key
# Vault con la identidad administrada de la app. Ver keyvault.tf en el repo
# mod3_eva_final_infra: la aplicacion nunca habla con el Key Vault.
SECRETO_ENV = "SECRETO_DEMO"

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


@app.get("/secreto")
def secreto():
    # Se lee en cada peticion y no al importar el modulo, para que rotar el
    # secreto solo requiera una revision nueva y no un cambio de codigo.
    valor = os.getenv(SECRETO_ENV)

    # 503 y no 500: el servicio esta sano, es la configuracion la que falta.
    # Ocurre al ejecutar el contenedor sin la variable, fuera de Azure.
    if not valor:
        raise HTTPException(
            status_code=503,
            detail=(
                f"El secreto no esta disponible: falta la variable {SECRETO_ENV}. "
                "En Azure la inyecta Container Apps desde el Key Vault."
            ),
        )

    return {
        "secreto": valor,
        "origen": "azure-key-vault",
    }


@app.get("/health")
def health():
    return {"status": "ok"}

# mod3_eva_final_app

Microservicio con endpoint `/hello` que devuelve un saludo. Todo corre en
contenedor: no hace falta instalar Python ni dependencias en la máquina local.

La infraestructura de despliegue vive en un repositorio aparte:
**`mod3_eva_final_infra`** (Terraform + Azure Container Apps).

## Estructura

```
.
├── Dockerfile
├── requirements.txt
├── app/
│   └── main.py        # endpoints /hello y /health
└── tests/
    └── test_hello.py
```

## Endpoints

| Método | Ruta      | Respuesta |
|--------|-----------|-----------|
| GET    | `/hello`  | `{"message": "Hola, Daybid!", "framework": "fastapi"}` |
| GET    | `/health` | `{"status": "ok"}` |
| GET    | `/docs`   | Documentación OpenAPI (Swagger UI) |

## Construir la imagen

```bash
docker build -t hello-fastapi:1.0.0 .
```

## Ejecutar

```bash
docker run --rm -p 8000:8000 hello-fastapi:1.0.0
```

Probar en otra terminal:

```bash
curl http://localhost:8000/hello
```

## Cambiar el nombre del saludo

El nombre se lee de la variable de entorno `GREETING_NAME` (por defecto `Daybid`):

```bash
docker run --rm -p 8000:8000 -e GREETING_NAME="Tu Nombre" hello-fastapi:1.0.0
```

## Ejecutar las pruebas dentro del contenedor

```bash
docker run --rm hello-fastapi:1.0.0 pytest -v
```

## Publicar la imagen en Docker Hub

El repositorio de infraestructura consume la imagen desde Docker Hub, así que
debe estar publicada y ser **pública**.

```bash
docker login -u rac4na

docker buildx build \
  --platform linux/amd64 \
  -t rac4na/mod3_eva_final:1.0.0 \
  -t rac4na/mod3_eva_final:latest \
  --push .
```

`--platform linux/amd64` es obligatorio si construyes desde un Mac con Apple
Silicon: sin ese flag la imagen sale `arm64` y no arranca en los nodos de Azure.

# mod3_eva_final_app

Microservicio con endpoint `/hello` que devuelve un saludo. Todo corre en
contenedor: no hace falta instalar Python ni dependencias en la máquina local.

La infraestructura de despliegue vive en un repositorio aparte:
**`mod3_eva_final_infra`** (Terraform + Azure Container Apps).

## Estructura

```
.
├── .github/workflows/
│   └── ci-cd.yml      # pipeline de pruebas y despliegue
├── Dockerfile
├── requirements.txt
├── pytest.ini         # pythonpath, para que tests/ importe app/
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

En el día a día no hace falta publicar a mano: de eso se encarga el pipeline.

## CI/CD

El pipeline vive en [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) y
sigue un esquema git-flow: se trabaja en `develop` y `main` es la rama de release.

```
push a develop ──────────► build imagen + pytest                    (CI)

PR develop → main ───────► build imagen + pytest                    (CI)

merge a main ────────────► build imagen + pytest                    (CI)
                           ├─ push a Docker Hub  :<sha> y :latest    (artefacto)
                           ├─ az containerapp update --image :<sha>   (CD)
                           └─ curl /hello para verificar
```

Las pruebas corren **dentro de la imagen** que se va a desplegar
(`docker run --rm hello-fastapi:test pytest -v`), no en un entorno paralelo: se
valida el mismo artefacto que llega a producción.

### Artefacto y trazabilidad

El artefacto del pipeline es la imagen Docker. Cada despliegue usa el tag
`:<sha-del-commit>` en lugar de `:latest`, así que toda revisión de la Container
App es rastreable hasta un commit concreto y un rollback es simplemente volver a
desplegar un tag anterior:

```bash
az containerapp update -n ca-mod3-eva-final -g rg-mod3-eva-final \
  --image rac4na/mod3_eva_final:<sha-anterior>
```

### Secrets requeridos

En `Settings → Environments → dockerhub-publish → Environment secrets`. Son
secretos de environment, no de repositorio: por eso el job `deploy` declara
`environment: dockerhub-publish`, sin lo cual no los vería y llegarían vacíos a
las acciones de login.

| Secret | Para qué |
|---|---|
| `AZURE_CLIENT_ID` | App registration `gh-mod3-eva-final` en Entra ID |
| `AZURE_TENANT_ID` | Tenant de Entra ID |
| `AZURE_SUBSCRIPTION_ID` | Suscripción de Azure donde vive la infraestructura |
| `DOCKERHUB_USERNAME` | Cuenta que publica la imagen |
| `DOCKERHUB_TOKEN` | Personal access token con permiso *Read & Write* |

**No hay `AZURE_CLIENT_SECRET`.** La autenticación contra Azure es por OIDC: en
cada ejecución GitHub emite un token de identidad de corta vida y Entra ID lo
canjea por credenciales. La confianza está atada a una credencial federada con
subject `repo:Rac4na/mod3_eva_final_app:environment:dockerhub-publish`, de modo
que solo los jobs de este repositorio que apuntan a ese environment pueden
obtener acceso. No existe ninguna contraseña de larga vida que pueda filtrarse.

El subject lo determina el propio `environment:` del job: al declararlo, GitHub
emite el token como `...:environment:<nombre>` en lugar de `...:ref:<rama>`. Si
alguna vez se quita esa línea, hay que registrar en Entra ID la credencial
federada de rama que le corresponde.

Por eso el job de despliegue declara:

```yaml
permissions:
  id-token: write   # sin esto no se puede emitir el token OIDC
  contents: read
```

### Requisito previo

El paso de despliegue **falla si la infraestructura no existe todavía**, porque
`az containerapp update` actúa sobre una app ya creada. Antes del primer push a
`main` hay que ejecutar `terraform apply` en el repositorio
`mod3_eva_final_infra`.

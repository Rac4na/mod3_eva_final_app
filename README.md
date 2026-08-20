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
| GET    | `/`       | Redirige (307) a `/docs` |
| GET    | `/hello`  | `{"message": "Hola, Daybid!", "framework": "fastapi"}` |
| GET    | `/secreto`| `{"secreto": "...", "origen": "azure-key-vault"}` |
| GET    | `/health` | `{"status": "ok"}` |
| GET    | `/docs`   | Documentación OpenAPI (Swagger UI) |

La raíz redirige por comodidad: sin ella, abrir el dominio a secas devuelve
`{"detail":"Not Found"}` y parece que el despliegue está roto cuando en realidad
es la respuesta correcta de una API que no publica nada en `/`.

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

## El endpoint /secreto

Devuelve un valor almacenado en **Azure Key Vault**. Lo importante es que la
aplicación **no habla con Key Vault**: no incluye el SDK de Azure ni maneja
credenciales. Solo lee una variable de entorno.

```python
valor = os.getenv("SECRETO_DEMO")
```

Quien resuelve el secreto es Azure Container Apps, usando la identidad
administrada de la app. La cadena completa está definida en Terraform, en el
repositorio `mod3_eva_final_infra`:

```
Key Vault ── secreto-demo
    │  la plataforma lo lee con la identidad de la app
    ▼
Container App
    ├── secret { key_vault_secret_id, identity }
    └── env    { name = "SECRETO_DEMO", secret_name = ... }
              │
              ▼
        os.getenv("SECRETO_DEMO")
```

Esto tiene una consecuencia práctica: el endpoint se puede probar en local y en
CI sin Azure y sin mockear nada.

```bash
docker run --rm -p 8000:8000 -e SECRETO_DEMO="lo-que-sea" hello-fastapi:1.0.0
curl http://localhost:8000/secreto
```

Sin la variable, `/secreto` responde **503** y no 500: el servicio está sano y
es la configuración la que falta.

> Exponer el valor de un secreto en un endpoint público anula el propósito de un
> Key Vault. Aquí se hace porque el ejercicio lo pide. En un sistema real este
> endpoint devolvería metadatos —que la lectura funciona, el nombre, la
> versión— y nunca el valor.

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

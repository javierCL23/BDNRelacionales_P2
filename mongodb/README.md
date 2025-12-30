# MongoDB - Entorno Local

Este proyecto requiere tener MongoDB corriendo localmente para poder ejecutar y probar el contenido de la base de datos.

---

## Dependencias

Para ejecutar todo correctamente, se necesitan las siguientes herramientas:

- `uv`
- `podman` o `docker`
- `podman-compose` o `docker-compose`

---

## Ejecutar MongoDB localmente

Para iniciar una base de datos MongoDB local en segundo plano:

```bash
podman run -d \
  --name mongo \
  -p 27017:27017 \
  --rm \
  mongo:7

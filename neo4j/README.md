# Neo4j - Entorno Local

Este proyecto requiere tener Neo4j corriendo localmente para poder ejecutar y probar el contenido de la base de datos.

---

## Dependencias

Para ejecutar todo correctamente, se necesitan las siguientes herramientas:

- `uv`
- `podman` o `docker` para iniciar la base de datos de Neo4j con AUTH: neo4j/password_seguro

---

## Ejecutar Neo4j localmente

Para montar las dependencias de esta app es necesario ejecutar lo siguiente:

```
uv venv --python 3.11
source .venv/bin/activate
uv pip install .
python3 app.py

# O alternativamente la versión TUI
python3 neo.py

```

El ejecutable inserciones.py está pensado para ser lanzado desde la misma carpeta donde se tengan los ficheros .csv. En este caso desde la raíz del proyecto:
```
python3 neo4j/inserciones.py
```

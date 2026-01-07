# BDNRelacionales_P2

Repositorio dedicado a la segunda práctica de Bases de Datos no Relacionales.

## Estructura general

El proyecto se divide en varias carpetas con distintos módulos, siendo la Raíz el principal.

```
Proyecto
├── build/                       # Contenedores y configuraciones para despliegue
│   ├── mongodb/
│   │   └── Dockerfile           # Dockerfile para MongoDB
│   └── neo4j/
│       └── Dockerfile           # Dockerfile para Neo4j
├── mongodb/                     # Código y scripts relacionados con MongoDB
│   ├── app.py                   # Aplicación principal de MongoDB
│   ├── inserciones.py           # Scripts de inserción de datos
│   ├── consultas_simplificadas.txt # Consultas de ejemplo
│   ├── pyproject.toml           # Configuración de proyecto Python
│   ├── test_indices.py          # Tests para índices
│   ├── README.md                # Documentación específica de MongoDB
│   └── templates/
│       └── index.html           # Plantillas HTML para MongoDB
├── neo4j/                       # Código y scripts relacionados con Neo4j
│   ├── app.py                   # Aplicación principal de Neo4j
│   ├── inserciones.py           # Scripts de inserción de datos
│   ├── neo.py                   # Funciones de conexión y gestión de Neo4j
│   ├── pyproject.toml           # Configuración de proyecto Python
│   ├── README.md                # Documentación específica de Neo4j
│   └── templates/
│       └── index.html           # Plantillas HTML para Neo4j
├── utils/                       # Scripts utilizados y CSVs auxiliares
│   ├── crear_lineas.py          # Script para creación de estaciones.csv
│   ├── M4_Estaciones.csv        # CSV con estaciones de líneas de metro
│   └── M5_Estaciones.csv        # CSV con estaciones de líneas de Renfe
├── campus.csv                   # Datos de campus
├── estaciones.csv               # Datos de estaciones
├── estudios.csv                 # Datos de estudios
├── docker-compose.yaml          # Configuración de Docker Compose
└── README.md                    # Documentación principal del proyecto
```

El proyecto está pensado para poder ser ejecutado tanto de manera aislada u orquestada.

Para ello, se han creado una serie de pyproject con las dependencias necesarias para construir ambas aplicaciones en local. Sin embargo, se recomienda usar el modo orquestado.

Todos los comandos mostrados a continuación usan podman como OCI, pero se puede usar cualquiera a elección como Docker.

## Replicación manual

### Creación de las imágenes necesarias

```bash
# Creación de imagen de aplicación de mongoDB
podman build -t mongodb-app -f build/mongodb/Dockerfile .

# Creación de imagen de aplicación de neo4j
podman build -t neo4j-app -f build/neo4j/Dockerfile .
```

### Ejecución de cada una de las imágenes

```bash
# MongoDB
podman run -d \
    --name mongo \
    -p 27017:27017 --rm \
    docker.io/mongo:7

# Neo4j
podman run -d \
    --name neo4j_visual \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password_seguro \
    docker.io/neo4j:latest

# MongoApp
podman run -d \
    --name mongo-app \
    -p 5000:5000 --rm \
    mongodb-app

# Neo4jApp
podman run -d \
    --name neo-app \
    -p 5001:5001 --rm \
    neo4j-app
```

## Replicación orquestada

### Replicación parcial

```bash
# Iniciar solo mongoDB
podman-compose up mongo mongo-app --build

# Parar solo mongoDB
podman-compose down mongo mongo-app

# Iniciar solo Neo4j
podman-compose up neo neo-app --build
podman-compose down neo neo-app
```

### Replicación total

```bash
podman-compose up --build
podman-compose down
```

Ambos proyectos tienen sus respectivos scripts pensados para ser usados desde fuera de cualquier contenedor. En el caso de MongoDB, el programa test_indices.py pone a prueba el uso de índices para la optimización de consultas complejas. Por otro lado, en Neo4j hay una versión de terminal que muestra las mismas opciones pero desde una TUI más simple.

---

**Autores:** Carlos Arévalo López, Javier Carreño Luque
# DocumentOps

Sistema de automatización documental. V1 se centra en detectar facturas en una carpeta local, extraer sus datos mediante reglas deterministas y organizar los archivos de forma estructurada.

## Stack

- Python 3.12
- FastAPI
- Pydantic + Pydantic Settings
- SQLAlchemy 2.0 (síncrono)
- PostgreSQL 16
- Alembic
- PyMuPDF
- pytest
- Docker + Docker Compose

## Estructura

```
src/documentops/
├── config/          # settings, logging
├── domain/          # modelos de dominio puros
├── infrastructure/  # db, storage, repositories
├── application/     # servicios de aplicación
├── sources/         # DocumentSource, LocalFolderSource
├── processing/      # pipeline, workers
├── api/             # FastAPI routers
└── worker/          # entrypoint del worker

specs/               # especificación del sistema
docs/decisions/      # ADRs
```

## Configuración

Copia `.env.example` a `.env` y ajusta los valores si es necesario:

```bash
cp .env.example .env
```

## Desarrollo local

### Requisitos

- Python 3.12+
- Poetry
- Docker + Docker Compose

### Instalación

```bash
poetry install
```

### Tests

```bash
poetry run pytest
```

### API local

```bash
poetry run uvicorn documentops.api.main:app --reload
```

### Worker local

```bash
poetry run python -m documentops.worker.main
```

## Docker Compose

Levantar todos los servicios:

```bash
docker-compose up --build
```

La API estará disponible en `http://localhost:8000`. El worker procesará documentos desde `./data/input`.

Crear los directorios de datos antes de empezar:

```bash
mkdir -p data/input data/raw data/processed data/failed data/review
```

## Documentación

- Especificación: `/specs`
- Decisiones arquitectónicas: `/docs/decisions`

## Estado del proyecto

V1 en desarrollo. La especificación está aprobada y la implementación sigue el flujo:

`SPEC → FEATURE → BRANCH → IMPLEMENTACIÓN → TESTS → REVIEW → MERGE`

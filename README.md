# DocumentOps

Sistema de automatización documental que detecta documentos en una fuente configurada, extrae texto, clasifica por tipo, extrae datos estructurados y organiza los archivos automáticamente.

## Qué hace V1

```
PDF → input/ → Worker → Ingestión (SHA-256, idempotencia, raw/) → Pipeline → PostgreSQL → processed/ | review/ | failed/
```

- Detecta PDFs en una carpeta local.
- Extrae texto con PyMuPDF.
- Clasifica como `invoice` o `unknown` mediante reglas deterministas.
- Extrae campos de facturas (issuer, invoice_number, date, total, currency).
- Organiza facturas válidas en `processed/invoice/`, desconocidos en `review/unknown/`, errores en `failed/`.
- Registra cada transición de estado e intento de procesamiento en PostgreSQL.
- Garantiza idempotencia por SHA-256.
- Recupera documentos abandonados mediante leases.

## Stack

- Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.0, PostgreSQL 16, Alembic, PyMuPDF
- Docker + Docker Compose
- pytest, ruff

## Demo rápida con Docker

### 1. Clonar y levantar

```bash
git clone https://github.com/Ryuu-no-Mi/DocumentOps.git
cd DocumentOps
docker compose up -d --build
```

Los tres servicios arrancan: `postgres`, `api`, `worker`. El worker ejecuta las migraciones de Alembic automáticamente.

### 2. Verificar que la API funciona

```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"documentops-api"}
```

### 3. Crear directorios de datos

```bash
mkdir -p data/input
```

### 4. Crear un PDF de factura de prueba

```bash
poetry run python -c "
import pymupdf, os
os.makedirs('data/input', exist_ok=True)
doc = pymupdf.open()
page = doc.new_page()
page.insert_text((72, 72), 'ENDESA ENERGÍA\nFactura nº 2026/92837\nFecha: 01/09/2026\nTotal: 84,32 EUR\nIVA 21%')
doc.save('data/input/factura_endesa.pdf')
doc.close()
print('PDF creado')
"
```

### 5. Esperar al worker (~15 segundos)

El worker detecta el PDF, lo ingesta y lo procesa automáticamente.

```bash
# Ver logs del worker
docker compose logs worker -f
```

### 6. Consultar documentos procesados

```bash
# Lista de documentos
curl http://localhost:8000/documents

# Detalle de un documento (sustituir {id})
curl http://localhost:8000/documents/{id}

# Datos extraídos
curl http://localhost:8000/documents/{id}/extracted-data

# Historial de intentos
curl http://localhost:8000/documents/{id}/attempts

# Historial de transiciones
curl http://localhost:8000/documents/{id}/transitions
```

### 7. Resultado esperado para una factura

```json
{
  "status": "COMPLETED",
  "processed_path": "/app/data/processed/invoice/2026/09/invoice_2026-09-01_92837_abc12345.pdf"
}
```

Datos extraídos:

```json
{
  "document_type": "invoice",
  "confidence": 0.44,
  "extracted_fields": {
    "issuer": "Endesa",
    "invoice_number": "2026/92837",
    "date": "2026-09-01",
    "total": 84.32,
    "currency": "EUR"
  }
}
```

Transiciones:

```
DETECTED → PROCESSING → TEXT_EXTRACTED → CLASSIFIED → DATA_EXTRACTED → VALIDATED → ORGANIZED → COMPLETED
```

### 8. Resultado esperado para un documento desconocido

Crear un PDF sin contenido de factura:

```bash
poetry run python -c "
import pymupdf
doc = pymupdf.open()
page = doc.new_page()
page.insert_text((72, 72), 'Carta sobre el tiempo y deportes.')
doc.save('data/input/carta_desconocida.pdf')
doc.close()
"
```

Resultado:

```json
{
  "status": "NEEDS_REVIEW",
  "processed_path": "/app/data/review/unknown/2026/09/..."
}
```

Transiciones (sin pasar por DATA_EXTRACTED ni VALIDATED):

```
DETECTED → PROCESSING → TEXT_EXTRACTED → CLASSIFIED → ORGANIZED → NEEDS_REVIEW
```

### 9. Reprocesar un documento

```bash
curl -X POST http://localhost:8000/documents/{id}/reprocess
```

El documento vuelve a `DETECTED` y el worker lo procesa de nuevo.

### 10. Verificar idempotencia

Copiar el mismo PDF dos veces. El segundo se ignora:

```
Duplicate document skipped: hash=abc123...
```

### 11. Parar servicios

```bash
docker compose down
```

Para limpiar también la base de datos:

```bash
docker compose down -v
```

## Desarrollo local

### Requisitos

- Python 3.12+
- Poetry
- Docker + Docker Compose (para PostgreSQL)

### Instalación

```bash
poetry install
cp .env.example .env
```

### Levantar PostgreSQL

```bash
docker compose up -d postgres
```

### Ejecutar migraciones

```bash
poetry run alembic upgrade head
```

### Tests

```bash
DATABASE_URL=postgresql://documentops:documentops@localhost:5432/documentops poetry run pytest
```

### API local

```bash
poetry run uvicorn documentops.api.main:app --reload
```

### Worker local

```bash
poetry run python -m documentops.worker.main
```

## Arquitectura

```
src/documentops/
├── config/               # Pydantic Settings
├── domain/               # Modelos Pydantic, enums
├── infrastructure/
│   ├── db/               # SQLAlchemy models, session, Alembic
│   ├── repositories/     # DocumentRepository (CRUD, lease)
│   └── storage/          # file_storage (hash, sanitize, copy)
├── application/services/ # IngestionService, ReprocessService
├── sources/              # DocumentSource ABC, LocalFolderSource
├── processing/           # Pipeline (extract, classify, validate, organize)
├── api/                  # FastAPI + routers
└── worker/               # WorkerService (source polling + processing)
```

## Documentación

- Especificación: [`specs/`](specs/)
- Decisiones arquitectónicas: [`docs/decisions/`](docs/decisions/)

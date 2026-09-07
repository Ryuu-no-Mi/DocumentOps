# Spec 04 — Processing Pipeline

## 4.1 Estados del documento

Estados posibles de `Document.status`:

- `DETECTED`
- `PROCESSING`
- `TEXT_EXTRACTED`
- `CLASSIFIED`
- `DATA_EXTRACTED`
- `VALIDATED`
- `ORGANIZED`
- `COMPLETED`
- `FAILED`
- `NEEDS_REVIEW`

## 4.2 State machine

```
DETECTED
   │
   ▼
PROCESSING
   │
   ├──► TEXT_EXTRACTED
   │       │
   │       ▼
   │   CLASSIFIED
   │       │
   │       ├──► DATA_EXTRACTED
   │       │       │
   │       │       ▼
   │       │   VALIDATED
   │       │       │
   │       │       ▼
   │       │   ORGANIZED ──► COMPLETED
   │       │
   │       └──► ORGANIZED ──► NEEDS_REVIEW  (document_type=unknown)
   │
   ├──► FAILED (error técnico)
   │
   └──► NEEDS_REVIEW (no aplica directamente desde PROCESSING en V1)
```

## 4.3 Transiciones permitidas

| De | A | Condición |
|----|---|-----------|
| `DETECTED` | `PROCESSING` | Worker adquiere lease transaccional |
| `PROCESSING` | `TEXT_EXTRACTED` | Extracción de texto OK |
| `PROCESSING` | `FAILED` | Error técnico permanente en extracción |
| `TEXT_EXTRACTED` | `CLASSIFIED` | Clasificación OK |
| `TEXT_EXTRACTED` | `FAILED` | Error técnico en clasificación |
| `CLASSIFIED` + `invoice` | `DATA_EXTRACTED` | Extracción estructurada OK |
| `CLASSIFIED` + `unknown` | `ORGANIZED` | Resultado `unknown`: organizar a `review/unknown/` |
| `CLASSIFIED` + `invoice` | `FAILED` | Error técnico en extracción estructurada |
| `DATA_EXTRACTED` + válido | `VALIDATED` | Validación Pydantic OK |
| `DATA_EXTRACTED` + inválido | `ORGANIZED` | Validación fallida: organizar a `review/invoice/` |
| `VALIDATED` | `ORGANIZED` | Organizar a `processed/invoice/` |
| `ORGANIZED` | `COMPLETED` | Destino `processed/` |
| `ORGANIZED` | `NEEDS_REVIEW` | Destino `review/` |
| `ORGANIZED` | `FAILED` | Error técnico al mover archivo |
| `FAILED` | `PROCESSING` | Reintento manual vía API |
| `NEEDS_REVIEW` | `PROCESSING` | Reintento manual vía API |
| `COMPLETED` | `PROCESSING` | Reprocesamiento manual vía API |

## 4.4 Distinción entre UNKNOWN, NEEDS_REVIEW y FAILED

| Concepto | Naturaleza | Estado final | Ubicación |
|----------|------------|--------------|-----------|
| `unknown` | Tipo de documento | `NEEDS_REVIEW` | `review/unknown/` |
| `NEEDS_REVIEW` | Estado del documento | `NEEDS_REVIEW` | `review/` |
| `FAILED` | Estado por error técnico | `FAILED` | `failed/` |

`unknown` es un resultado de clasificación normal, no un error técnico.

## 4.5 Categorías de error y reintentos

| Categoría | Descripción | Reintento automático | Estado final |
|-----------|-------------|----------------------|--------------|
| `TRANSIENT` | Error temporal: archivo bloqueado, timeout | Sí, máximo `MAX_AUTO_RETRIES=3` | `FAILED` si se agotan |
| `PERMANENT` | Error técnico no recuperable: PDF corrupto | No | `FAILED` |
| `VALIDATION_ERROR` | Datos extraídos no cumplen validación | No | `NEEDS_REVIEW` |
| `MIME_TYPE_MISMATCH` | Extensión y content-type no coinciden | No | `FAILED` |
| `EXTRACTED_TEXT_TOO_LARGE` | Texto extraído supera 10 MB | No | `NEEDS_REVIEW` |

> `CLASSIFICATION_UNKNOWN` **no es una categoría de error**. Es el resultado normal `document_type=unknown`.

## 4.6 Lease y recuperación tras reinicio

Campos en `Document`:

| Campo | Propósito |
|-------|-----------|
| `processing_started_at` | Timestamp en que el worker comenzó a procesar |
| `processing_lease_expires_at` | Timestamp de expiración del lease |
| `processed_by` | Identificador del worker que lo procesa |

Adquisición transaccional:

```sql
BEGIN;
SELECT * FROM documents
WHERE status IN ('DETECTED', 'PROCESSING')
  AND (processing_lease_expires_at IS NULL OR processing_lease_expires_at < NOW())
ORDER BY received_at
LIMIT 1
FOR UPDATE SKIP LOCKED;

UPDATE documents
SET status = 'PROCESSING',
    processing_started_at = NOW(),
    processing_lease_expires_at = NOW() + INTERVAL 'PROCESSING_TIMEOUT_SECONDS seconds',
    processed_by = :worker_id
WHERE id = :document_id;
COMMIT;
```

El worker renueva el lease periódicamente durante el procesamiento. Si el worker muere, el lease expira y otro worker puede retomar el documento.

Esta operación debe implementarse y testearse de forma transaccional, incluyendo escenarios concurrentes.

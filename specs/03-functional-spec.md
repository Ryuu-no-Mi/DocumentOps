# Spec 03 — Functional Spec

## 3.1 Servicios

| Servicio | Responsabilidad |
|----------|-----------------|
| `api` | FastAPI + REST API. No procesa documentos. |
| `worker` | Detección (`LocalFolderSource`) + procesamiento (`ProcessingWorker`). |
| `postgres` | PostgreSQL como fuente de verdad de estados, metadatos y texto extraído. |

Ambos servicios comparten el mismo código fuente, pero arrancan con comandos diferentes.

## 3.2 Fuente

- V1 implementa únicamente `LocalFolderSource`.
- Escanea el directorio configurado mediante polling.
- El intervalo de polling es configurable mediante `POLL_INTERVAL_SECONDS`.
- Produce objetos `DocumentIngestionRequest`.
- No conoce el pipeline ni PostgreSQL.

## 3.3 Ingestión

Al recibir un `DocumentIngestionRequest`:

1. Validar extensión permitida (V1: `.pdf`).
2. Validar tamaño ≤ `MAX_FILE_SIZE_BYTES` (50 MB).
3. Validar content-type básico (`application/pdf`).
4. Si extensión y content-type no coinciden: crear `Document` en estado `FAILED` con `error_type=MIME_TYPE_MISMATCH` y mover a `failed/`.
5. Sanitizar el nombre de archivo original.
6. Calcular SHA-256 del contenido.
7. Si `file_hash` ya existe en PostgreSQL: ignorar (idempotencia).
8. Copiar archivo a `raw/` con nombre interno único.
9. Crear `Document` en estado `DETECTED`.

## 3.4 Worker

El worker ejecuta dos bucles independientes:

1. **Source polling**: detecta archivos en la carpeta local y los ingiere.
2. **Processing polling**: consulta PostgreSQL periódicamente para encontrar documentos pendientes y procesarlos.

V1 procesa **un solo documento simultáneamente**. La variable `WORKER_CONCURRENCY=1` existe preparada para futura concurrencia, pero no se implementa procesamiento paralelo en V1.

El worker adquiere un lease transaccional sobre el documento antes de procesarlo. Si el worker muere, el lease expira y otro worker puede retomarlo.

## 3.5 Pipeline de procesamiento

Pasos ejecutados por el worker:

1. **extract**: extraer texto del PDF y guardarlo en `ExtractedData.extracted_text`.
2. **classify**: aplicar reglas deterministas. Resultado `invoice` o `unknown`.
3. **structure**: si es `invoice`, extraer campos mediante reglas y regex.
4. **validate**: validar con Pydantic y generar lista de errores.
5. **organize**: mover archivo a `processed/`, `review/` o `failed/`.

## 3.6 Tipos de documento

- V1: `invoice`, `unknown`.
- `unknown` no es un error técnico: es un resultado de clasificación válido.
- Nuevos tipos se añaden como estrategias sin modificar el pipeline central.

## 3.7 Organización de archivos

| Resultado | Destino |
|-----------|---------|
| Factura válida | `processed/invoice/{year}/{month}/invoice_{date}_{invoice_number}_{hash_short}.pdf` |
| Documento `unknown` | `review/unknown/{year}/{month}/unknown_{received_at}_{hash_short}.pdf` |
| Factura con datos inválidos | `review/invoice/{year}/{month}/...` |
| Error técnico | `failed/{year}/{month}/{safe_filename}_{hash_short}.pdf` |

El `file_hash` completo sigue siendo el identificador único en PostgreSQL. El `hash_short` son los primeros 8 caracteres del SHA-256, usados únicamente para nombres de archivo legibles.

## 3.8 Reprocesamiento

- Endpoint `POST /documents/{id}/reprocess`.
- No crea un nuevo `Document`.
- Crea un nuevo `ProcessingAttempt` asociado al mismo `Document`.
- El estado del documento vuelve a `DETECTED` para que el worker lo retome.
- El historial completo de intentos y transiciones es consultable.

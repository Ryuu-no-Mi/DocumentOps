# Spec 02 — Requirements

## Requisitos funcionales

| ID | Requisito |
|----|-----------|
| FR-001 | El sistema MUST detectar nuevos archivos en el directorio de entrada configurado. |
| FR-002 | El sistema MUST soportar directorios `raw`, `processed`, `failed`, `review` y tipos de archivo soportados. |
| FR-003 | El sistema MUST extraer texto de archivos PDF. |
| FR-004 | El sistema MUST clasificar documentos como `invoice` o `unknown` mediante reglas deterministas. |
| FR-005 | El sistema MUST extraer datos estructurados de facturas: `issuer`, `invoice_number`, `date`, `total`, `currency`. |
| FR-006 | El sistema MUST validar datos extraídos con Pydantic. |
| FR-007 | El sistema MUST organizar facturas válidas en `processed/invoice/{year}/{month}/...`. |
| FR-008 | El sistema MUST organizar documentos `unknown` en `review/unknown/{year}/{month}/...`. |
| FR-009 | El sistema MUST mover documentos con errores técnicos a `failed/{year}/{month}/...`. |
| FR-010 | El sistema MUST registrar cada intento de procesamiento (`ProcessingAttempt`). |
| FR-011 | El sistema MUST registrar cada transición de estado (`StateTransition`). |
| FR-012 | El sistema MUST soportar reintentos manuales de procesamiento mediante API. |
| FR-013 | El sistema MUST evitar procesamiento duplicado usando SHA-256 del contenido. |
| FR-014 | El sistema MUST proveer una API REST para consultar documentos, estados e intentos. |
| FR-015 | El sistema MUST permitir añadir nuevas fuentes sin modificar el pipeline central. |
| FR-016 | El sistema MUST permitir añadir nuevos tipos de documento sin modificar el pipeline central. |
| FR-017 | El worker MUST ejecutarse en un contenedor separado del API. |

## Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| NFR-001 | El sistema MUST ser desplegable con Docker Compose. |
| NFR-002 | El sistema MUST tener tests unitarios y de integración con pytest. |
| NFR-003 | El sistema MUST usar variables de entorno para configuración sensible. |
| NFR-004 | El sistema MUST validar nombres de archivo y prevenir path traversal. |
| NFR-005 | El sistema MUST rechazar archivos mayores a `MAX_FILE_SIZE_BYTES` antes de procesarlos. |
| NFR-006 | El sistema MUST mantener un audit trail de estados e intentos. |
| NFR-007 | El pipeline MUST ser idempotente ante reinicios, duplicados y fallos parciales. |
| NFR-008 | El sistema SHOULD ejecutar CI con GitHub Actions. |
| NFR-009 | El sistema MUST guardar texto extraído en PostgreSQL con límite máximo de 10 MB. |
| NFR-010 | El worker MUST recuperar documentos abandonados en estado `PROCESSING` usando leases en PostgreSQL. |

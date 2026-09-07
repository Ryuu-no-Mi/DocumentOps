# Spec 05 — Data Model

## 5.1 documents

| Columna | Tipo | Notas |
|---------|------|-------|
| id | UUID | PK |
| source_type | VARCHAR | `local_folder` |
| source_id | VARCHAR | identificador de instancia de fuente |
| original_filename | VARCHAR | nombre original sanitizado |
| internal_filename | VARCHAR | nombre único en `raw/` |
| file_hash | VARCHAR(64) | SHA-256, **UNIQUE** |
| file_size | BIGINT | bytes |
| mime_type | VARCHAR | content-type validado |
| status | VARCHAR | estado actual del documento |
| raw_path | VARCHAR | ruta relativa en `raw/` |
| processed_path | VARCHAR | ruta relativa final |
| received_at | TIMESTAMP | momento de detección |
| processed_at | TIMESTAMP | nullable |
| processing_started_at | TIMESTAMP | nullable, para lease |
| processing_lease_expires_at | TIMESTAMP | nullable, para lease |
| processed_by | VARCHAR | nullable, identificador del worker |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |
| metadata | JSONB | contexto adicional de la fuente |

## 5.2 extracted_data

| Columna | Tipo | Notas |
|---------|------|-------|
| id | UUID | PK |
| document_id | UUID | FK → documents, **UNIQUE** |
| document_type | VARCHAR | `invoice`, `unknown` |
| confidence | FLOAT | 0.0 - 1.0, calculado por reglas |
| extracted_text | TEXT | limitado a 10 MB |
| extracted_fields | JSONB | datos estructurados extraídos |
| validation_errors | JSONB | lista de errores de validación |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

> `extracted_data` es una tabla independiente 1:1 con `documents`. No existe como columna en `documents`.

## 5.3 processing_attempts

| Columna | Tipo | Notas |
|---------|------|-------|
| id | UUID | PK |
| document_id | UUID | FK → documents |
| attempt_number | INT | secuencial por documento |
| step | VARCHAR | paso del pipeline |
| status | VARCHAR | `success`, `failed` |
| error_type | VARCHAR | `TRANSIENT`, `PERMANENT`, `VALIDATION_ERROR`, etc. |
| error_message | TEXT | nullable |
| started_at | TIMESTAMP | |
| finished_at | TIMESTAMP | nullable |
| created_at | TIMESTAMP | |

## 5.4 state_transitions

| Columna | Tipo | Notas |
|---------|------|-------|
| id | UUID | PK |
| document_id | UUID | FK → documents |
| from_state | VARCHAR | |
| to_state | VARCHAR | |
| reason | VARCHAR | nullable |
| created_by | VARCHAR | `system`, `api`, `worker` |
| created_at | TIMESTAMP | |

## 5.5 Restricciones y relaciones

- `documents.file_hash` tiene restricción `UNIQUE`.
- `extracted_data.document_id` tiene restricción `UNIQUE` (relación 1:1).
- `documents.id` → `processing_attempts.document_id` (1:N).
- `documents.id` → `state_transitions.document_id` (1:N).
- Toda transición de estado del documento genera un registro en `state_transitions`.

# Spec 08 — Error Handling

## 8.1 Categorías de error

| Categoría | Descripción | Reintento automático | Estado final |
|-----------|-------------|----------------------|--------------|
| `TRANSIENT` | Error temporal: archivo bloqueado, timeout de lectura | Sí, máximo `MAX_AUTO_RETRIES=3` | `FAILED` si se agotan |
| `PERMANENT` | Error técnico no recuperable: PDF corrupto, imágenes sin texto, excepción no controlada | No | `FAILED` |
| `VALIDATION_ERROR` | Datos extraídos no cumplen validación Pydantic | No | `NEEDS_REVIEW` |
| `MIME_TYPE_MISMATCH` | Extensión y content-type no coinciden | No | `FAILED` |
| `EXTRACTED_TEXT_TOO_LARGE` | Texto extraído supera 10 MB | No | `NEEDS_REVIEW` |

> `CLASSIFICATION_UNKNOWN` **no es una categoría de error**. Es el resultado normal `document_type=unknown`.

## 8.2 Texto extraído mayor a 10 MB

- No se trunca silenciosamente.
- Se registra `error_type=EXTRACTED_TEXT_TOO_LARGE` en `ProcessingAttempt`.
- Se almacena la causa en `ExtractedData.validation_errors`.
- El documento pasa a estado `NEEDS_REVIEW`.
- No se guarda texto parcial.

## 8.3 MIME mismatch

- Si la extensión y el content-type no coinciden:
  - Se crea el `Document` en estado `FAILED`.
  - Se registra `error_type=MIME_TYPE_MISMATCH`.
  - Se mueve el archivo a `failed/`.
  - No continúa el pipeline.

## 8.4 Documento `unknown`

- No es un error técnico.
- Se registra `document_type=unknown` en `ExtractedData`.
- Se calcula `confidence` según las reglas.
- El documento pasa a `NEEDS_REVIEW` y se organiza en `review/unknown/`.

## 8.5 Registro

- Todo error genera un `ProcessingAttempt` con `status=failed`.
- Todo cambio de estado genera un `StateTransition`.
- Logs estructurados con `document_id`, `attempt_number`, `step` y `error_type`.

# ADR-009: Texto extraído en PostgreSQL con límite

## Estado
Aprobado

## Contexto
El texto extraído de los PDFs debe conservarse para análisis, debugging y futuras mejoras.

## Decisión
- Guardar el texto extraído en la columna `ExtractedData.extracted_text`.
- Establecer límite máximo de 10 MB (`MAX_EXTRACTED_TEXT_LENGTH=10485760`).
- Si se supera, no se trunca silenciosamente: se marca como `NEEDS_REVIEW` con `error_type=EXTRACTED_TEXT_TOO_LARGE`.

## Consecuencias
- No se necesita búsqueda full-text en V1.
- PDFs muy grandes requerirán intervención manual o ajuste de configuración.

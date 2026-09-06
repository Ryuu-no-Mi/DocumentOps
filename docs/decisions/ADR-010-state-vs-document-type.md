# ADR-010: Separación estado del documento vs tipo de documento

## Estado
Aprobado

## Contexto
Es fácil confundir el estado de procesamiento con el resultado de la clasificación.

## Decisión
- El estado del documento (`Document.status`) describe dónde está en el pipeline.
- El tipo de documento (`ExtractedData.document_type`) describe qué clase de documento es.
- `unknown` es un tipo de documento válido, no un error.
- `NEEDS_REVIEW` es un estado del documento.
- `FAILED` es un estado por error técnico.

Ejemplo de flujo `unknown`:

```
CLASSIFIED (document_type=unknown)
   │
   ▼
ORGANIZED (review/unknown/)
   │
   ▼
NEEDS_REVIEW
```

## Consecuencias
Modelo semánticamente coherente. El audit trail refleja claramente qué pasó y por qué.

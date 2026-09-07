# ADR-005: Recuperación por lease en PostgreSQL

## Estado
Aprobado

## Contexto
Si el worker muere mientras procesa un documento en estado `PROCESSING`, el sistema debe poder detectar y retomar ese trabajo.

## Decisión
Usar un mecanismo de lease en PostgreSQL:
- `processing_started_at`
- `processing_lease_expires_at`
- `processed_by`

El worker actualiza el lease al tomar un documento y lo renueva periódicamente. Si el lease expira, otro worker puede retomarlo.

La adquisición usa:

```sql
BEGIN;
SELECT ... FROM documents
WHERE status IN ('DETECTED', 'PROCESSING')
  AND (processing_lease_expires_at IS NULL OR processing_lease_expires_at < NOW())
ORDER BY received_at
LIMIT 1
FOR UPDATE SKIP LOCKED;

UPDATE documents SET ... WHERE id = :document_id;
COMMIT;
```

## Consecuencias
Recuperación robusta sin dependencias adicionales. Requiere testear concurrencia.

# ADR-007: Idempotencia por SHA-256 UNIQUE

## Estado
Aprobado

## Contexto
Un mismo archivo puede aparecer varias veces. El sistema no debe procesarlo múltiples veces automáticamente.

## Decisión
- Calcular SHA-256 del contenido del archivo.
- Guardar en `documents.file_hash`.
- Aplicar restricción `UNIQUE` en PostgreSQL.
- Si el hash ya existe, se ignora el archivo duplicado.

## Consecuencias
La idempotencia está garantizada a nivel de aplicación y base de datos. El reprocesamiento manual sigue siendo posible.

# ADR-004: Worker separado sin Celery/Redis

## Estado
Aprobado

## Contexto
El procesamiento de documentos debe estar separado de la API, pero no queremos añadir infraestructura de colas externa.

## Decisión
- El servicio `api` ejecuta FastAPI.
- El servicio `worker` ejecuta detección y procesamiento.
- El worker consulta PostgreSQL periódicamente para encontrar documentos pendientes.
- No se usa Celery, Redis, RabbitMQ ni otra cola externa en V1.

## Consecuencias
- Simplicidad operativa.
- El worker es stateless.
- Posible acoplamiento al modelo de PostgreSQL, aceptado para V1.

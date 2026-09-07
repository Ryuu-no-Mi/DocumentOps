# Spec 07 — API

## 7.1 Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado de la API y conexión a base de datos |
| GET | `/documents` | Listar documentos con filtros opcionales |
| GET | `/documents/{id}` | Detalle de un documento |
| GET | `/documents/{id}/extracted-data` | Datos extraídos del documento |
| GET | `/documents/{id}/attempts` | Historial de intentos de procesamiento |
| GET | `/documents/{id}/transitions` | Historial de transiciones de estado |
| POST | `/documents/{id}/reprocess` | Reprocesar documento manualmente |
| GET | `/stats` | Estadísticas simples por estado |

## 7.2 Reglas

- La API no ejecuta el pipeline de procesamiento.
- La API no accede directamente al filesystem.
- La API delega en servicios de aplicación.
- El reprocesamiento (`POST /documents/{id}/reprocess`) no crea un nuevo `Document`. Cambia el estado a `DETECTED`, crea un nuevo `ProcessingAttempt` y el worker lo retoma.

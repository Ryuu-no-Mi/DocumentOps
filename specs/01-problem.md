# Spec 01 — Problem

Las personas y pequeñas empresas reciben documentos desde múltiples fuentes: correos electrónicos, descargas del navegador, carpetas locales, APIs.

Actualmente el proceso es manual:

1. Descargar o recibir el archivo.
2. Abrirlo e identificar qué tipo de documento es.
3. Buscar datos relevantes (proveedor, número, fecha, importe).
4. Renombrar el archivo.
5. Moverlo a la carpeta correcta.
6. Mantener un registro.

DocumentOps automatiza este flujo para documentos provenientes de fuentes configuradas.

## Scope V1

- **Fuente**: carpeta local (`LocalFolderSource`).
- **Tipos de documento**: `invoice` y `unknown`.
- **Pipeline**: determinista basado en reglas. Sin inteligencia artificial.
- **Arquitectura**: monolito modular desplegado en tres contenedores:
  - `api`: FastAPI y REST API.
  - `worker`: detección y procesamiento de documentos.
  - `postgres`: base de datos PostgreSQL.

El objetivo de V1 es demostrar un pipeline real, fiable y extensible, sin introducir complejidad innecesaria.

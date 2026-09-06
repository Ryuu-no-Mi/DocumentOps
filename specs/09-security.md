# Spec 09 — Security

## 9.1 Validación de archivos

- Extensión permitida en V1: `.pdf`.
- Content-type básico validado: `application/pdf`.
- Tamaño máximo: `MAX_FILE_SIZE_BYTES=52428800` (50 MB).
- Nombres de archivo sanitizados antes de cualquier operación.

## 9.2 Path traversal

- Las rutas base las controla la aplicación mediante variables de entorno.
- Nunca se usan rutas provenientes de nombres de archivo de usuario.
- Los nombres finales se generan internamente por la aplicación.

## 9.3 Configuración

- Toda configuración sensible y rutas mediante variables de entorno.
- Archivo `.env.example` en el repositorio.
- Archivo `.env` ignorado en control de versiones.
- Secrets fuera del repositorio.

## 9.4 Autenticación

- V1 no implementa autenticación.
- La API se expone solo en entornos controlados.

## 9.5 Límites de seguridad configurables

| Variable | Descripción | Valor por defecto V1 |
|----------|-------------|----------------------|
| `MAX_FILE_SIZE_BYTES` | Tamaño máximo de archivo | 52428800 |
| `MAX_EXTRACTED_TEXT_LENGTH` | Máximo de texto extraído | 10485760 |
| `MAX_AUTO_RETRIES` | Reintentos automáticos | 3 |

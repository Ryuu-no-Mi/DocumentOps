# ADR-002: Polling en LocalFolderSource

## Estado
Aprobado

## Contexto
La detección de archivos en carpetas locales puede hacerse con eventos (inotify, watchdog) o polling.

## Decisión
V1 utiliza polling configurable. No se usa watchdog ni inotify.

## Motivación
- Mayor simplicidad.
- Mejor portabilidad, especialmente en contenedores Docker.
- Menos dependencias.

## Consecuencias
Mayor latencia en la detección, controlada por `POLL_INTERVAL_SECONDS`.

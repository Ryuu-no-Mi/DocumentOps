# ADR-006: Almacenamiento de archivos en filesystem

## Estado
Aprobado

## Contexto
Los archivos físicos deben almacenarse de forma organizada y trazable.

## Decisión
Usar filesystem local con cuatro áreas:
- `raw/`: copia original del archivo detectado.
- `processed/`: archivos procesados correctamente.
- `review/`: archivos que requieren revisión humana.
- `failed/`: archivos con errores técnicos.

## Consecuencias
- Simple de implementar y entender.
- PostgreSOLO guarda rutas relativas, no contenido binario.
- Futura migración a S3 u otro storage es posible sin cambiar el modelo de datos.

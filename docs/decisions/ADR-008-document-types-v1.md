# ADR-008: Tipos de documento en V1

## Estado
Aprobado

## Contexto
Se podrían soportar muchos tipos de documento desde el inicio.

## Decisión
V1 soporta únicamente:
- `invoice`
- `unknown`

La arquitectura permite añadir nuevos tipos como estrategias sin modificar el pipeline central.

## Consecuencias
Menor alcance inicial, mayor fiabilidad. Los documentos que no son facturas van a revisión manual.

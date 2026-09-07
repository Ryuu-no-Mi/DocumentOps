# ADR-003: No usar IA/LLM en V1

## Estado
Aprobado

## Contexto
Se podría usar un LLM para clasificación y extracción, pero aumentaría complejidad, coste y falta de determinismo.

## Decisión
V1 usa únicamente código tradicional: parsing, regex, reglas y Pydantic.

## Motivación
- Construir un pipeline determinista y fiable primero.
- Demostrar capacidad de diseño sin depender de APIs externas.
- Dejar la puerta abierta a IA como mecanismo complementario en el futuro.

## Consecuencias
La precisión depende de la calidad de las reglas. Los documentos que no encajan irán a `NEEDS_REVIEW`.

# ADR-001: Stack inicial y librerías

## Estado
Aprobado

## Contexto
DocumentOps V1 necesita un stack simple, profesional y mantenible para una sola persona.

## Decisión
- **Python**: lenguaje principal.
- **FastAPI**: API REST.
- **Pydantic**: validación de datos y settings.
- **SQLAlchemy**: ORM para PostgreSQL.
- **PostgreSQL**: base de datos relacional.
- **pytest**: tests unitarios e integración.
- **Docker + Docker Compose**: entorno de desarrollo y despliegue.
- **PyMuPDF**: extracción de texto de PDFs.

## Consecuencias
Stack coherente con el objetivo del proyecto. Sin dependencias innecesarias.

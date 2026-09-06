# Spec 06 — Source System

## 6.1 Abstracción

Toda fuente de documentos implementa la misma interfaz:

```python
class DocumentSource(ABC):
    @abstractmethod
    async def poll(self) -> list[DocumentIngestionRequest]:
        ...
```

La fuente solo detecta archivos y produce solicitudes de ingesta. No conoce el pipeline, PostgreSQL ni el filesystem de destino.

## 6.2 LocalFolderSource

- Implementa `DocumentSource`.
- Lee archivos del directorio configurado.
- Utiliza polling configurable (`POLL_INTERVAL_SECONDS`).
- No utiliza watchdog, inotify ni eventos del sistema de archivos en V1.
- Ignora archivos ocultos, temporales y directorios.
- Valida extensión y tamaño básico antes de emitir el request.
- No procesa archivos.

## 6.3 DocumentIngestionRequest

```python
class DocumentIngestionRequest(BaseModel):
    source_type: str           # "local_folder"
    source_id: str             # identificador de la instancia
    original_filename: str
    file_path: Path            # ruta absoluta temporal del archivo detectado
    file_size: int
    mime_type: str
    received_at: datetime
    metadata: dict             # información adicional de la fuente
```

## 6.4 Extensibilidad

- `EmailSource`, `UploadSource` u otras fuentes futuras implementan `DocumentSource`.
- Producen el mismo `DocumentIngestionRequest`.
- El pipeline recibe un `Document` y no necesita conocer el `source_type` para funcionar.
- El `source_type`, `source_id` y `metadata` se conservan únicamente para trazabilidad.

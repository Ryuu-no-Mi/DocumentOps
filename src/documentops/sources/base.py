"""Abstract base class for document sources."""

from abc import ABC, abstractmethod

from documentops.domain.models import DocumentIngestionRequest


class DocumentSource(ABC):
    """Interface that all document sources must implement.

    A source detects files and produces ingestion requests.
    It does NOT process files, access PostgreSQL, or manage storage.
    """

    @abstractmethod
    async def poll(self) -> list[DocumentIngestionRequest]:
        """Detect new documents and return ingestion requests."""
        ...

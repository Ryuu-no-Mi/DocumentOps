"""Worker service that connects source detection, ingestion and processing."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from documentops.config.settings import settings
from documentops.application.services.ingestion import IngestionService
from documentops.infrastructure.db.session import SessionLocal
from documentops.infrastructure.repositories.document_repository import DocumentRepository
from documentops.processing.pipeline import DocumentProcessor
from documentops.sources.local_folder import LocalFolderSource

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class WorkerService:
    """Connects LocalFolderSource, IngestionService and DocumentProcessor.

    Two independent loops:
    1. Source polling: detect new files and ingest them.
    2. Processing polling: find pending documents and process them.
    """

    def __init__(self, source: LocalFolderSource | None = None) -> None:
        self.source = source or LocalFolderSource()
        self.worker_id = settings.worker_id

    def run(self) -> None:
        """Run both polling loops sequentially (V1: single document at a time)."""
        logger.info("Worker starting (id=%s)", self.worker_id)

        try:
            while True:
                self._source_poll_cycle()
                self._processing_poll_cycle()
                self._cleanup_expired_leases()
                import time
                time.sleep(settings.poll_interval_seconds)
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")

    def _source_poll_cycle(self) -> None:
        """Detect new files and ingest them."""
        db = SessionLocal()
        try:
            requests = _run_async(self.source.poll())
            if not requests:
                return

            logger.info("Detected %d new file(s)", len(requests))
            service = IngestionService(db)

            for request in requests:
                try:
                    doc = service.ingest(request)
                    if doc:
                        logger.info("Ingested: %s (id=%s)", request.original_filename, doc.id)
                    else:
                        logger.debug("Skipped duplicate: %s", request.original_filename)
                except ValueError as e:
                    logger.warning("Validation failed for %s: %s", request.original_filename, e)
                except Exception as e:
                    logger.error("Ingestion error for %s: %s", request.original_filename, e)
        except Exception as e:
            logger.error("Source poll error: %s", e)
        finally:
            db.close()

    def _processing_poll_cycle(self) -> None:
        """Find pending documents and process them."""
        db = SessionLocal()
        try:
            repo = DocumentRepository(db)
            pending = repo.get_pending_documents(limit=1)

            if not pending:
                return

            document = pending[0]
            logger.info("Processing document %s (status=%s)", document.id, document.status)

            lease_expires = datetime.now(timezone.utc) + timedelta(
                seconds=settings.processing_timeout_seconds
            )

            if document.status != "PROCESSING":
                repo.set_processing_lease(document, self.worker_id, lease_expires)
                db.commit()

            processor = DocumentProcessor(db)
            result = processor.process(document)
            db.commit()

            logger.info(
                "Document %s processed: status=%s",
                result.id,
                result.status,
            )
        except Exception as e:
            logger.error("Processing cycle error: %s", e)
            db.rollback()
        finally:
            db.close()

    def _cleanup_expired_leases(self) -> None:
        """Reset documents stuck in PROCESSING with expired leases."""
        db = SessionLocal()
        try:
            from documentops.infrastructure.db.models import Document
            from sqlalchemy import select

            now = datetime.now(timezone.utc)
            stmt = select(Document).where(
                Document.status == "PROCESSING",
                Document.processing_lease_expires_at < now,
            )
            stuck = list(db.scalars(stmt).all())

            for doc in stuck:
                logger.warning(
                    "Resetting stuck document %s (lease expired at %s)",
                    doc.id,
                    doc.processing_lease_expires_at,
                )
                doc.status = "DETECTED"
                doc.processing_started_at = None
                doc.processing_lease_expires_at = None
                doc.processed_by = None

            if stuck:
                db.commit()
                logger.info("Reset %d stuck document(s)", len(stuck))
        except Exception as e:
            logger.error("Lease cleanup error: %s", e)
            db.rollback()
        finally:
            db.close()

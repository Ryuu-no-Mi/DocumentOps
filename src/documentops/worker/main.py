"""Worker entrypoint."""

import logging

from documentops.config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def run_worker() -> None:
    """Run the document processing worker."""
    from documentops.infrastructure.storage.file_storage import ensure_storage_directories

    ensure_storage_directories()

    from documentops.worker.service import WorkerService

    service = WorkerService()
    service.run()


if __name__ == "__main__":
    run_worker()

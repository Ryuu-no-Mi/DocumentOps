"""Worker entrypoint."""

import logging
import time

from documentops.config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def run_worker() -> None:
    """Run the document processing worker."""
    logger.info("Starting DocumentOps worker (id=%s)", settings.worker_id)
    logger.info("Worker concurrency: %d", settings.worker_concurrency)
    logger.info("Poll interval: %d seconds", settings.poll_interval_seconds)

    try:
        while True:
            logger.debug("Worker polling cycle")
            # Source polling and processing polling will be implemented here.
            time.sleep(settings.poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")


if __name__ == "__main__":
    run_worker()

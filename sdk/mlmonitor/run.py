from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client

logger = logging.getLogger(__name__)


class Run:
    """Represents an active training run. Use as a context manager or call finish() manually."""

    def __init__(self, client: Client, experiment_id: str, run_id: str, name: str):
        self._client = client
        self.experiment_id = experiment_id
        self.id = run_id
        self.name = name
        self._finished = False

    def log(self, metric_name: str, value: float, step: int = 0) -> None:
        """Log a single metric value at the given step."""
        self._client._post(
            f'/api/experiments/{self.experiment_id}/runs/{self.id}/metrics/',
            {'name': metric_name, 'value': value, 'step': step},
        )
        logger.debug('Logged %s=%.4f @ step %d', metric_name, value, step)

    def finish(self, status: str = 'completed') -> None:
        """Mark the run as completed or failed. Idempotent."""
        if self._finished:
            return
        self._client._patch(
            f'/api/experiments/{self.experiment_id}/runs/{self.id}/',
            {'status': status, 'ended_at': datetime.datetime.now(datetime.timezone.utc).isoformat()},
        )
        self._finished = True
        logger.info('Run %s marked as %s', self.id, status)

    def __enter__(self) -> Run:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        status = 'failed' if exc_type is not None else 'completed'
        self.finish(status=status)
        return False

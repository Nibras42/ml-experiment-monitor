from __future__ import annotations

import datetime
import logging
from typing import Any

import requests

from .exceptions import APIError, AuthenticationError
from .run import Run

logger = logging.getLogger(__name__)


class Client:
    """
    MLMonitor API client.

    Usage::

        # Authenticate with a pre-issued JWT token
        client = Client("http://localhost:8000", token="<access-token>")

        # Or authenticate with email + password (fetches token automatically)
        client = Client("http://localhost:8000", email="you@example.com", password="secret")

        # Start a run and log metrics
        with client.run("My Experiment", hyperparameters={"lr": 0.001}) as run:
            for step, loss in enumerate(training_loop()):
                run.log("loss", loss, step=step)
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        email: str | None = None,
        password: str | None = None,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip('/')
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({'Content-Type': 'application/json'})

        if token:
            self._set_token(token)
        elif email and password:
            self._login(email, password)
        else:
            raise ValueError('Provide either token= or both email= and password=')

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _set_token(self, token: str) -> None:
        self._token = token
        self._session.headers['Authorization'] = f'Bearer {token}'

    def _login(self, email: str, password: str) -> None:
        resp = self._session.post(
            f'{self.base_url}/api/users/login/',
            json={'email': email, 'password': password},
            timeout=self._timeout,
        )
        if resp.status_code == 401:
            raise AuthenticationError('Invalid email or password')
        _raise_for_status(resp)
        self._set_token(resp.json()['access'])
        logger.info('Authenticated as %s', email)

    # ------------------------------------------------------------------
    # Experiment helpers
    # ------------------------------------------------------------------

    def _get_or_create_experiment(
        self,
        name: str,
        description: str = '',
        tags: list[str] | None = None,
    ) -> str:
        """Return the experiment ID, creating the experiment if it doesn't exist."""
        existing = self._get('/api/experiments/')
        for exp in existing:
            if exp['name'] == name:
                return exp['id']

        data = self._post('/api/experiments/', {'name': name, 'description': description, 'tags': tags or []})
        logger.info('Created experiment "%s" (%s)', name, data['id'])
        return data['id']

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        experiment_name: str,
        *,
        name: str = '',
        hyperparameters: dict[str, Any] | None = None,
        description: str = '',
        tags: list[str] | None = None,
    ) -> Run:
        """
        Create a new run under experiment_name and return a Run object.

        Use as a context manager so the run is automatically marked
        complete (or failed) when the block exits::

            with client.run("My Experiment", hyperparameters={"lr": 0.001}) as run:
                run.log("loss", 0.42, step=1)
        """
        experiment_id = self._get_or_create_experiment(experiment_name, description=description, tags=tags)

        started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        run_data = self._post(
            f'/api/experiments/{experiment_id}/runs/',
            {'name': name, 'hyperparameters': hyperparameters or {}},
        )
        self._patch(
            f'/api/experiments/{experiment_id}/runs/{run_data["id"]}/',
            {'status': 'running', 'started_at': started_at},
        )

        logger.info('Started run "%s" (%s)', name or run_data['id'], run_data['id'])
        return Run(self, experiment_id=experiment_id, run_id=run_data['id'], name=run_data['name'])

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, path: str) -> Any:
        resp = self._session.get(f'{self.base_url}{path}', timeout=self._timeout)
        _raise_for_status(resp)
        return resp.json()

    def _post(self, path: str, payload: dict) -> Any:
        resp = self._session.post(f'{self.base_url}{path}', json=payload, timeout=self._timeout)
        _raise_for_status(resp)
        return resp.json()

    def _patch(self, path: str, payload: dict) -> Any:
        resp = self._session.patch(f'{self.base_url}{path}', json=payload, timeout=self._timeout)
        _raise_for_status(resp)
        return resp.json()


def _raise_for_status(resp: requests.Response) -> None:
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise APIError(resp.status_code, detail)

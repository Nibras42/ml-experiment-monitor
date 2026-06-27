"""
SDK tests using unittest.mock — no running server required.
Each test patches requests.Session to intercept HTTP calls.
"""
import sys
import os
import json
from unittest.mock import MagicMock, call, patch

import pytest

# Make the sdk package importable without installing it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk'))

from mlmonitor import Client
from mlmonitor.exceptions import APIError, AuthenticationError
from mlmonitor.run import Run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mock_response(status_code=200, body=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body or {}
    resp.text = json.dumps(body or {})
    return resp


EXPERIMENT_PAYLOAD = {'id': 'exp-uuid-1', 'name': 'Test Exp', 'description': '', 'tags': [], 'run_count': 0, 'created_at': '', 'updated_at': ''}
RUN_PAYLOAD = {'id': 'run-uuid-1', 'name': 'run-1', 'status': 'pending', 'hyperparameters': {}, 'metric_count': 0, 'created_at': '', 'updated_at': ''}
METRIC_PAYLOAD = {'id': 'metric-uuid-1', 'name': 'loss', 'value': 0.42, 'step': 1, 'created_at': ''}


# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------

class TestClientInit:
    def test_token_sets_auth_header(self):
        with patch('requests.Session') as MockSession:
            session = MockSession.return_value
            Client('http://localhost:8000', token='my-token')
            session.headers.__setitem__.assert_any_call('Authorization', 'Bearer my-token')

    def test_email_password_calls_login(self):
        with patch('requests.Session') as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response(200, {'access': 'jwt-token', 'refresh': 'refresh-token'})
            Client('http://localhost:8000', email='user@test.com', password='pass')
            session.post.assert_called_once()
            args, kwargs = session.post.call_args
            assert '/api/users/login/' in args[0]
            assert kwargs['json'] == {'email': 'user@test.com', 'password': 'pass'}

    def test_login_failure_raises_authentication_error(self):
        with patch('requests.Session') as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response(401, {'detail': 'No active account'})
            with pytest.raises(AuthenticationError):
                Client('http://localhost:8000', email='x@x.com', password='wrong')

    def test_no_credentials_raises_value_error(self):
        with pytest.raises(ValueError):
            Client('http://localhost:8000')

    def test_base_url_trailing_slash_stripped(self):
        with patch('requests.Session'):
            client = Client('http://localhost:8000/', token='tok')
            assert client.base_url == 'http://localhost:8000'


# ---------------------------------------------------------------------------
# get_or_create_experiment
# ---------------------------------------------------------------------------

class TestGetOrCreateExperiment:
    def _make_client(self, session):
        client = Client.__new__(Client)
        client.base_url = 'http://localhost:8000'
        client._timeout = 30
        client._session = session
        return client

    def test_returns_existing_experiment_id(self):
        session = MagicMock()
        session.get.return_value = mock_response(200, [EXPERIMENT_PAYLOAD])
        client = self._make_client(session)

        exp_id = client._get_or_create_experiment('Test Exp')
        assert exp_id == 'exp-uuid-1'
        session.post.assert_not_called()

    def test_creates_experiment_when_not_found(self):
        session = MagicMock()
        session.get.return_value = mock_response(200, [])
        session.post.return_value = mock_response(201, EXPERIMENT_PAYLOAD)
        client = self._make_client(session)

        exp_id = client._get_or_create_experiment('Test Exp', tags=['nlp'])
        assert exp_id == 'exp-uuid-1'
        session.post.assert_called_once()
        _, kwargs = session.post.call_args
        assert kwargs['json']['name'] == 'Test Exp'
        assert kwargs['json']['tags'] == ['nlp']


# ---------------------------------------------------------------------------
# client.run()
# ---------------------------------------------------------------------------

class TestClientRun:
    def _make_client(self, session):
        client = Client.__new__(Client)
        client.base_url = 'http://localhost:8000'
        client._timeout = 30
        client._session = session
        return client

    def test_run_creates_experiment_and_run(self):
        session = MagicMock()
        session.get.return_value = mock_response(200, [])
        session.post.side_effect = [
            mock_response(201, EXPERIMENT_PAYLOAD),
            mock_response(201, RUN_PAYLOAD),
        ]
        session.patch.return_value = mock_response(200, {**RUN_PAYLOAD, 'status': 'running'})
        client = self._make_client(session)

        run = client.run('Test Exp', name='run-1', hyperparameters={'lr': 0.001})
        assert isinstance(run, Run)
        assert run.id == 'run-uuid-1'
        assert run.experiment_id == 'exp-uuid-1'

    def test_run_patches_status_to_running(self):
        session = MagicMock()
        session.get.return_value = mock_response(200, [EXPERIMENT_PAYLOAD])
        session.post.return_value = mock_response(201, RUN_PAYLOAD)
        session.patch.return_value = mock_response(200, {**RUN_PAYLOAD, 'status': 'running'})
        client = self._make_client(session)

        client.run('Test Exp')
        patch_call_kwargs = session.patch.call_args[1]
        assert patch_call_kwargs['json']['status'] == 'running'
        assert 'started_at' in patch_call_kwargs['json']

    def test_context_manager_finishes_run_on_success(self):
        session = MagicMock()
        session.get.return_value = mock_response(200, [EXPERIMENT_PAYLOAD])
        session.post.return_value = mock_response(201, RUN_PAYLOAD)
        session.patch.return_value = mock_response(200, {**RUN_PAYLOAD, 'status': 'running'})
        client = self._make_client(session)

        with client.run('Test Exp') as run:
            pass

        finish_call = session.patch.call_args_list[-1]
        assert finish_call[1]['json']['status'] == 'completed'

    def test_context_manager_marks_run_failed_on_exception(self):
        session = MagicMock()
        session.get.return_value = mock_response(200, [EXPERIMENT_PAYLOAD])
        session.post.return_value = mock_response(201, RUN_PAYLOAD)
        session.patch.return_value = mock_response(200, {**RUN_PAYLOAD, 'status': 'running'})
        client = self._make_client(session)

        with pytest.raises(ValueError):
            with client.run('Test Exp') as run:
                raise ValueError('training crashed')

        finish_call = session.patch.call_args_list[-1]
        assert finish_call[1]['json']['status'] == 'failed'


# ---------------------------------------------------------------------------
# Run.log
# ---------------------------------------------------------------------------

class TestRunLog:
    def _make_run(self, session):
        client = Client.__new__(Client)
        client.base_url = 'http://localhost:8000'
        client._timeout = 30
        client._session = session
        return Run(client, experiment_id='exp-uuid-1', run_id='run-uuid-1', name='run-1')

    def test_log_posts_metric(self):
        session = MagicMock()
        session.post.return_value = mock_response(201, METRIC_PAYLOAD)
        run = self._make_run(session)

        run.log('loss', 0.42, step=1)
        _, kwargs = session.post.call_args
        assert kwargs['json'] == {'name': 'loss', 'value': 0.42, 'step': 1}
        assert '/metrics/' in session.post.call_args[0][0]

    def test_log_defaults_step_to_zero(self):
        session = MagicMock()
        session.post.return_value = mock_response(201, METRIC_PAYLOAD)
        run = self._make_run(session)

        run.log('accuracy', 0.95)
        _, kwargs = session.post.call_args
        assert kwargs['json']['step'] == 0


# ---------------------------------------------------------------------------
# Run.finish
# ---------------------------------------------------------------------------

class TestRunFinish:
    def _make_run(self, session):
        client = Client.__new__(Client)
        client.base_url = 'http://localhost:8000'
        client._timeout = 30
        client._session = session
        return Run(client, experiment_id='exp-uuid-1', run_id='run-uuid-1', name='run-1')

    def test_finish_patches_status_completed(self):
        session = MagicMock()
        session.patch.return_value = mock_response(200, {**RUN_PAYLOAD, 'status': 'completed'})
        run = self._make_run(session)

        run.finish()
        _, kwargs = session.patch.call_args
        assert kwargs['json']['status'] == 'completed'

    def test_finish_patches_status_failed(self):
        session = MagicMock()
        session.patch.return_value = mock_response(200, {**RUN_PAYLOAD, 'status': 'failed'})
        run = self._make_run(session)

        run.finish(status='failed')
        _, kwargs = session.patch.call_args
        assert kwargs['json']['status'] == 'failed'

    def test_finish_is_idempotent(self):
        session = MagicMock()
        session.patch.return_value = mock_response(200, {})
        run = self._make_run(session)

        run.finish()
        run.finish()
        assert session.patch.call_count == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestAPIError:
    def _make_client(self, session):
        client = Client.__new__(Client)
        client.base_url = 'http://localhost:8000'
        client._timeout = 30
        client._session = session
        return client

    def test_4xx_raises_api_error(self):
        session = MagicMock()
        session.get.return_value = mock_response(404, {'detail': 'Not found'})
        client = self._make_client(session)

        with pytest.raises(APIError) as exc_info:
            client._get('/api/experiments/bad-id/')
        assert exc_info.value.status_code == 404

    def test_5xx_raises_api_error(self):
        session = MagicMock()
        session.post.return_value = mock_response(500, {'detail': 'Server error'})
        client = self._make_client(session)

        with pytest.raises(APIError) as exc_info:
            client._post('/api/experiments/', {})
        assert exc_info.value.status_code == 500

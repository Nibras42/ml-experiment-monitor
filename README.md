# MLMonitor

A Django-based MLOps dashboard for logging ML training runs, tracking metrics live via WebSockets, comparing experiments, defining data pipelines, and receiving threshold alerts. A companion Python SDK lets any training script push metrics in 3 lines.

→ **[Quick Start — run locally in 5 minutes](QUICKSTART.md)**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           Clients                               │
│   Browser (HTMX + Plotly)      Training script (mlmonitor SDK) │
└───────────────┬────────────────────────────┬────────────────────┘
                │ HTTP / WebSocket            │ REST API (JWT)
                ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Django + Daphne (ASGI)                       │
│                                                                 │
│  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  users   │  │experiments │  │pipelines │  │   alerts    │  │
│  │  (JWT)   │  │(runs/metr.)│  │  (DAG)   │  │(Celery Beat)│  │
│  └──────────┘  └─────┬──────┘  └──────────┘  └──────┬──────┘  │
│                      │ broadcast                      │ signal  │
│                      ▼                               ▼          │
│              ┌───────────────┐            ┌──────────────────┐  │
│              │ Channel Layer │            │  notifications   │  │
│              │  (WebSocket)  │            │ (email dispatch) │  │
│              └───────┬───────┘            └──────────────────┘  │
└──────────────────────┼──────────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │PostgreSQL│  │  Redis   │  │  Celery  │
    │  (data)  │  │(channels │  │ (worker  │
    │          │  │+ broker) │  │  + beat) │
    └──────────┘  └──────────┘  └──────────┘
```

---

## Features

- **Experiment tracking** — Create experiments, log runs, record hyperparameters
- **Live metric streaming** — Metrics pushed via WebSocket appear in the browser in real time
- **Run comparison** — Side-by-side Plotly charts across multiple runs
- **Data pipelines** — Define pipeline stages as a DAG; track status per stage
- **Alert rules** — Set metric thresholds; get an email when a run breaches them
- **Python SDK** — Push metrics from any training script with 3 lines of code
- **REST API** — Full JWT-authenticated API for all resources

---

## Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Django 6, Django REST Framework |
| Async / WebSockets | Django Channels, Daphne |
| Background tasks | Celery + Celery Beat |
| Message broker | Redis |
| Database (production) | PostgreSQL |
| Database (local dev) | SQLite |
| Frontend | HTMX, Tailwind CSS (CDN), Plotly, Mermaid |
| Auth | JWT via djangorestframework-simplejwt |
| Tests | pytest-django, factory\_boy |
| Static files | WhiteNoise |

---

## API Reference

All endpoints are prefixed with `/api/`. Pass `Authorization: Bearer <token>` on every request after login.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/register/` | Create account |
| POST | `/api/users/login/` | Obtain JWT tokens |
| POST | `/api/users/token/refresh/` | Refresh access token |
| GET | `/api/users/me/` | Current user profile |
| GET / POST | `/api/experiments/` | List / create experiments |
| GET / PATCH / DELETE | `/api/experiments/<id>/` | Experiment detail |
| GET / POST | `/api/experiments/<id>/runs/` | List / create runs |
| GET / PATCH / DELETE | `/api/experiments/<id>/runs/<id>/` | Run detail |
| GET / POST | `/api/experiments/<id>/runs/<id>/metrics/` | List / log metrics |
| WebSocket | `ws://host/ws/runs/<id>/?token=<jwt>` | Live metric stream |
| GET / POST | `/api/alerts/` | List / create alert rules |
| GET / PATCH / DELETE | `/api/alerts/<id>/` | Alert rule detail |
| GET / POST | `/api/pipelines/` | List / create pipelines |
| GET / PATCH / DELETE | `/api/pipelines/<id>/` | Pipeline detail |
| GET / POST | `/api/pipelines/<id>/stages/` | List / create stages |
| PATCH / DELETE | `/api/pipelines/<id>/stages/<id>/` | Stage detail |
| GET | `/api/pipelines/<id>/dag/` | Pipeline DAG (nodes + edges) |

---

## Python SDK

Install from the `sdk/` directory:

```bash
pip install ./sdk
```

```python
from mlmonitor import Client

client = Client("http://localhost:8000", email="you@example.com", password="secret")

with client.run("BERT Fine-tune", hyperparameters={"lr": 3e-5, "epochs": 10}) as run:
    for epoch in range(10):
        loss = train_one_epoch(model, data)
        run.log("loss", loss, step=epoch)
        run.log("accuracy", evaluate(model, val_data), step=epoch)
# Run is automatically marked completed (or failed on exception)
```

Or authenticate with a pre-issued token:

```python
client = Client("http://localhost:8000", token="<access-token>")
```

---

## Dashboard Pages

| URL | Page |
|-----|------|
| `/` | Overview — experiment, pipeline, and alert counts |
| `/experiments/` | Experiment list with live HTMX search |
| `/experiments/<id>/` | Runs table with status badges |
| `/experiments/<id>/runs/<id>/` | Metric charts (Plotly) + hyperparameters |
| `/experiments/<id>/compare/?runs=<id1>&runs=<id2>` | Side-by-side run comparison |
| `/pipelines/` | Pipeline list |
| `/pipelines/<id>/` | Stage table + interactive DAG (Mermaid) |

---

## Project Structure

```
config/           Django project config (settings, urls, asgi, celery)
apps/
  users/          Custom user model, JWT auth
  experiments/    Experiment, Run, Metric models + API + WebSocket consumer
  pipelines/      Pipeline, PipelineStage models + API + DAG endpoint
  alerts/         AlertRule model, threshold evaluation, Celery Beat tasks
  notifications/  Email dispatch (signal receivers)
  dashboard/      Template-based web UI (HTMX + Plotly + Mermaid)
sdk/
  mlmonitor/      Pip-installable Python client
tests/            All tests (pytest-django + factory_boy)
templates/        Django HTML templates
```

---

## Running Tests

```bash
pytest                            # all tests
pytest tests/test_experiments.py  # single file
pytest --tb=short -q              # compact output
```

---

## Docker (Full Stack)

Runs Django, Celery, PostgreSQL, and Redis together locally.

```bash
# Copy and edit the docker env file
cp .env.docker.example .env.docker   # set SECRET_KEY at minimum

# Start all services
docker compose up --build

# Create a superuser (first time only)
docker compose exec web python manage.py createsuperuser
```

---

## Project Breakdown

The project is divided into three tiers based on complexity.

### Easy — Built independently

These are the foundational parts of the project that any Django developer would be comfortable setting up on their own.

- Python virtual environment setup and dependency management (`requirements.txt`)
- Django project initialization and app structure
- Environment variable configuration (`.env`, `DJANGO_SETTINGS_MODULE`)
- Git repository setup, `.gitignore`, and commit workflow
- Django admin panel registrations for all models
- Basic URL routing (`config/urls.py`, per-app `urls.py`)
- Database migrations (`makemigrations`, `migrate`)

---

### Medium — Built with guidance

These required understanding new patterns or making architectural decisions, done collaboratively.

- Settings split into `base` / `development` / `production` / `test`
- Custom `User` model using `AbstractBaseUser` with email as the login field
- JWT authentication endpoints (register, login, token refresh, `/me`)
- REST API serializers and viewset-based views for experiments, runs, metrics, alerts, and pipelines
- HTMX-powered web dashboard (live search, partial template rendering)
- Plotly run comparison charts and hyperparameter display
- Railway deployment configuration and production settings

---

### Hard — Fully engineered

These involve advanced Django internals, async programming, or non-trivial system design.

- **Django Channels WebSocket consumer** — async `RunMetricsConsumer` that streams live metric updates to the browser in real time
- **JWT WebSocket middleware** — custom plain ASGI3 middleware class that authenticates WebSocket connections via a query-string token
- **Celery + Redis integration** — background worker, Celery Beat periodic scheduler, and alert threshold evaluation task running every 60 seconds
- **Signal-based notification system** — `alert_triggered` signal decouples the alerts app from the notifications app; email is dispatched as a Celery task
- **Pipeline DAG service** — builds a `{nodes, edges}` graph from `PipelineStage` dependency data; rendered as an interactive Mermaid.js diagram
- **Python SDK** (`mlmonitor`) — pip-installable client with a `Run` context manager that automatically marks runs complete or failed and logs metrics over REST
- **Full test suite** — 100+ tests using pytest-django, factory_boy, and `WebsocketCommunicator`; includes async WebSocket consumer tests with `transaction=True` isolation

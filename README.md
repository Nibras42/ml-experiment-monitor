# MLMonitor

A Django-based MLOps dashboard for logging ML training runs, tracking metrics in real time via WebSockets, comparing experiments, defining data pipelines, and receiving alerts when metric thresholds are breached.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                 │
│   Browser (HTMX + Plotly)    Training script (mlmonitor SDK)   │
└────────────┬────────────────────────────┬───────────────────────┘
             │ HTTP / WebSocket            │ REST API (JWT)
             ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Django + Daphne (ASGI)                       │
│                                                                 │
│  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  users   │  │experiments │  │pipelines │  │   alerts    │  │
│  │  (JWT)   │  │(runs/metr.)│  │  (DAG)   │  │ (Celery Beat│  │
│  └──────────┘  └─────┬──────┘  └──────────┘  └──────┬──────┘  │
│                      │ broadcast                      │ signal  │
│                      ▼                               ▼          │
│              ┌───────────────┐            ┌──────────────────┐  │
│              │ Channels Layer│            │  notifications   │  │
│              │  (WebSocket)  │            │ (email/webhook)  │  │
│              └───────┬───────┘            └──────────────────┘  │
└──────────────────────┼──────────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    ┌─────────┐  ┌──────────┐  ┌──────────┐
    │PostgreSQL│  │  Redis   │  │  Celery  │
    │  (data)  │  │(channels │  │ (worker  │
    │          │  │ + broker)│  │  + beat) │
    └──────────┘  └──────────┘  └──────────┘
```

---

## Quick Start (Local Dev)

**Requirements:** Python 3.12+, Redis running locally

```powershell
# 1. Clone and create virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env   # then edit .env with your values

# 4. Apply migrations and start server
python manage.py migrate
python manage.py runserver

# 5. In a second terminal — start Celery worker
celery -A config worker --loglevel=info --pool=solo

# 6. In a third terminal — start Celery Beat (alert scheduler)
celery -A config beat --loglevel=info
```

Open `http://localhost:8000/` to reach the dashboard.

---

## Docker (Recommended)

```powershell
# Copy and edit the docker env file
copy .env.docker .env.docker.local   # set SECRET_KEY at minimum

# Start all services
docker compose up --build

# Run migrations (first time only)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Services started: `web` (Daphne ASGI), `celery`, `celery-beat`, `db` (Postgres 16), `redis`.

---

## API Overview

All API endpoints are prefixed with `/api/`. Authentication uses JWT — obtain a token via `POST /api/users/login/` and pass it as `Authorization: Bearer <token>`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/register/` | Create account |
| POST | `/api/users/login/` | Obtain JWT tokens |
| POST | `/api/users/token/refresh/` | Refresh access token |
| GET/POST | `/api/experiments/` | List / create experiments |
| GET/PUT/PATCH/DELETE | `/api/experiments/<id>/` | Experiment detail |
| GET/POST | `/api/experiments/<id>/runs/` | List / create runs |
| GET/PATCH/DELETE | `/api/experiments/<id>/runs/<id>/` | Run detail |
| GET/POST | `/api/experiments/<id>/runs/<id>/metrics/` | List / log metrics |
| WS | `ws://host/ws/runs/<id>/?token=<jwt>` | Live metric stream |
| GET/POST | `/api/alerts/` | List / create alert rules |
| GET/PATCH/DELETE | `/api/alerts/<id>/` | Alert rule detail |
| GET/POST | `/api/pipelines/` | List / create pipelines |
| GET/PUT/PATCH/DELETE | `/api/pipelines/<id>/` | Pipeline detail |
| GET/POST | `/api/pipelines/<id>/stages/` | List / create stages |
| PATCH/DELETE | `/api/pipelines/<id>/stages/<id>/` | Stage detail |
| GET | `/api/pipelines/<id>/dag/` | Pipeline DAG (nodes + edges) |

---

## Python SDK

Install the SDK from the `sdk/` directory:

```bash
pip install ./sdk
```

**3-line usage:**

```python
from mlmonitor import Client

client = Client("http://localhost:8000", email="you@example.com", password="secret")

with client.run("BERT Fine-tune", hyperparameters={"lr": 3e-5, "epochs": 10}) as run:
    for epoch in range(10):
        loss = train_one_epoch(model, data)
        accuracy = evaluate(model, val_data)
        run.log("loss", loss, step=epoch)
        run.log("accuracy", accuracy, step=epoch)
# Run is automatically marked completed (or failed if an exception is raised)
```

Or with a pre-issued token:

```python
client = Client("http://localhost:8000", token="<access-token>")
```

---

## Dashboard

| Path | Page |
|------|------|
| `/` | Overview — experiment/pipeline/alert counts |
| `/experiments/` | Experiment list with live search (HTMX) |
| `/experiments/<id>/` | Runs table with status badges, multi-run compare |
| `/experiments/<id>/runs/<id>/` | Metric charts (Plotly), hyperparameters |
| `/experiments/<id>/compare/?runs=<id1>&runs=<id2>` | Side-by-side run comparison |
| `/pipelines/` | Pipeline list |
| `/pipelines/<id>/` | Stage table + interactive DAG (Mermaid) |

---

## Running Tests

```powershell
pytest                          # all tests
pytest tests/test_experiments.py  # single file
pytest --tb=short -q            # compact output
```

Target: ≥80% coverage across all apps.

---

## Project Structure

```
config/          Django project config (settings, urls, asgi, celery)
apps/
  users/         Custom user model, JWT auth
  experiments/   Experiment, Run, Metric models + API + WebSocket consumer
  pipelines/     Pipeline, PipelineStage models + API + DAG endpoint
  alerts/        AlertRule model, threshold evaluation, Celery Beat tasks
  notifications/ Email / webhook dispatch (signal receivers)
  dashboard/     Template-based web UI (HTMX + Plotly + Mermaid)
sdk/
  mlmonitor/     Pip-installable Python client
tests/           All tests (pytest-django + factory_boy)
templates/       Django templates (base + dashboard pages)
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Django 6, Django REST Framework |
| Async / WebSockets | Django Channels, Daphne |
| Background tasks | Celery + Celery Beat |
| Message broker / cache | Redis |
| Database (prod) | PostgreSQL 16 |
| Database (dev) | SQLite |
| Frontend | HTMX, Tailwind CSS (CDN), Plotly, Mermaid |
| Auth | JWT (djangorestframework-simplejwt) |
| Tests | pytest-django, factory\_boy |
| Static files | Whitenoise |

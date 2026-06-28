# Quick Start — Run Locally

Get the project running on your machine in under 5 minutes.

---

## Prerequisites

- Python 3.12 or later
- Git

Redis is **not** required for local development — the project uses an in-memory channel layer by default.

---

## 1. Clone the repo

```bash
git clone https://github.com/Nibras42/ml-experiment-monitor.git
cd ml-experiment-monitor
```

---

## 2. Create and activate a virtual environment

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Mac / Linux**
```bash
python -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Set up environment variables

```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

Open `.env` and set a value for `SECRET_KEY` — any long random string works for local dev:

```
SECRET_KEY=any-long-random-string-goes-here
```

Leave everything else as-is. SQLite is used automatically for local development.

---

## 5. Apply database migrations

```bash
python manage.py migrate
```

---

## 6. Create an admin account

```bash
python manage.py createsuperuser
```

Enter an email and password when prompted.

---

## 7. Start the development server

```bash
python manage.py runserver
```

Open your browser at **http://localhost:8000**

Log in with the email and password you just created.

---

## Running the tests

```bash
pytest
```

---

## Optional — Celery (only needed for alert threshold checking)

Alerts are evaluated by a background Celery worker. This is optional for basic testing.
You will need Redis running locally for this step.

```bash
# Terminal 2 — Celery worker
celery -A config worker --loglevel=info --pool=solo

# Terminal 3 — Celery Beat scheduler
celery -A config beat --loglevel=info
```

---

## Optional — Python SDK

To test the companion SDK from a training script:

```bash
pip install ./sdk
```

```python
from mlmonitor import Client

client = Client("http://localhost:8000", email="you@example.com", password="yourpassword")

with client.run("My Experiment", hyperparameters={"lr": 0.001}) as run:
    for step in range(10):
        run.log("loss", 1.0 / (step + 1), step=step)
```

# Productivity Tracker Backend

The AI-powered engine behind the Productivity Tracker Extension. This Django-based REST API ingests granular behavioral telemetry, manages asynchronous classification queues via Celery, and utilizes LangChain to accurately categorize user productivity workflows.

## Tech Stack

* **Framework:** Django & Django REST Framework (DRF)
* **Database:** PostgreSQL (Hosted on Aiven) with `pgvector` for semantic caching
* **Asynchronous Tasks:** Celery & Celery Beat
* **Message Broker:** Redis
* **AI Pipeline:** LangChain & Groq (`llama-3.3-70b-versatile`)
* **Infrastructure:** Docker & Docker Compose

## Core Architecture

1. **Ingestion API:** Receives throttled, granular telemetry (clicks, scrolls, keystrokes, semantic DOM text) from the browser extension and calculates a weighted Interactions Per Minute (IPM) score.
2. **The Dispatcher (Celery Beat):** Runs every 5 minutes, checking the database for unclassified browsing sessions and pushing device-specific jobs to the Redis queue using distributed locks to prevent duplication.
3. **The AI Worker (Celery):** Pulls chronological chunks of unclassified sessions, injecting the physical metrics and text snippets into a LangChain prompt. The Llama 3.3 model returns a strict Pydantic JSON object containing the intent category, reasoning, and a confidence score.
4. **Timeline API:** Serves the categorized, time-filtered data back to the React dashboard.

## Local Development Setup

### 1. Prerequisites
Ensure you have Python 3.12+ and Docker installed on your machine.

### 2. Environment Variables
Create a `.env` file in the root directory.

```env
DEBUG=True
SECRET_KEY=your-local-django-secret-key
GROQ_API_KEY=your-groq-api-key

# Database Connection (Local or Aiven)
DATABASE_URL=postgres://user:password@localhost:5432/productivity_db

# Redis connection for Celery
CELERY_BROKER_URL=redis://localhost:6379/0
```

### 3. Database Initialization
If using a managed PostgreSQL database like Aiven, ensure the `pgvector` extension is enabled before running migrations:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. Running the Stack (Docker)
The easiest way to run the entire backend stack locally is using Docker Compose. This spins up the Django API, Redis, the Celery worker, and the Celery Beat scheduler.

```bash
# Build and start all services
docker compose up --build

# Run database migrations inside the running web container
docker compose exec web python manage.py migrate
```

The API will be available at `http://localhost:9001`.

## Production Deployment
For production environments, use the `docker-compose.prod.yml` file. This configuration replaces the Django development server with a multi-worker Gunicorn WSGI server and includes strict restart policies for reliability.

```bash
docker compose -f docker-compose.prod.yml up -d --build
```
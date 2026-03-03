# ParkWise MTL

CLI chatbot that answers questions about Montréal paid street parking using public open data from the Agence de mobilité durable and Ville de Montréal.

## Features

- Search paid parking spaces by street name
- Check parking rules/regulations at any location and time
- Look up parking sign codes (RPA) and their meanings
- Find snow-removal parking lots nearby
- Natural language interface powered by Claude AI

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Anthropic API key

## Setup

1. **Clone and install dependencies:**

```bash
cd parkwise-mtl
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY
```

3. **Start PostGIS:**

```bash
docker compose up -d
```

4. **Run database migrations:**

```bash
alembic upgrade head
# Or let the seed script create tables directly
```

5. **Seed the database (downloads open data + loads into PostGIS):**

```bash
python scripts/seed.py
```

6. **Start the chatbot:**

```bash
python scripts/run_chat.py
```

## Usage

The chatbot starts a local FastAPI server and opens an interactive CLI:

```
🅿 You > How many paid parkings on Saint-Alexandre?
🅿 You > Can I park on Sainte-Catherine at 7pm?
🅿 You > Where can I park during snow removal near 45.5017,-73.5673?
```

Commands: `/reset` (clear history) · `/quit` (exit)

## API Endpoints

The FastAPI server is also accessible directly at `http://localhost:8000`:

| Endpoint | Description |
|---|---|
| `GET /parking/search?street=...` | Search parking spaces |
| `GET /parking/summary?street=...` | Parking summary for a street |
| `GET /parking/rules?lat=...&lon=...` | Parking rules at location/time |
| `GET /signs/search?street=...` | Parking signs on a street |
| `GET /snow/lots?lat=...&lon=...` | Nearby snow-removal lots |
| `GET /health` | API health check |

## Data Sources

- [Agence de mobilité durable](https://www.agencemobilitedurable.ca/fr/donnees-ouvertes) — paid parking spaces, pay stations, regulations
- [Ville de Montréal Open Data](https://donnees.montreal.ca/) — parking signage, snow-removal lots

## Tech Stack

- **FastAPI** — REST API
- **PostgreSQL + PostGIS** — spatial database
- **SQLAlchemy + GeoAlchemy2** — ORM
- **Claude AI** — natural language chatbot with tool-calling
- **Rich + prompt_toolkit** — terminal UI

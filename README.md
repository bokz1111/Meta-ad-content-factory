# Meta Ads Creative Factory

A local MVP application for storing marketing data and preparing ad variants for Meta (Facebook/Instagram) ads.

## Features

- **Projects** — Organize campaigns by brand, product, and language (EN/JP)
- **Assets** — Store landing page URLs and image paths per project
- **Angles** — Define messaging angles (pain point, benefit, hook, proof)
- **Variants** — Create ad copy variants linked to assets and angles
- **API** — JSON REST endpoints alongside the server-rendered UI

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
uvicorn ads_factory.main:app --reload --port 8000
```

### 4. Open the app

- UI: http://localhost:8000/projects
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Optional: Seed sample data

```bash
python -m ads_factory.scripts.seed
```

## Project Structure

```
ads_factory/
├── main.py                  # FastAPI app entrypoint
├── backend/
│   ├── models.py            # SQLAlchemy ORM models
│   ├── database.py          # DB engine, session, init
│   ├── schemas.py           # Pydantic schemas
│   └── routers/
│       └── projects.py      # UI + API routes
├── templates/
│   ├── base.html            # Layout base
│   └── projects/
│       ├── list.html        # /projects
│       ├── new.html         # /projects/new
│       └── dashboard.html   # /projects/{id}
├── scripts/
│   └── seed.py              # Sample data seeder
├── data/                    # SQLite DB stored here
├── exports/                 # Output files
└── ui/                      # Static assets (CSS/JS)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/projects` | List all projects |
| POST | `/api/projects` | Create a project |
| GET | `/api/projects/{id}` | Get project by ID |
| POST | `/api/assets` | Create an asset |
| POST | `/api/angles` | Create an angle |
| POST | `/api/variants` | Create a variant |

## Database Models

- **Project** — Brand, product/offer description, language settings, brand rules
- **Asset** — Landing page URL and image path linked to a project
- **Angle** — Messaging angle (pain point, benefit, hook, proof) per language
- **Variant** — Ad copy (headline, primary text, description, overlay) linked to asset + angle
- **Render** — Generated image paths (square/portrait/story formats)
- **QCResult** — Quality check scores per render

## Requirements

- Python 3.11+
- No external services required (SQLite, local files only)

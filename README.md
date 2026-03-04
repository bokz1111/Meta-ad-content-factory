# Meta Ads Creative Factory

A local MVP application for storing marketing data and preparing ad variants for Meta (Facebook/Instagram) ads.

## Features

- **Projects** — Organize campaigns by brand, product, and language (EN/JP)
- **Assets** — Store landing page URLs and image paths per project
- **Angles** — Define messaging angles (pain point, benefit, hook, proof)
- **Variants** — Create ad copy variants linked to assets and angles
- **Agent Registry** — DB-backed prompt store; edit system prompts + templates in the UI without code changes
- **Angle Builder** — Run `angle_builder_en` / `angle_builder_ja` to auto-generate angles from landing page data
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
│       ├── projects.py      # Project + angle + variant routes
│       └── assets.py        # fetch-landing + landing summary routes
├── templates/
│   ├── base.html            # Layout base
│   └── projects/
│       ├── list.html        # /projects
│       ├── new.html         # /projects/new
│       └── dashboard.html   # /projects/{id}
├── workers/
│   └── landing_extract.py   # BeautifulSoup scraper + normaliser
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
| POST | `/assets/{id}/fetch-landing` | Fetch + store landing page summary |
| GET | `/assets/{id}/landing` | Get latest landing summary JSON |
| POST | `/assets/{id}/run-angle-builder` | Run angle builder agent for an asset |
| GET | `/agents` | List agents (UI) |
| GET | `/api/agents` | List agents (JSON) |
| GET | `/agents/{id}` | Edit agent form |
| POST | `/agents/{id}` | Save agent edits |
| GET | `/api/agent-runs/{id}` | Get a single run result JSON |

## Database Models

- **Project** — Brand, product/offer description, language settings, brand rules
- **Asset** — Landing page URL and image path linked to a project
- **Angle** — Messaging angle (pain point, benefit, hook, proof) per language
- **Variant** — Ad copy (headline, primary text, description, overlay) linked to asset + angle
- **LandingSummary** — Extracted marketing data per asset (title, H1, H2s, bullets, CTAs, prices, paragraphs); cached by `content_hash`
- **AgentConfig** — Reusable agent definition: system prompt, user template, JSON schema, model settings
- **AgentRun** — Execution log for every agent invocation (inputs, outputs, status, duration)
- **Render** — Generated image paths (square/portrait/story formats)
- **QCResult** — Quality check scores per render

## Step 2 done: Landing page extraction + caching

Each asset with a `landing_page_url` can now have its page fetched and normalised into a compact marketing summary.

### How to add an asset

1. Open a project at `/projects/{id}`
2. In the **Assets** section scroll to **Add Asset**
3. Enter a `Landing Page URL` (e.g. `https://example.com/sale`) and optionally an image path
4. Click **Add Asset**

### How to fetch a landing summary

- In the **Assets** table, find the **Landing Data** column for any asset that has a URL
- Click **Fetch** (first fetch) or **↻ Refresh** (re-fetch)
- The page is scraped server-side; result is stored in the `landing_summaries` table
- If the page content hasn't changed (same `content_hash`), no new row is written — the button just returns "cached"

### Where to see the summary in the UI

- After a successful fetch the **Landing Data** cell shows a green timestamp badge
- Click the **"Asset #N — Landing summary"** collapsible panel that appears below the table
- The top section shows `title`, `h1`, and `meta_description` as readable text
- Expand **Full extracted JSON** to see the complete structured data:
  `headings_h2`, `bullets`, `ctas`, `price_mentions`, `top_paragraphs`

### API access

```
GET  /assets/{id}/landing         → latest summary JSON
POST /assets/{id}/fetch-landing   → trigger a fetch (add ?project_id=N to redirect back)
```

---

## Step 3 done: Agent Registry + Angle Builder

### Setting `ANTHROPIC_API_KEY`

```bash
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn ads_factory.main:app --reload --port 8000
```

Without the key the app runs in **stub mode** — the angle builder returns 3 hard-coded demo angles per run so the full UI/DB pipeline can be tested for free.

### How to edit agent prompts

1. Navigate to `/agents` (linked from every project dashboard)
2. Click **Edit** on `angle_builder_en` or `angle_builder_ja`
3. Modify **System Prompt** or **User Prompt Template** — save without restarting the server
4. Allowed template variables: `{{brand_name}}`, `{{brand_rules}}`, `{{product_description}}`, `{{offer_description}}`, `{{landing_summary_json}}`, `{{language}}`, `{{project_name}}`
5. The **Output JSON Schema** field validates the model response; leave blank to skip validation

### How to run the Angle Builder

1. Open a project dashboard (`/projects/{id}`)
2. In the **Assets** section expand the **"Asset #N — Angle Builder"** panel
3. Select an agent (`angle_builder_en` or `angle_builder_ja`) and click **Run Angle Builder**
4. New angles appear in the **Angles** section (duplicates are skipped automatically)
5. Each run is logged — click **view JSON** to inspect inputs/outputs

### Stub mode

When `ANTHROPIC_API_KEY` is absent, `llm.generate()` returns 3 deterministic demo angles instead of calling the API. The rest of the pipeline (JSON extraction, schema validation, upsert, AgentRun logging) runs exactly as in production.

---

## Requirements

- Python 3.11+
- No external services required (SQLite, local files only)
- Optional: `ANTHROPIC_API_KEY` for real LLM calls (stub mode works without it)

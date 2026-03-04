from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .backend.database import init_db, SessionLocal
from .backend.routers import projects as projects_router
from .backend.routers import assets as assets_router
from .backend.routers import agents as agents_router

app = FastAPI(title="Meta Ads Creative Factory", version="0.1.0")

# Static files
static_dir = Path(__file__).parent / "ui"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.on_event("startup")
def on_startup():
    init_db()
    # Seed default agents (idempotent — skips if already present)
    from .backend.seed import seed_default_agents
    db = SessionLocal()
    try:
        seed_default_agents(db)
    finally:
        db.close()


# Include routers
app.include_router(projects_router.router)
app.include_router(assets_router.router)
app.include_router(agents_router.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "Meta Ads Creative Factory"}


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return RedirectResponse(url="/projects")

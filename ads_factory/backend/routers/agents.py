import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AgentConfig, AgentRun, Asset
from ..services.angle_builder import run_angle_builder

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))

PURPOSE_OPTIONS = ["creative", "research", "critic", "compliance", "planner"]


# ── UI: agent list ────────────────────────────────────────────────────────────

@router.get("/agents", response_class=HTMLResponse)
def list_agents_ui(request: Request, db: Session = Depends(get_db)):
    agents = db.query(AgentConfig).order_by(AgentConfig.name).all()
    return templates.TemplateResponse("agents/list.html", {
        "request": request,
        "agents": agents,
    })


# ── UI: new agent form ────────────────────────────────────────────────────────

@router.get("/agents/new", response_class=HTMLResponse)
def new_agent_form(request: Request):
    return templates.TemplateResponse("agents/form.html", {
        "request": request,
        "agent": None,
        "runs": [],
        "purpose_options": PURPOSE_OPTIONS,
    })


@router.post("/agents")
def create_agent(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    purpose: str = Form("creative"),
    system_prompt: str = Form(...),
    user_prompt_template: str = Form(...),
    output_json_schema: Optional[str] = Form(None),
    model_provider: str = Form("anthropic"),
    model_name: str = Form("claude-sonnet-4-6"),
    temperature: float = Form(0.7),
    max_tokens: int = Form(4096),
    is_enabled: Optional[str] = Form(None),   # checkbox → None when unchecked
    db: Session = Depends(get_db),
):
    agent = AgentConfig(
        name=name.strip(),
        description=description,
        purpose=purpose,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        output_json_schema=output_json_schema or None,
        model_provider=model_provider,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        is_enabled=(is_enabled is not None),
    )
    db.add(agent)
    db.commit()
    return RedirectResponse(url="/agents", status_code=303)


# ── UI: edit agent ────────────────────────────────────────────────────────────

@router.get("/agents/{agent_id}", response_class=HTMLResponse)
def edit_agent_form(request: Request, agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.agent_id == agent_id)
        .order_by(AgentRun.created_at.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse("agents/form.html", {
        "request": request,
        "agent": agent,
        "runs": runs,
        "purpose_options": PURPOSE_OPTIONS,
    })


@router.post("/agents/{agent_id}")
def update_agent(
    agent_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    purpose: str = Form("creative"),
    system_prompt: str = Form(...),
    user_prompt_template: str = Form(...),
    output_json_schema: Optional[str] = Form(None),
    model_provider: str = Form("anthropic"),
    model_name: str = Form("claude-sonnet-4-6"),
    temperature: float = Form(0.7),
    max_tokens: int = Form(4096),
    is_enabled: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    agent = db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.name = name.strip()
    agent.description = description
    agent.purpose = purpose
    agent.system_prompt = system_prompt
    agent.user_prompt_template = user_prompt_template
    agent.output_json_schema = output_json_schema or None
    agent.model_provider = model_provider
    agent.model_name = model_name
    agent.temperature = temperature
    agent.max_tokens = max_tokens
    agent.is_enabled = (is_enabled is not None)
    agent.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url=f"/agents/{agent_id}", status_code=303)


# ── Run angle builder ─────────────────────────────────────────────────────────

@router.post("/assets/{asset_id}/run-angle-builder")
def run_angle_builder_route(
    asset_id: int,
    agent_name: str = Form("angle_builder_en"),
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    pid = project_id or asset.project_id

    agent = (
        db.query(AgentConfig)
        .filter(AgentConfig.name == agent_name, AgentConfig.is_enabled == True)  # noqa: E712
        .first()
    )
    if not agent:
        raise HTTPException(
            status_code=404, detail=f"Agent '{agent_name}' not found or disabled"
        )

    run_angle_builder(agent, asset_id, pid, db)
    return RedirectResponse(url=f"/projects/{pid}", status_code=303)


# ── JSON API ──────────────────────────────────────────────────────────────────

@router.get("/api/agents")
def list_agents_api(db: Session = Depends(get_db)):
    agents = db.query(AgentConfig).order_by(AgentConfig.name).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "purpose": a.purpose,
            "model_name": a.model_name,
            "is_enabled": a.is_enabled,
        }
        for a in agents
    ]


@router.get("/api/agent-runs/{run_id}")
def get_run_api(run_id: int, db: Session = Depends(get_db)):
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": run.id,
        "agent_id": run.agent_id,
        "project_id": run.project_id,
        "asset_id": run.asset_id,
        "status": run.status,
        "error_message": run.error_message,
        "input": json.loads(run.input_json) if run.input_json else None,
        "output": json.loads(run.output_json) if run.output_json else None,
        "duration_ms": run.duration_ms,
        "created_at": run.created_at.isoformat(),
    }

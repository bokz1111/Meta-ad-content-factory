"""
Angle Builder orchestration service.

Steps:
  1. Load Asset, Project, latest LandingSummary
  2. Render the agent's user_prompt_template
  3. Call the LLM via llm.generate()
  4. Extract the first valid JSON object from the response
  5. Validate against the agent's output_json_schema
  6. Upsert new Angles (skip near-duplicates)
  7. Persist an AgentRun record and return it
"""
import hashlib
import json
import re
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models import AgentConfig, AgentRun, Asset, Angle, LandingSummary, Project
from .llm import generate as llm_generate
from .prompt_renderer import render as render_prompt


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(text: str):
    """Extract the first valid JSON object or array from *text*."""
    # Strip markdown code fences if the model wrapped the JSON
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned.strip(), flags=re.MULTILINE)

    # Try the whole cleaned text first (ideal path)
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass

    # Fall back: find the outermost { … } or [ … ] block
    for pattern in (r"(\{[\s\S]*\})", r"(\[[\s\S]*\])"):
        m = re.search(pattern, cleaned)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    return None


# ── Duplicate detection ───────────────────────────────────────────────────────

def _angle_sig(project_id: int, language: str, name: str, hook: str) -> str:
    """Return an md5 fingerprint used to detect near-duplicate angles."""
    raw = f"{project_id}|{language}|{name.lower().strip()}|{hook[:60].lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


# ── Main entry point ─────────────────────────────────────────────────────────

def run_angle_builder(
    agent: AgentConfig,
    asset_id: int,
    project_id: int,
    db: Session,
) -> AgentRun:
    """
    Fully synchronous angle builder run.  Returns the persisted AgentRun.
    """
    t0 = time.monotonic()

    def _error_run(msg: str, output: Optional[dict] = None) -> AgentRun:
        run = AgentRun(
            agent_id=agent.id,
            project_id=project_id,
            asset_id=asset_id,
            run_type="angle_builder",
            input_json=json.dumps(input_meta),
            output_json=json.dumps(output) if output else None,
            status="error",
            error_message=msg,
            created_at=datetime.utcnow(),
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
        db.add(run)
        db.commit()
        return run

    # ── 1. Load records ───────────────────────────────────────────────────────
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    project = db.query(Project).filter(Project.id == project_id).first()

    input_meta: dict = {
        "agent_name": agent.name,
        "project_id": project_id,
        "asset_id": asset_id,
    }

    if not asset or not project:
        return _error_run("Asset or project not found")

    landing = (
        db.query(LandingSummary)
        .filter(LandingSummary.asset_id == asset_id)
        .order_by(LandingSummary.fetched_at.desc())
        .first()
    )

    # ── 2. Build variables ────────────────────────────────────────────────────
    if landing and landing.extracted_json:
        extracted = json.loads(landing.extracted_json)
        compact = {
            "title": landing.title,
            "h1": landing.h1,
            "meta_description": landing.meta_description,
            **extracted,
        }
        landing_json_str = json.dumps(compact, ensure_ascii=False, indent=2)
    else:
        landing_json_str = "No landing page data available."

    language = "JP" if ("jp" in agent.name.lower() or "ja" in agent.name.lower()) else "EN"
    input_meta["language"] = language
    input_meta["has_landing_summary"] = landing is not None

    variables = {
        "brand_name": project.brand_name or "",
        "brand_rules": project.brand_rules or "None specified",
        "product_description": project.product_description or "",
        "offer_description": project.offer_description or "No specific offer",
        "landing_summary_json": landing_json_str,
        "language": language,
        "project_name": project.name or "",
    }

    # ── 3. Render prompt ──────────────────────────────────────────────────────
    try:
        rendered_prompt = render_prompt(agent.user_prompt_template, variables)
    except ValueError as exc:
        return _error_run(f"Prompt render error: {exc}")

    # ── 4. LLM call ───────────────────────────────────────────────────────────
    try:
        raw_output = llm_generate(agent, rendered_prompt)
    except Exception as exc:
        return _error_run(f"LLM call failed: {exc}")

    # ── 5. Extract JSON ───────────────────────────────────────────────────────
    parsed = _extract_json(raw_output)
    if parsed is None:
        return _error_run(
            "Could not extract valid JSON from model output",
            {"raw_excerpt": raw_output[:500]},
        )

    # ── 6. JSON schema validation ─────────────────────────────────────────────
    if agent.output_json_schema:
        try:
            import jsonschema
            schema = json.loads(agent.output_json_schema)
            jsonschema.validate(instance=parsed, schema=schema)
        except json.JSONDecodeError:
            return _error_run("Agent output_json_schema is not valid JSON")
        except jsonschema.ValidationError as exc:
            return _error_run(
                f"Output failed schema validation: {exc.message}",
                {"raw_excerpt": raw_output[:500]},
            )

    # ── 7. Upsert angles ──────────────────────────────────────────────────────
    angles_data = parsed.get("angles", [])

    # Pre-compute existing signatures to avoid N+1 queries
    existing = db.query(Angle).filter(Angle.project_id == project_id).all()
    existing_sigs = {
        _angle_sig(project_id, a.language or "EN", a.name or "", a.hook or "")
        for a in existing
    }

    created_count = 0
    skipped_count = 0

    for ang in angles_data:
        name = (ang.get("name") or "").strip()
        hook = (ang.get("hook") or "").strip()
        lang = ang.get("language") or language
        if not name:
            continue
        sig = _angle_sig(project_id, lang, name, hook)
        if sig in existing_sigs:
            skipped_count += 1
            continue
        db.add(Angle(
            project_id=project_id,
            name=name,
            pain_point=(ang.get("pain_point") or ""),
            benefit=(ang.get("benefit") or ""),
            hook=hook,
            proof=(ang.get("proof") or ""),
            language=lang,
        ))
        existing_sigs.add(sig)
        created_count += 1

    db.flush()

    # ── 8. Persist AgentRun ───────────────────────────────────────────────────
    output_data = {
        "angles_found": len(angles_data),
        "angles_created": created_count,
        "angles_skipped": skipped_count,
    }
    run = AgentRun(
        agent_id=agent.id,
        project_id=project_id,
        asset_id=asset_id,
        run_type="angle_builder",
        input_json=json.dumps(input_meta),
        output_json=json.dumps(output_data),
        status="success",
        created_at=datetime.utcnow(),
        duration_ms=int((time.monotonic() - t0) * 1000),
    )
    db.add(run)
    db.commit()
    return run

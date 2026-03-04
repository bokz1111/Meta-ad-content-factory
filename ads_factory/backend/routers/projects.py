from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path

from ..database import get_db
from ..models import Project, Asset, Angle, Variant, LandingSummary
from ..schemas import ProjectCreate, AssetCreate, AngleCreate, VariantCreate

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


# --- API endpoints ---

@router.get("/api/projects")
def list_projects_api(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/api/projects/{project_id}")
def get_project_api(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/api/projects")
def create_project_api(data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.post("/api/assets")
def create_asset_api(data: AssetCreate, db: Session = Depends(get_db)):
    asset = Asset(**data.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/api/angles")
def create_angle_api(data: AngleCreate, db: Session = Depends(get_db)):
    angle = Angle(**data.model_dump())
    db.add(angle)
    db.commit()
    db.refresh(angle)
    return angle


@router.post("/api/variants")
def create_variant_api(data: VariantCreate, db: Session = Depends(get_db)):
    variant = Variant(**data.model_dump())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


# --- UI routes ---

@router.get("/projects", response_class=HTMLResponse)
def list_projects_ui(request: Request, db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return templates.TemplateResponse("projects/list.html", {
        "request": request,
        "projects": projects,
    })


@router.get("/projects/new", response_class=HTMLResponse)
def new_project_form(request: Request):
    return templates.TemplateResponse("projects/new.html", {"request": request})


@router.post("/projects/new")
def create_project_form(
    request: Request,
    name: str = Form(...),
    brand_name: str = Form(...),
    product_description: str = Form(...),
    offer_description: Optional[str] = Form(None),
    languages: str = Form("EN"),
    brand_rules: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    project = Project(
        name=name,
        brand_name=brand_name,
        product_description=product_description,
        offer_description=offer_description,
        languages=languages,
        brand_rules=brand_rules,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return RedirectResponse(url=f"/projects/{project.id}", status_code=303)


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_dashboard(request: Request, project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    assets = db.query(Asset).filter(Asset.project_id == project_id).all()
    angles = db.query(Angle).filter(Angle.project_id == project_id).all()
    variants = db.query(Variant).filter(Variant.project_id == project_id).order_by(Variant.created_at.desc()).all()

    # Latest LandingSummary per asset for UI status indicators
    asset_summaries: dict = {}
    for asset in assets:
        latest = (
            db.query(LandingSummary)
            .filter(LandingSummary.asset_id == asset.id)
            .order_by(LandingSummary.fetched_at.desc())
            .first()
        )
        if latest:
            asset_summaries[asset.id] = latest

    return templates.TemplateResponse("projects/dashboard.html", {
        "request": request,
        "project": project,
        "assets": assets,
        "angles": angles,
        "variants": variants,
        "asset_summaries": asset_summaries,
    })


@router.post("/projects/{project_id}/assets")
def add_asset(
    project_id: int,
    landing_page_url: Optional[str] = Form(None),
    image_path: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    asset = Asset(
        project_id=project_id,
        landing_page_url=landing_page_url,
        image_path=image_path,
        notes=notes,
    )
    db.add(asset)
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/projects/{project_id}/angles")
def add_angle(
    project_id: int,
    name: str = Form(...),
    pain_point: Optional[str] = Form(None),
    benefit: Optional[str] = Form(None),
    hook: Optional[str] = Form(None),
    proof: Optional[str] = Form(None),
    language: str = Form("EN"),
    db: Session = Depends(get_db),
):
    angle = Angle(
        project_id=project_id,
        name=name,
        pain_point=pain_point,
        benefit=benefit,
        hook=hook,
        proof=proof,
        language=language,
    )
    db.add(angle)
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/projects/{project_id}/variants")
def add_variant(
    project_id: int,
    asset_id: Optional[int] = Form(None),
    angle_id: Optional[int] = Form(None),
    language: str = Form("EN"),
    primary_text: Optional[str] = Form(None),
    headline: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    overlay_text: Optional[str] = Form(None),
    template_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    variant = Variant(
        project_id=project_id,
        asset_id=asset_id if asset_id else None,
        angle_id=angle_id if angle_id else None,
        language=language,
        primary_text=primary_text,
        headline=headline,
        description=description,
        overlay_text=overlay_text,
        template_id=template_id,
        status="draft",
    )
    db.add(variant)
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

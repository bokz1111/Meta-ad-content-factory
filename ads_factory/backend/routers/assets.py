import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, LandingSummary
from ...workers.landing_extract import extract_landing_summary

router = APIRouter()


@router.post("/assets/{asset_id}/fetch-landing")
def fetch_landing(
    asset_id: int,
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Fetch the landing page for this asset, extract marketing data, and store
    a LandingSummary row. If the content_hash is unchanged from the latest
    stored row, skip writing and return 'cached'.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not asset.landing_page_url:
        raise HTTPException(status_code=400, detail="Asset has no landing_page_url")

    data = extract_landing_summary(asset.landing_page_url)

    # Cache check: only skip if no error AND hash matches latest stored row
    latest = (
        db.query(LandingSummary)
        .filter(LandingSummary.asset_id == asset_id)
        .order_by(LandingSummary.fetched_at.desc())
        .first()
    )

    is_error = bool(data.get("error"))
    new_hash = data.get("content_hash")
    cached = (
        not is_error
        and latest is not None
        and latest.content_hash is not None
        and latest.content_hash == new_hash
    )

    if not cached:
        summary = LandingSummary(
            asset_id=asset_id,
            url=asset.landing_page_url,
            fetched_at=datetime.utcnow(),
            http_status=data.get("http_status"),
            title=data.get("title"),
            h1=data.get("h1"),
            meta_description=data.get("meta_description"),
            canonical_url=data.get("canonical_url"),
            language_detected=data.get("language_detected"),
            extracted_json=json.dumps({
                "headings_h2": data.get("headings_h2", []),
                "bullets": data.get("bullets", []),
                "ctas": data.get("ctas", []),
                "price_mentions": data.get("price_mentions", []),
                "top_paragraphs": data.get("top_paragraphs", []),
                "error": data.get("error"),
            }),
            raw_text_excerpt=data.get("raw_text_excerpt", ""),
            content_hash=new_hash,
        )
        db.add(summary)
        db.commit()

    if project_id:
        return RedirectResponse(url=f"/projects/{project_id}", status_code=303)
    return {"status": "cached" if cached else "fetched", "asset_id": asset_id}


@router.get("/assets/{asset_id}/landing")
def get_landing_summary(asset_id: int, db: Session = Depends(get_db)):
    """Return the latest LandingSummary for an asset as JSON."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    latest = (
        db.query(LandingSummary)
        .filter(LandingSummary.asset_id == asset_id)
        .order_by(LandingSummary.fetched_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No landing summary found for this asset")

    extracted = json.loads(latest.extracted_json) if latest.extracted_json else {}
    return {
        "id": latest.id,
        "asset_id": latest.asset_id,
        "url": latest.url,
        "fetched_at": latest.fetched_at.isoformat(),
        "http_status": latest.http_status,
        "title": latest.title,
        "h1": latest.h1,
        "meta_description": latest.meta_description,
        "canonical_url": latest.canonical_url,
        "language_detected": latest.language_detected,
        "content_hash": latest.content_hash,
        **extracted,
    }

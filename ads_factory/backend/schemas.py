from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


# --- Project ---

class ProjectCreate(BaseModel):
    name: str
    brand_name: str
    product_description: str
    offer_description: Optional[str] = None
    languages: str = "EN"
    brand_rules: Optional[str] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    brand_name: str
    product_description: str
    offer_description: Optional[str]
    languages: str
    brand_rules: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Asset ---

class AssetCreate(BaseModel):
    project_id: int
    landing_page_url: Optional[str] = None
    image_path: Optional[str] = None
    notes: Optional[str] = None


class AssetOut(BaseModel):
    id: int
    project_id: int
    landing_page_url: Optional[str]
    image_path: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Angle ---

class AngleCreate(BaseModel):
    project_id: int
    name: str
    pain_point: Optional[str] = None
    benefit: Optional[str] = None
    hook: Optional[str] = None
    proof: Optional[str] = None
    language: str = "EN"


class AngleOut(BaseModel):
    id: int
    project_id: int
    name: str
    pain_point: Optional[str]
    benefit: Optional[str]
    hook: Optional[str]
    proof: Optional[str]
    language: str

    class Config:
        from_attributes = True


# --- Variant ---

class VariantCreate(BaseModel):
    project_id: int
    asset_id: Optional[int] = None
    angle_id: Optional[int] = None
    language: str = "EN"
    primary_text: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    overlay_text: Optional[str] = None
    template_id: Optional[str] = None
    status: str = "draft"


class VariantOut(BaseModel):
    id: int
    project_id: int
    asset_id: Optional[int]
    angle_id: Optional[int]
    language: str
    primary_text: Optional[str]
    headline: Optional[str]
    description: Optional[str]
    overlay_text: Optional[str]
    template_id: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

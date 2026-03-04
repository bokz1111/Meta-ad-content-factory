from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    brand_name = Column(String(255), nullable=False)
    product_description = Column(Text, nullable=False)
    offer_description = Column(Text, nullable=True)
    languages = Column(String(50), default="EN")  # comma-separated: EN,JP
    brand_rules = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    angles = relationship("Angle", back_populates="project", cascade="all, delete-orphan")
    variants = relationship("Variant", back_populates="project", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    landing_page_url = Column(String(512), nullable=True)
    image_path = Column(String(512), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="assets")
    variants = relationship("Variant", back_populates="asset")


class Angle(Base):
    __tablename__ = "angles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    pain_point = Column(Text, nullable=True)
    benefit = Column(Text, nullable=True)
    hook = Column(Text, nullable=True)
    proof = Column(Text, nullable=True)
    language = Column(String(10), default="EN")

    project = relationship("Project", back_populates="angles")
    variants = relationship("Variant", back_populates="angle")


class Variant(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    angle_id = Column(Integer, ForeignKey("angles.id"), nullable=True)
    language = Column(String(10), default="EN")
    primary_text = Column(Text, nullable=True)
    headline = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    overlay_text = Column(String(255), nullable=True)
    template_id = Column(String(100), nullable=True)
    status = Column(String(50), default="draft")  # draft, ready, exported
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="variants")
    asset = relationship("Asset", back_populates="variants")
    angle = relationship("Angle", back_populates="variants")
    renders = relationship("Render", back_populates="variant", cascade="all, delete-orphan")


class Render(Base):
    __tablename__ = "renders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    image_square = Column(String(512), nullable=True)   # 1080x1080
    image_portrait = Column(String(512), nullable=True)  # 1080x1350
    image_story = Column(String(512), nullable=True)     # 1080x1920
    created_at = Column(DateTime, default=datetime.utcnow)

    variant = relationship("Variant", back_populates="renders")
    qc_result = relationship("QCResult", back_populates="render", uselist=False)


class QCResult(Base):
    __tablename__ = "qc_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    render_id = Column(Integer, ForeignKey("renders.id"), nullable=False)
    blur_score = Column(Float, nullable=True)
    brightness_score = Column(Float, nullable=True)
    clutter_score = Column(Float, nullable=True)
    warnings_json = Column(Text, nullable=True)  # JSON string

    render = relationship("Render", back_populates="qc_result")

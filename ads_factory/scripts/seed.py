"""
Optional seed script — populates the database with sample data for development.
Run: python -m ads_factory.scripts.seed
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ads_factory.backend.database import SessionLocal, init_db
from ads_factory.backend.models import Project, Asset, Angle, Variant


def seed():
    init_db()
    db = SessionLocal()

    # Check if already seeded
    if db.query(Project).count() > 0:
        print("Database already has data, skipping seed.")
        db.close()
        return

    project = Project(
        name="Summer Sale 2024",
        brand_name="Acme Store",
        product_description="Premium ergonomic office chairs designed for remote workers who spend 8+ hours at a desk.",
        offer_description="50% off sitewide, limited to first 500 orders. Free shipping included.",
        languages="EN,JP",
        brand_rules="Tone: friendly, confident. Avoid: medical claims, competitor names. Use: action verbs, numbers.",
    )
    db.add(project)
    db.flush()

    asset = Asset(
        project_id=project.id,
        landing_page_url="https://acmestore.example.com/summer-sale",
        image_path="data/images/chair_hero.jpg",
        notes="Hero image, white background, 1200x1200px",
    )
    db.add(asset)
    db.flush()

    angle_en = Angle(
        project_id=project.id,
        name="Back Pain Relief",
        pain_point="Hours of sitting cause chronic back pain and poor posture",
        benefit="Ergonomic lumbar support eliminates pain within days",
        hook="Still suffering from back pain after every workday?",
        proof="9,000+ five-star reviews from remote workers",
        language="EN",
    )
    angle_jp = Angle(
        project_id=project.id,
        name="生産性向上",
        pain_point="長時間のデスクワークで集中力が低下する",
        benefit="人間工学的デザインで疲労を軽減し、集中力を維持",
        hook="仕事中に腰痛や疲れを感じていませんか？",
        proof="9,000件以上の星5レビュー",
        language="JP",
    )
    db.add_all([angle_en, angle_jp])
    db.flush()

    variant = Variant(
        project_id=project.id,
        asset_id=asset.id,
        angle_id=angle_en.id,
        language="EN",
        primary_text="Tired of back pain ruining your productivity? Our ergonomic chair has helped 9,000+ remote workers work pain-free. 50% OFF today only — free shipping included.",
        headline="End Back Pain. Work Better.",
        description="Limited offer — 500 units only",
        overlay_text="50% OFF TODAY",
        template_id="template_v1_square",
        status="draft",
    )
    db.add(variant)
    db.commit()

    print(f"Seeded project '{project.name}' (id={project.id})")
    print(f"  1 asset, 2 angles, 1 variant created.")
    db.close()


if __name__ == "__main__":
    seed()

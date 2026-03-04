"""
Seed default AgentConfig rows on application startup.
Runs only if the named agents do not already exist — safe to call every boot.
"""
import json

from sqlalchemy.orm import Session

from .models import AgentConfig

# ── Output JSON schema shared by both agents ─────────────────────────────────

_ANGLE_SCHEMA = json.dumps({
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["angles"],
    "properties": {
        "angles": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "required": ["name", "pain_point", "benefit", "hook", "language"],
                "properties": {
                    "name":        {"type": "string", "minLength": 1, "maxLength": 80},
                    "pain_point":  {"type": "string"},
                    "benefit":     {"type": "string"},
                    "hook":        {"type": "string"},
                    "proof":       {"type": "string"},
                    "language":    {"type": "string", "enum": ["EN", "JP"]},
                },
                "additionalProperties": False,
            },
        }
    },
})

# ── English angle builder ─────────────────────────────────────────────────────

_EN_SYSTEM = """\
You are an expert performance marketing copywriter specialising in Meta \
(Facebook/Instagram) paid ads.
Your task: generate diverse ad angles from the product and landing page data provided.

Hard rules:
1. Ground every claim in the provided data. Do NOT invent statistics, reviews, or facts.
2. Return ONLY a valid JSON object — no markdown, no code fences, no commentary.
3. Each angle name must be unique within your response.
4. Hooks must be ≤20 words, punchy, and specific to a real claim in the data.
5. Vary tone across angles: urgency, curiosity, social proof, FOMO, aspiration, pain-relief.\
"""

_EN_USER_TEMPLATE = """\
Generate 10 high-converting Meta ad angles for the product below.

## Product Information
Brand: {{brand_name}}
Product: {{product_description}}
Offer: {{offer_description}}
Brand Rules / Tone: {{brand_rules}}

## Landing Page Data (extracted)
{{landing_summary_json}}

## Output Language
{{language}}

Return this exact JSON and nothing else:
{
  "angles": [
    {
      "name": "<3-5 word descriptive label>",
      "pain_point": "<specific problem this angle targets, grounded in landing data>",
      "benefit": "<concrete outcome or transformation promised>",
      "hook": "<opening ad line ≤20 words>",
      "proof": "<credibility element from landing page, or empty string>",
      "language": "EN"
    }
  ]
}\
"""

# ── Japanese angle builder ────────────────────────────────────────────────────

_JP_SYSTEM = """\
あなたはMeta（Facebook/Instagram）有料広告に特化した、経験豊富な\
パフォーマンスマーケティングコピーライターです。
タスク：提供された商品情報とランディングページデータのみに基づいて、\
多様な広告アングルを生成してください。

厳守ルール：
1. 提供データに基づいた主張のみを行うこと。統計・レビュー・事実を作り上げないこと。
2. 有効なJSONオブジェクトのみを返すこと。マークダウン・コードフェンス・説明文は不要。
3. レスポンス内のアングル名はすべて一意であること。
4. フックは≤20語で、簡潔かつデータ内の具体的な主張に基づくこと。
5. 緊急性・好奇心・社会的証明・FOMO・願望・痛み解消など、トーンを多様化すること。\
"""

_JP_USER_TEMPLATE = """\
以下の商品について10個の高コンバージョンMetaアドアングルを作成してください。

## 商品情報
ブランド: {{brand_name}}
商品: {{product_description}}
オファー: {{offer_description}}
ブランドルール / トーン: {{brand_rules}}

## ランディングページデータ（抽出済み）
{{landing_summary_json}}

## 出力言語
{{language}}

以下の正確なJSON形式のみで返してください（説明文なし）:
{
  "angles": [
    {
      "name": "<3〜5語の説明的なラベル>",
      "pain_point": "<このアングルが対象とする具体的な問題（ランディングデータに基づく）>",
      "benefit": "<約束された具体的な変化や成果>",
      "hook": "<≤20語の冒頭の広告コピー>",
      "proof": "<ランディングページからの信頼性要素、または空文字>",
      "language": "JP"
    }
  ]
}\
"""

# ── Seed function ─────────────────────────────────────────────────────────────

_DEFAULTS = [
    dict(
        name="angle_builder_en",
        description="Generates 10 EN Meta ad angles grounded in landing page data",
        purpose="creative",
        system_prompt=_EN_SYSTEM,
        user_prompt_template=_EN_USER_TEMPLATE,
        output_json_schema=_ANGLE_SCHEMA,
        model_provider="anthropic",
        model_name="claude-sonnet-4-6",
        temperature=0.7,
        max_tokens=4096,
        is_enabled=True,
    ),
    dict(
        name="angle_builder_ja",
        description="Generates 10 JP Meta ad angles grounded in landing page data",
        purpose="creative",
        system_prompt=_JP_SYSTEM,
        user_prompt_template=_JP_USER_TEMPLATE,
        output_json_schema=_ANGLE_SCHEMA,
        model_provider="anthropic",
        model_name="claude-sonnet-4-6",
        temperature=0.7,
        max_tokens=4096,
        is_enabled=True,
    ),
]


def seed_default_agents(db: Session) -> None:
    """Insert default agents if they do not already exist. Idempotent."""
    for data in _DEFAULTS:
        exists = db.query(AgentConfig).filter_by(name=data["name"]).first()
        if not exists:
            db.add(AgentConfig(**data))
    db.commit()

"""
LLM call abstraction.

Behaviour:
- No ANTHROPIC_API_KEY set  →  return deterministic stub JSON (app runs fully offline)
- ANTHROPIC_API_KEY present  →  call Anthropic Messages API via requests

Only one provider is supported for now: "anthropic".
"""
import json
import os

import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

# ── Stub responses ────────────────────────────────────────────────────────────
# Returned when no API key is configured.  Deterministic so tests are stable.

_STUB_EN = {
    "angles": [
        {
            "name": "Pain Relief Focus",
            "pain_point": "Hours at a desk cause chronic back pain and fatigue",
            "benefit": "Ergonomic support eliminates pain and boosts focus from day one",
            "hook": "Still tolerating back pain every single workday?",
            "proof": "9,000+ five-star reviews from remote workers",
            "language": "EN",
        },
        {
            "name": "Productivity Unlock",
            "pain_point": "Discomfort forces constant breaks and kills deep-work sessions",
            "benefit": "Work distraction-free for hours with zero discomfort",
            "hook": "What if you never had to stop mid-flow because of pain?",
            "proof": "Rated #1 ergonomic chair by WFH community 2024",
            "language": "EN",
        },
        {
            "name": "Limited Offer Urgency",
            "pain_point": "Missing a rare 50% sale means paying full price for months",
            "benefit": "Get the same premium chair at half the cost — today only",
            "hook": "50% off ends at midnight. 500 units left.",
            "proof": "",
            "language": "EN",
        },
    ]
}

_STUB_JP = {
    "angles": [
        {
            "name": "腰痛解消フォーカス",
            "pain_point": "長時間のデスクワークによる慢性的な腰痛と疲労",
            "benefit": "人間工学的サポートで初日から痛みを解消し集中力アップ",
            "hook": "毎日の腰痛、もう我慢しなくていいかもしれません",
            "proof": "リモートワーカーから9,000件以上の星5レビュー",
            "language": "JP",
        },
        {
            "name": "生産性向上",
            "pain_point": "不快感で集中が途切れ、深い作業ができない",
            "benefit": "何時間も不快感ゼロで集中して働ける",
            "hook": "痛みのせいで作業を中断しなければならないとしたら？",
            "proof": "WFHコミュニティ2024年 No.1人間工学チェア",
            "language": "JP",
        },
        {
            "name": "期間限定オファー",
            "pain_point": "めったにない50%OFFセールを逃すと数ヶ月間定価を払い続ける",
            "benefit": "同じプレミアムチェアが今日だけ半額で手に入る",
            "hook": "50%OFF終了まであと少し。残り500台。",
            "proof": "",
            "language": "JP",
        },
    ]
}


def generate(agent, prompt: str) -> str:
    """
    Call the LLM and return the raw text response.

    *agent* is an ``AgentConfig`` instance (duck-typed to avoid circular import).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    if not api_key:
        # Stub mode — return deterministic mock
        is_jp = "jp" in agent.name.lower() or "ja" in agent.name.lower()
        return json.dumps(_STUB_JP if is_jp else _STUB_EN, ensure_ascii=False)

    # Real API call
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }
    body: dict = {
        "model": agent.model_name or "claude-sonnet-4-6",
        "max_tokens": agent.max_tokens or 4096,
        "system": agent.system_prompt,
        "messages": [{"role": "user", "content": prompt}],
    }
    if agent.temperature is not None:
        body["temperature"] = agent.temperature

    resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"]

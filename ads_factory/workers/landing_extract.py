"""
Worker: extract key marketing data from a landing page URL.
Uses requests + BeautifulSoup. No full HTML is stored.
"""
import hashlib
import re

import requests
from bs4 import BeautifulSoup

# Tags that are almost always navigational / non-content boilerplate
_BOILERPLATE_TAGS = {"nav", "footer", "header", "aside", "script", "style", "noscript"}

# Keywords that indicate a CTA element (EN + JP)
_CTA_KEYWORDS = [
    "buy", "shop", "sign up", "signup", "subscribe", "order", "get started",
    "start free", "try free", "claim", "add to cart", "checkout", "purchase",
    "register", "join", "download", "install",
    "無料", "購入", "申し込み", "注文", "試す", "始める", "登録", "ダウンロード",
]

# Regex for common price formats (USD, JPY, EUR, GBP, KRW)
_PRICE_RE = re.compile(
    r"(?:[$¥€£₩]\s*[\d,]+(?:\.\d{1,2})?|[\d,]+(?:\.\d{1,2})?\s*(?:USD|JPY|円|ドル|%\s*off|%\s*OFF))",
)

RAW_TEXT_MAX = 10_000


def _is_cta(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _CTA_KEYWORDS)


def extract_landing_summary(url: str) -> dict:
    """
    Fetch *url*, parse it with BeautifulSoup and return a dict containing:
    - Scalar fields: title, h1, meta_description, canonical_url,
      language_detected, http_status, error
    - List fields: headings_h2, bullets, ctas, price_mentions, top_paragraphs
    - Raw: raw_text_excerpt (≤10k chars)
    - Cache key: content_hash (sha256)

    Never stores full HTML. All lists are capped per spec.
    """
    result: dict = {
        "title": None,
        "h1": None,
        "meta_description": None,
        "canonical_url": None,
        "language_detected": None,
        "http_status": None,
        "headings_h2": [],
        "bullets": [],
        "ctas": [],
        "price_mentions": [],
        "top_paragraphs": [],
        "raw_text_excerpt": "",
        "content_hash": None,
        "error": None,
    }

    # ── Fetch ────────────────────────────────────────────────────────────────
    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AdsFactoryBot/1.0)"},
            allow_redirects=True,
        )
        result["http_status"] = resp.status_code
        resp.raise_for_status()
    except requests.Timeout:
        result["error"] = "Request timed out after 15s"
        return result
    except requests.ConnectionError as exc:
        result["error"] = f"Connection error: {exc}"
        return result
    except requests.HTTPError as exc:
        result["error"] = f"HTTP {result['http_status']}: {exc}"
        return result
    except requests.RequestException as exc:
        result["error"] = str(exc)
        return result

    # ── Parse ────────────────────────────────────────────────────────────────
    soup = BeautifulSoup(resp.text, "html.parser")

    # Strip boilerplate before extracting text
    for tag in soup.find_all(_BOILERPLATE_TAGS):
        tag.decompose()

    # Title
    title_tag = soup.find("title")
    result["title"] = title_tag.get_text(strip=True) if title_tag else None

    # First H1
    h1_tag = soup.find("h1")
    result["h1"] = h1_tag.get_text(strip=True) if h1_tag else None

    # Meta description
    meta = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if meta:
        result["meta_description"] = (meta.get("content") or "").strip() or None

    # Canonical URL
    canonical = soup.find("link", rel="canonical")
    if canonical:
        result["canonical_url"] = (canonical.get("href") or "").strip() or None

    # ── Language detection ───────────────────────────────────────────────────
    html_el = soup.find("html")
    lang_attr = (html_el.get("lang") or "") if html_el else ""
    if lang_attr:
        result["language_detected"] = lang_attr.split("-")[0].upper()
    else:
        # Heuristic: count CJK code-point blocks
        full = soup.get_text()
        cjk = sum(
            1 for ch in full
            if "\u3000" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef"
        )
        result["language_detected"] = "JP" if cjk > 50 else "EN"

    # ── H2 headings (≤20) ────────────────────────────────────────────────────
    result["headings_h2"] = [
        h.get_text(strip=True)
        for h in soup.find_all("h2")
        if h.get_text(strip=True)
    ][:20]

    # ── Bullets / list items (≤50) ───────────────────────────────────────────
    result["bullets"] = [
        li.get_text(strip=True)
        for li in soup.find_all("li")
        if li.get_text(strip=True)
    ][:50]

    # ── CTAs — anchor & button text matching keywords (≤15, deduped) ─────────
    seen_ctas: set = set()
    ctas = []
    for el in soup.find_all(["a", "button"]):
        text = el.get_text(strip=True)
        if text and _is_cta(text) and text not in seen_ctas:
            seen_ctas.add(text)
            ctas.append(text)
            if len(ctas) >= 15:
                break
    result["ctas"] = ctas

    # ── Price mentions (≤10, deduped) ────────────────────────────────────────
    raw_text = soup.get_text(separator=" ")
    seen_prices: list = list(dict.fromkeys(_PRICE_RE.findall(raw_text)))[:10]
    result["price_mentions"] = seen_prices

    # ── Top paragraphs — meaningful only (≤8) ────────────────────────────────
    paras = []
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 40:
            paras.append(text)
            if len(paras) >= 8:
                break
    result["top_paragraphs"] = paras

    # ── Raw text excerpt (≤10k) ──────────────────────────────────────────────
    result["raw_text_excerpt"] = raw_text[:RAW_TEXT_MAX]

    # ── Content hash — sha256 over stable scalar+list fields ─────────────────
    hash_src = "|".join([
        result["title"] or "",
        result["h1"] or "",
        result["meta_description"] or "",
        " ".join(result["headings_h2"]),
        " ".join(result["bullets"][:10]),
        " ".join(result["ctas"][:5]),
    ])
    result["content_hash"] = hashlib.sha256(hash_src.encode("utf-8")).hexdigest()

    return result

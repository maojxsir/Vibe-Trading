"""Pure quote-fetching/parsing for the market overview proxy.

Kept free of FastAPI so the parsing logic can be unit-tested without the web
framework installed. The HTTP layer uses httpx.

Fetches free public quotes from Tencent (`qt.gtimg.cn`). Returns a flat
``code -> {name, price, change_pct}`` map for the frontend to render directly.
"""

from __future__ import annotations

from typing import Dict, Optional

import httpx

# Tencent quote endpoint. GBK-encoded ``;``-terminated assignment lines.
_TENCENT_URL = "https://qt.gtimg.cn/q="

# Codes shown on the overview page (indices + humanoid + AI-compute cores).
OVERVIEW_CODES = [
    # 大盘指数
    "sh000001", "sz399001", "sz399006", "sh000300", "usDJI", "usIXIC", "usINX",
    # 人形机器人·核心标的
    "sh688017", "sz002050", "sh601689", "sz002472", "sz300124", "sz003021",
    # AI算力·核心标的 (same four as AI算力 page coreFour)
    "sz300308", "sz002463", "sz300476", "sz300394",
]


def parse_tencent_line(raw: str) -> Optional[Dict[str, object]]:
    """Parse one ``v_<code>="...";`` line into ``{code, name, price, change_pct}``.

    Tencent fields are ``~``-separated: [1]=name, [3]=current price,
    [4]=previous close. ``change_pct`` is derived from those so it stays
    correct regardless of the trailing field layout. Returns ``None`` when the
    line cannot be parsed.
    """
    try:
        head, _, rest = raw.partition("=")
        code = head.strip().removeprefix("v_")
        body = rest.split('"', 1)[1].rsplit('"', 1)[0]
        fields = body.split("~")
        if len(fields) < 5 or not code:
            return None
        name = fields[1]
        price = float(fields[3])
        prev = float(fields[4]) if fields[4] else price
        change_pct = (price - prev) / prev * 100 if prev else 0.0
        return {"code": code, "name": name, "price": price, "change_pct": round(change_pct, 2)}
    except (IndexError, ValueError):
        return None


def parse_tencent_payload(text: str) -> Dict[str, Dict[str, object]]:
    """Parse a full multi-line Tencent response into ``code -> quote``."""
    quotes: Dict[str, Dict[str, object]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("v_"):
            continue
        parsed = parse_tencent_line(line)
        if parsed:
            quotes[str(parsed["code"])] = parsed
    return quotes


async def fetch_quotes(codes: list[str]) -> Dict[str, Dict[str, object]]:
    url = _TENCENT_URL + ",".join(codes)
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        # Tencent serves GBK; honour it explicitly (httpx may guess wrong).
        text = resp.content.decode("gbk", errors="replace")
    return parse_tencent_payload(text)

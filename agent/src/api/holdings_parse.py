"""Broker holdings screenshot parsing helpers.

The route accepts images in memory only. OCR and LLM calls are isolated behind
small functions so tests can exercise the JSON extraction and symbol resolving
logic without external services.
"""

from __future__ import annotations

import io
import json
import logging
import re
from typing import Any, Iterable, Mapping

from src.api.symbol_index import load_index

logger = logging.getLogger(__name__)

_CODE_RE = re.compile(r"\d{6}")
_INVALID_CODES = frozenset({"000000"})
_NUM_TOKEN_RE = re.compile(r"(\d+(?:\.\d+)?)(万)?")
_COST_KEYS = ("cost", "cost_price", "avg_cost", "成本", "成本价", "买入均价", "参考成本")
_SHARES_KEYS = ("shares", "quantity", "volume", "持仓数量", "证券数量", "持有数量", "股数", "数量", "可用")
_POSITION_KEYS = ("position_pct", "position", "weight_pct", "仓位", "仓位占比", "持仓占比", "占比")
_MARKET_VALUE_KEYS = ("market_value", "market_cap", "市值", "参考市值", "证券市值", "最新市值")
# "持仓" alone usually means share count on broker screenshots, not portfolio weight.
_SHARES_KEYS_WITH_HOLDING = _SHARES_KEYS + ("持仓",)


def _json_array_slice(text: str) -> str:
    start = text.find("[")
    if start < 0:
        raise ValueError("parse_failed")
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    raise ValueError("parse_failed")


def extract_holdings_json(text: str) -> list[dict[str, Any]]:
    """Extract a JSON array from an LLM response."""
    raw = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, flags=re.IGNORECASE | re.DOTALL)
    candidate = fence.group(1).strip() if fence else _json_array_slice(raw)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("parse_failed") from exc
    if isinstance(payload, dict):
        payload = payload.get("rows") or payload.get("holdings")
    if not isinstance(payload, list):
        raise ValueError("parse_failed")
    return [row for row in payload if isinstance(row, dict)]


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("%", "").replace(",", "")
    if text.endswith("万"):
        base = _to_float(text[:-1])
        return base * 10000 if base is not None else None
    if not text or text in {"-", "—"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _pick_float(raw: Mapping[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        val = _to_float(raw.get(key))
        if val is not None:
            return val
    return None


def _numbers_after_code(line: str, code: str) -> list[float]:
    """Extract numeric tokens from an OCR line, skipping the six-digit code itself."""
    compact = line.replace(" ", "")
    idx = compact.find(code)
    tail = line[idx + len(code) :] if idx >= 0 else line
    out: list[float] = []
    for match in _NUM_TOKEN_RE.finditer(tail):
        val = _to_float(f"{match.group(1)}{match.group(2) or ''}")
        if val is None:
            continue
        if abs(val - int(code)) < 1e-6:
            continue
        out.append(val)
    return out


def _infer_from_ocr_line(code: str, ocr_text: str) -> dict[str, float]:
    """Best-effort fallback when the LLM omits cost/shares/market value."""
    line = ""
    for candidate in ocr_text.splitlines():
        if code in candidate.replace(" ", ""):
            line = candidate
            break
    if not line:
        return {}

    nums = _numbers_after_code(line, code)
    if not nums:
        return {}

    inferred: dict[str, float] = {}
    prices = [n for n in nums if 0.01 <= n <= 5000]
    if prices:
        inferred["cost"] = prices[0]

    share_candidates = [n for n in nums if 100 <= n <= 200_000 and abs(n - round(n)) < 1e-6]
    if share_candidates:
        inferred["shares"] = max(share_candidates)

    large = [n for n in nums if n >= 1000]
    if large:
        inferred["market_value"] = max(large)

    return inferred


def _infer_position_weights(rows: list[dict[str, Any]]) -> None:
    """Fill missing position (%) from market value or shares × cost."""
    weights: list[float] = []
    for row in rows:
        weight = _to_float(row.get("market_value"))
        if weight is None:
            shares = _to_float(row.get("shares"))
            cost = _to_float(row.get("cost"))
            if shares is not None and cost is not None:
                weight = shares * cost
        weights.append(weight or 0.0)

    total = sum(weights)
    if total <= 0:
        return

    for row, weight in zip(rows, weights):
        if row.get("position") is not None or weight <= 0:
            continue
        row["position"] = round(weight / total * 100, 2)
        warnings = list(row.get("warnings") or [])
        if "inferred_position" not in warnings:
            warnings.append("inferred_position")
        row["warnings"] = warnings


def _clean_code(value: Any) -> str:
    match = _CODE_RE.search(str(value or ""))
    code = match.group(0) if match else ""
    if code in _INVALID_CODES:
        return ""
    return code


def _is_valid_code(code: str) -> bool:
    return bool(code) and bool(_CODE_RE.fullmatch(code)) and code not in _INVALID_CODES


def _index_maps(index_rows: Iterable[Mapping[str, str]]) -> tuple[dict[str, Mapping[str, str]], dict[str, Mapping[str, str]]]:
    by_code: dict[str, Mapping[str, str]] = {}
    by_name: dict[str, Mapping[str, str]] = {}
    for row in index_rows:
        code = str(row.get("code") or "").strip()
        name = str(row.get("name") or "").strip()
        if code and name:
            by_code[code] = row
            by_name[name] = row
    return by_code, by_name


def resolve_row(
    raw: Mapping[str, Any],
    index_by_code: Mapping[str, Mapping[str, str]],
    index_by_name: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    """Normalize one parsed holding row against the symbol index."""
    raw_code = _clean_code(raw.get("code") or raw.get("symbol"))
    raw_name = str(raw.get("name") or "").strip()
    matched = index_by_code.get(raw_code) if raw_code else None
    if matched is None and raw_name:
        matched = index_by_name.get(raw_name)

    warnings: list[str] = []
    confidence = 0.45
    code = raw_code
    name = raw_name
    if matched:
        code = str(matched.get("code") or raw_code)
        canonical_name = str(matched.get("name") or raw_name)
        if raw_name and canonical_name and raw_name != canonical_name:
            warnings.append("name_mismatch")
            confidence = 0.8
        else:
            confidence = 0.95 if raw_code else 0.78
        name = canonical_name
    else:
        warnings.append("unresolved_symbol")

    cost = _pick_float(raw, _COST_KEYS)
    position = _pick_float(raw, _POSITION_KEYS)
    shares = _pick_float(raw, _SHARES_KEYS_WITH_HOLDING)
    market_value = _pick_float(raw, _MARKET_VALUE_KEYS)

    if cost is None:
        warnings.append("missing_cost")
        cost = 0.0
    if shares is None:
        warnings.append("missing_shares")
    if position is None:
        warnings.append("missing_position")

    out: dict[str, Any] = {
        "code": code,
        "name": name or code,
        "cost": cost,
        "position": position,
        "shares": shares,
        "market_value": market_value,
        "confidence": round(confidence, 2),
        "warnings": warnings,
        "action": "append",
    }
    return out


def parse_holdings_from_text(
    ocr_text: str,
    llm_rows: list[Mapping[str, Any]],
    index_rows: Iterable[Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """Resolve LLM rows against the symbol index and drop duplicate codes."""
    index_by_code, index_by_name = _index_maps(index_rows if index_rows is not None else load_index())
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    warnings: list[str] = []
    for raw in llm_rows:
        resolved = resolve_row(raw, index_by_code, index_by_name)
        code = resolved.get("code")
        if not _is_valid_code(str(code or "")):
            continue
        if code and code in seen:
            if "duplicate_codes" not in warnings:
                warnings.append("duplicate_codes")
            continue
        if code:
            seen.add(str(code))
        rows.append(resolved)

    for row in rows:
        code = str(row.get("code") or "")
        if not code:
            continue
        inferred = _infer_from_ocr_line(code, ocr_text)
        row_warnings = list(row.get("warnings") or [])
        if row.get("cost") in (None, 0.0) and inferred.get("cost") is not None:
            row["cost"] = inferred["cost"]
            if "missing_cost" in row_warnings:
                row_warnings.remove("missing_cost")
            if "ocr_fallback" not in row_warnings:
                row_warnings.append("ocr_fallback")
        if row.get("shares") is None and inferred.get("shares") is not None:
            row["shares"] = inferred["shares"]
            if "missing_shares" in row_warnings:
                row_warnings.remove("missing_shares")
            if "ocr_fallback" not in row_warnings:
                row_warnings.append("ocr_fallback")
        if row.get("market_value") is None and inferred.get("market_value") is not None:
            row["market_value"] = inferred["market_value"]
            if "ocr_fallback" not in row_warnings:
                row_warnings.append("ocr_fallback")
        row["warnings"] = row_warnings

    _infer_position_weights(rows)

    for row in rows:
        row.pop("market_value", None)
        row_warnings = list(row.get("warnings") or [])
        if row.get("shares") is not None and "missing_shares" in row_warnings:
            row_warnings.remove("missing_shares")
        if row.get("position") is not None and "missing_position" in row_warnings:
            row_warnings.remove("missing_position")
        row["warnings"] = row_warnings

    if not rows:
        raise ValueError("no_holdings_found")

    return {
        "rows": rows,
        "meta": {
            "ocr_chars": len(ocr_text or ""),
            "model": "deepseek",
            "warnings": warnings,
        },
    }


def _prepare_image_array(image_bytes: bytes):
    """Load screenshot bytes, fix orientation, and downscale very large images for OCR."""
    import numpy as np  # type: ignore
    from PIL import Image, ImageOps  # type: ignore

    img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    max_side = max(img.size)
    if max_side > 2400:
        scale = 2400 / max_side
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
    return np.array(img)


def ocr_image_bytes(image_bytes: bytes) -> str:
    """Run OCR on an image byte buffer without persisting it."""
    try:
        from src.tools.doc_reader_tool import _get_ocr, _ocr_image_array

        _get_ocr()
    except ImportError as exc:
        raise ValueError("ocr_failed: rapidocr_not_installed") from exc

    try:
        text = _ocr_image_array(_prepare_image_array(image_bytes))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"ocr_failed: {exc}") from exc

    if not text.strip():
        logger.warning("holdings OCR returned no text (bytes=%s)", len(image_bytes or b""))
    return text


def call_llm_extract(ocr_text: str) -> str:
    """Ask the configured text LLM to extract holdings JSON from OCR text."""
    from src.providers.chat import ChatLLM

    prompt = (
        "你是 A 股券商/同花顺/东方财富持仓截图 OCR 文本解析器。"
        "请只输出 JSON 数组，每个元素字段："
        "code,name,cost,shares,market_value,position_pct。\n"
        "字段映射：\n"
        "- cost ← 成本价/成本/买入均价\n"
        "- shares ← 持仓/持仓数量/证券数量/股数/可用（整数，单位：股）\n"
        "- market_value ← 市值/参考市值（金额，含“万”需换算成元）\n"
        "- position_pct ← 仓位占比/占总资产%（截图若无此列填 null，禁止把股数填进 position_pct）\n"
        "只保留 A 股持仓行；无法确定的数字用 null。\n\n"
        f"OCR 文本:\n{ocr_text}"
    )
    response = ChatLLM().chat([{"role": "user", "content": prompt}], timeout=120)
    if not response.content:
        raise ValueError("parse_failed")
    return str(response.content)


def parse_holdings_image(image_bytes: bytes) -> dict[str, Any]:
    """OCR + LLM + symbol-resolution pipeline for a broker screenshot."""
    if not image_bytes:
        raise ValueError("ocr_empty")
    ocr_text = ocr_image_bytes(image_bytes)
    stripped = ocr_text.strip()
    if len(stripped) < 20 and not _CODE_RE.search(stripped):
        raise ValueError("ocr_empty")
    llm_text = call_llm_extract(ocr_text)
    llm_rows = extract_holdings_json(llm_text)
    return parse_holdings_from_text(ocr_text, llm_rows)

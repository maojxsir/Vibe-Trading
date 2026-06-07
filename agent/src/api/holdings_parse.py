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
    if not text or text in {"-", "—"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _clean_code(value: Any) -> str:
    match = _CODE_RE.search(str(value or ""))
    return match.group(0) if match else ""


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

    cost = _to_float(raw.get("cost") or raw.get("cost_price") or raw.get("成本") or raw.get("成本价"))
    position = _to_float(raw.get("position_pct") or raw.get("position") or raw.get("仓位") or raw.get("持仓占比"))
    shares = _to_float(raw.get("shares") or raw.get("quantity") or raw.get("持仓") or raw.get("可用"))
    if cost is None:
        warnings.append("missing_cost")
        cost = 0.0

    out: dict[str, Any] = {
        "code": code,
        "name": name or code,
        "cost": cost,
        "position": position,
        "shares": shares,
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
        if code and code in seen:
            if "duplicate_codes" not in warnings:
                warnings.append("duplicate_codes")
            continue
        if code:
            seen.add(str(code))
        rows.append(resolved)

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


def ocr_image_bytes(image_bytes: bytes) -> str:
    """Run OCR on an image byte buffer without persisting it."""
    try:
        import numpy as np  # type: ignore
        from PIL import Image  # type: ignore
        from src.tools.doc_reader_tool import _ocr_image_array

        img = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
        return _ocr_image_array(img)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"ocr_failed: {exc}") from exc


def call_llm_extract(ocr_text: str) -> str:
    """Ask the configured text LLM to extract holdings JSON from OCR text."""
    from src.providers.chat import ChatLLM

    prompt = (
        "你是 A 股券商持仓截图 OCR 文本解析器。"
        "请只输出 JSON 数组, 每个元素包含 code,name,cost,position_pct,shares。"
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
    if len(ocr_text.strip()) < 50:
        raise ValueError("ocr_empty")
    llm_text = call_llm_extract(ocr_text)
    llm_rows = extract_holdings_json(llm_text)
    return parse_holdings_from_text(ocr_text, llm_rows)

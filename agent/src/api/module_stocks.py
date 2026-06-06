"""Agent-backed industry-chain module stock list generation.

Mirrors :mod:`logic_chain` — strict JSON prompt, fenced-json parser, lazy agent
imports. Used by ``POST /market/module-stocks/generate`` for manual refresh on
AI算力 / 人形机器人 module tabs.
"""

from __future__ import annotations

import json
import re
from typing import List

_CODE_RE = re.compile(r"^\d{6}$")


def build_prompt(theme: str, module: str) -> str:
    """Build the agent prompt for a curated module watchlist."""
    return (
        f"你是A股「{theme}」产业链研究员。请为环节「{module}」挑选 3–6 只核心A股标的。\n"
        "如果可用，请先使用 web_search 工具检索最新研报与产业动态，再作答。\n\n"
        "最终只输出一个 JSON 对象（不要任何多余文字），用 ```json 代码块包裹。\n"
        "schema:\n"
        '{"stocks":[{"name":"公司简称","code":"6位A股代码","industry":"细分行业",'
        f'"module":"{module}","heatBase":0到100的整数,"logic":"不超过50字的核心逻辑"}}]}}\n\n'
        "要求：\n"
        "- 必须是真实A股上市公司，code 为 6 位数字（如 300308）；\n"
        "- heatBase 表示当前环节研究热度（0–100）；\n"
        "- 优先龙头与产业链卡位明确的标的；\n"
        "- 全部使用简体中文；只返回 JSON。"
    )


def _find_json_payload(text: str) -> str:
    """Return the first JSON object or array substring (prefers fenced blocks)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.S)
    if fenced:
        return fenced.group(1)
    stripped = text.strip()
    pairs = ("[", "]") if stripped.startswith("[") else ("{", "}")
    opener, closer = pairs
    start = text.find(opener)
    if start < 0:
        raise ValueError("no JSON payload found")
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("no JSON payload found")


def _normalize_row(raw: dict, default_module: str) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    code = str(raw.get("code") or "").strip()
    industry = str(raw.get("industry") or "").strip()
    module = str(raw.get("module") or default_module).strip() or default_module
    logic = str(raw.get("logic") or "").strip()
    if not name or not _CODE_RE.match(code) or not industry or not logic:
        return None
    try:
        heat = int(raw.get("heatBase", 50))
    except (TypeError, ValueError):
        heat = 50
    heat = max(0, min(100, heat))
    return {
        "name": name,
        "code": code,
        "industry": industry,
        "module": module,
        "heatBase": heat,
        "logic": logic,
    }


def extract_module_stocks_json(text: str, default_module: str = "") -> List[dict]:
    """Parse the agent answer into validated module stock rows."""
    if not text or not text.strip():
        raise ValueError("empty agent answer")
    payload = json.loads(_find_json_payload(text))
    if isinstance(payload, list):
        rows_raw = payload
    elif isinstance(payload, dict):
        rows_raw = payload.get("stocks") or []
    else:
        raise ValueError("unexpected JSON root type")

    rows: List[dict] = []
    seen: set[str] = set()
    for raw in rows_raw:
        row = _normalize_row(raw, default_module)
        if row and row["code"] not in seen:
            rows.append(row)
            seen.add(row["code"])
    if not rows:
        raise ValueError("no valid stocks in agent answer")
    return rows


def generate_module_stocks(theme: str, module: str, max_iterations: int = 12) -> List[dict]:
    """Run the Vibe-Trading agent to research module watchlist."""
    from src.tools import build_registry
    from src.providers.chat import ChatLLM
    from src.agent.loop import AgentLoop
    from src.memory.persistent import PersistentMemory
    from src.config.loader import load_agent_config

    pm = PersistentMemory()
    registry = build_registry(
        persistent_memory=pm,
        include_shell_tools=False,
        agent_config=load_agent_config(),
    )
    agent = AgentLoop(registry=registry, llm=ChatLLM(), max_iterations=max_iterations, persistent_memory=pm)
    result = agent.run(build_prompt(theme, module))
    return extract_module_stocks_json(result.get("content") or "", default_module=module)

"""Agent-backed 逻辑链 (logic chain) generation.

Uses the Vibe-Trading ReAct agent (with web_search) to research a topic and
emit a structured causal chain: 触发因素 → 传导逻辑 → 受益板块 → 具体标的.

Top-level imports are kept light (no FastAPI / agent stack) so the pure JSON
parser is unit-testable without those deps installed. The heavy agent stack is
imported lazily inside :func:`generate_logic_chain`.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

KINDS = {"trigger", "transmit", "sector", "target"}


def build_prompt(topic: str) -> str:
    """Build the agent prompt that asks for a strict JSON logic chain."""
    return (
        f"你是A股产业链与事件传导分析师。请研究主题：「{topic}」。\n"
        "如果可用，请先使用 web_search 工具检索最新信息，再作答。\n\n"
        "最终只输出一个 JSON 对象（不要任何多余文字、不要解释说明），用 ```json 代码块包裹。\n"
        "schema:\n"
        '{"nodes":[{"id":"唯一英文/数字id","kind":"trigger|transmit|sector|target",'
        '"label":"不超过14字的标题","desc":"不超过40字的说明","code":"仅当kind=target时填A股6位代码"}],'
        '"edges":[{"source":"节点id","target":"节点id"}]}\n\n'
        "要求：\n"
        "- 6到12个节点，至少各包含1个 trigger / transmit / sector / target；\n"
        "- kind=target 的节点必须是真实A股标的，并在 code 填写其6位代码（如 300308）；\n"
        "- edges 表达 触发因素→传导逻辑→受益板块→具体标的 的因果流向；\n"
        "- 全部使用简体中文；只返回 JSON。"
    )


def _find_json_object(text: str) -> str:
    """Return the first JSON object substring (prefers a fenced ```json block)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        return fenced.group(1)
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object found")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("unbalanced JSON object")


def extract_chain_json(text: str) -> Dict[str, List[dict]]:
    """Parse the agent's answer into a validated ``{nodes, edges}`` chain.

    Drops malformed nodes (bad/missing kind or label) and edges that reference
    unknown node ids. Raises ``ValueError`` when nothing usable remains.
    """
    if not text or not text.strip():
        raise ValueError("empty agent answer")
    data = json.loads(_find_json_object(text))

    nodes: List[dict] = []
    ids: set[str] = set()
    for n in data.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id") or "").strip()
        kind = str(n.get("kind") or "").strip()
        label = str(n.get("label") or "").strip()
        if not nid or kind not in KINDS or not label:
            continue
        node: dict = {"id": nid, "kind": kind, "label": label, "desc": str(n.get("desc") or "").strip()}
        code = n.get("code")
        if code:
            node["code"] = str(code).strip()
        nodes.append(node)
        ids.add(nid)

    if not nodes:
        raise ValueError("no valid nodes in agent answer")

    edges: List[dict] = []
    seen: set[tuple[str, str]] = set()
    for e in data.get("edges") or []:
        if not isinstance(e, dict):
            continue
        s = str(e.get("source") or "").strip()
        t = str(e.get("target") or "").strip()
        if s in ids and t in ids and s != t and (s, t) not in seen:
            edges.append({"source": s, "target": t})
            seen.add((s, t))

    return {"nodes": nodes, "edges": edges}


def generate_logic_chain(topic: str, max_iterations: int = 12) -> Dict[str, List[dict]]:
    """Run the Vibe-Trading agent to research ``topic`` and return a chain.

    Requires the full agent stack and a configured LLM provider. Raises on any
    failure (no provider key, agent error, unparseable answer); the route layer
    converts that into a graceful ``stale`` response.
    """
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
    result = agent.run(build_prompt(topic))
    return extract_chain_json(result.get("content") or "")

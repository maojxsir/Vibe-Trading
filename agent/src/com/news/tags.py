"""Watchlist tagging shared by all news providers."""

from __future__ import annotations

from typing import List

WATCHLIST_NAMES: List[str] = [
    "绿的谐波", "三花智控", "拓普集团", "双环传动", "汇川技术", "兆威机电",
    "中际旭创", "沪电股份", "胜宏科技", "天孚通信", "寒武纪", "海光信息",
    "光模块", "减速器", "丝杠", "PCB", "人形机器人", "算力", "AI芯片",
    "GPU", "CPO", "HBM", "数据中心", "液冷", "英伟达", "国产替代",
]


def tag_tickers(text: str) -> List[str]:
    return [name for name in WATCHLIST_NAMES if name in text]

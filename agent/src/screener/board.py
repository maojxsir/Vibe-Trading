"""A-share board detection and limit-up threshold helpers."""

from __future__ import annotations

BoardName = str


def _normalize_code(code: str) -> str:
    """Return bare 6-digit code, stripping exchange suffix if present."""
    bare = code.split(".", maxsplit=1)[0]
    return bare.strip()


def _is_st_name(name: str) -> bool:
    """True when the security name indicates an ST/*ST listing."""
    upper = str(name or "").strip().upper()
    return upper.startswith("*ST") or upper.startswith("ST")


def _is_delisting_name(name: str) -> bool:
    """True when the security name indicates a delisting/delisted stock.

    退市整理期个股会被冠以“退市XX”或更名为“XX退”，如 605081 退市太和。
    """
    text = str(name or "").strip()
    return "退市" in text or text.endswith("退")


def detect_board(code: str, name: str) -> BoardName:
    """Classify an A-share listing by board from code and name.

    ST names take precedence. Otherwise board is inferred from the code prefix.
    """
    if _is_st_name(name):
        return "ST"

    bare = _normalize_code(code)

    if bare.startswith("688"):
        return "科创板"
    if bare.startswith("30"):
        return "创业板"
    if bare.startswith("920") or bare.startswith("8") or bare.startswith("4"):
        return "北交所"
    return "主板"


def limit_up_threshold(code: str, name: str) -> float:
    """Return the limit-up percentage threshold for the given security."""
    if _is_st_name(name):
        return 5.0

    board = detect_board(code, name)
    if board in ("创业板", "科创板"):
        return 20.0
    if board == "北交所":
        return 30.0
    return 10.0


def is_limit_up(
    pct_chg: float,
    code: str,
    name: str,
    *,
    tolerance: float = 0.3,
) -> bool:
    """True when pct_chg reaches the board limit within tolerance."""
    threshold = limit_up_threshold(code, name)
    return pct_chg >= threshold - tolerance

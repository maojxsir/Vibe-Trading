import pytest


def test_extract_json_from_llm_response():
    from src.api.holdings_parse import extract_holdings_json

    text = '```json\n[{"code":"688017","name":"绿的谐波","cost":248.5,"position_pct":42}]\n```'
    rows = extract_holdings_json(text)
    assert rows[0]["code"] == "688017"
    assert rows[0]["position_pct"] == 42


def test_extract_json_rejects_no_array():
    from src.api.holdings_parse import extract_holdings_json

    with pytest.raises(ValueError):
        extract_holdings_json("没有持仓")


def test_resolve_row_matches_index_by_code():
    from src.api.holdings_parse import resolve_row

    index_by_code = {"688017": {"code": "688017", "name": "绿的谐波", "cnspell": "LDXB"}}
    out = resolve_row(
        {"code": "688017", "name": "绿的谐波", "cost": 248.5, "position_pct": 42},
        index_by_code,
        {},
    )
    assert out["code"] == "688017"
    assert out["name"] == "绿的谐波"
    assert out["position"] == 42
    assert out["confidence"] >= 0.9
    assert out["warnings"] == []


def test_resolve_row_warns_on_name_mismatch():
    from src.api.holdings_parse import resolve_row

    index_by_code = {"688017": {"code": "688017", "name": "绿的谐波", "cnspell": "LDXB"}}
    out = resolve_row(
        {"code": "688017", "name": "错名", "cost": 248.5, "position_pct": 42},
        index_by_code,
        {},
    )
    assert out["name"] == "绿的谐波"
    assert "name_mismatch" in out["warnings"]


def test_parse_holdings_from_text_dedupes_codes():
    from src.api.holdings_parse import parse_holdings_from_text

    index_rows = [{"code": "688017", "name": "绿的谐波", "cnspell": "LDXB"}]
    llm_rows = [
        {"code": "688017", "name": "绿的谐波", "cost": 248.5, "position_pct": 42},
        {"code": "688017", "name": "绿的谐波", "cost": 249.5, "position_pct": 41},
    ]
    result = parse_holdings_from_text("持仓 688017 绿的谐波", llm_rows, index_rows)
    assert len(result["rows"]) == 1
    assert "duplicate_codes" in result["meta"]["warnings"]

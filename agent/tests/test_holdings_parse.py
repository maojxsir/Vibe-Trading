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
        {"code": "688017", "name": "绿的谐波", "cost": 248.5, "position_pct": 42, "shares": 4200},
        index_by_code,
        {},
    )
    assert out["code"] == "688017"
    assert out["name"] == "绿的谐波"
    assert out["position"] == 42
    assert out["shares"] == 4200
    assert out["confidence"] >= 0.9
    assert "missing_shares" not in out["warnings"]
    assert "missing_position" not in out["warnings"]


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


def test_infer_position_from_market_values():
    from src.api.holdings_parse import parse_holdings_from_text

    index_rows = [
        {"code": "688017", "name": "绿的谐波", "cnspell": "LDXB"},
        {"code": "300124", "name": "汇川技术", "cnspell": "HCGJ"},
    ]
    llm_rows = [
        {"code": "688017", "name": "绿的谐波", "cost": 248.5, "shares": 4200, "market_value": 1650000},
        {"code": "300124", "name": "汇川技术", "cost": 68.2, "shares": 5000, "market_value": 375000},
    ]
    result = parse_holdings_from_text("688017 ... 165万\n300124 ... 37.5万", llm_rows, index_rows)
    positions = {row["code"]: row["position"] for row in result["rows"]}
    assert positions["688017"] == pytest.approx(81.48, rel=0.01)
    assert positions["300124"] == pytest.approx(18.52, rel=0.01)
    assert "inferred_position" in result["rows"][0]["warnings"]


def test_ocr_fallback_fills_shares_and_position():
    from src.api.holdings_parse import parse_holdings_from_text

    index_rows = [{"code": "688017", "name": "绿的谐波", "cnspell": "LDXB"}]
    ocr = "688017 绿的谐波 248.50 393.00 4200 165.26万"
    llm_rows = [{"code": "688017", "name": "绿的谐波", "cost": 248.5}]
    result = parse_holdings_from_text(ocr, llm_rows, index_rows)
    row = result["rows"][0]
    assert row["shares"] == 4200
    assert row["position"] == pytest.approx(100.0)
    assert "ocr_fallback" in row["warnings"]


def test_parse_holdings_skips_placeholder_code():
    from src.api.holdings_parse import parse_holdings_from_text

    index_rows = [{"code": "688017", "name": "绿的谐波", "cnspell": "LDXB"}]
    llm_rows = [
        {"code": "000000", "name": "新标的", "cost": 0, "position_pct": 0},
        {"code": "688017", "name": "绿的谐波", "cost": 248.5, "shares": 4200, "market_value": 1650000},
    ]
    result = parse_holdings_from_text("688017 248.5 4200", llm_rows, index_rows)
    assert len(result["rows"]) == 1
    assert result["rows"][0]["code"] == "688017"

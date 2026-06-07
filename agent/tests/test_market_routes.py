from src.api.market_quotes import parse_tencent_line, parse_tencent_payload
from src.api.market_news import parse_sina_news, tag_tickers
from src.api.logic_chain import extract_chain_json, extract_topics_json
from src.api.module_stocks import extract_module_stocks_json


def _route_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.api.market_routes import router

    app = FastAPI()
    app.include_router(router)
    try:
        from src.api.market_routes import holdings_router

        app.include_router(holdings_router)
    except ImportError:
        pass
    return TestClient(app)


def test_parse_tencent_index_line():
    raw = 'v_sh000001="1~上证指数~000001~4083.97~4075.00~8.97~123~456~789";'
    q = parse_tencent_line(raw)
    assert q is not None
    assert q["code"] == "sh000001"
    assert q["name"] == "上证指数"
    assert q["price"] == 4083.97
    assert q["change_pct"] == 0.22  # (4083.97-4075)/4075*100


def test_symbols_search_returns_results(monkeypatch):
    from src.api import symbol_index

    monkeypatch.setattr(
        symbol_index,
        "load_index",
        lambda: [{"code": "688017", "name": "绿的谐波", "cnspell": "LDXB", "ts_code": "688017.SH"}],
    )
    response = _route_client().get("/market/symbols/search", params={"q": "688"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["results"][0]["code"] == "688017"


def test_market_kline_route(monkeypatch):
    from src.api import market_kline

    monkeypatch.setattr(
        market_kline,
        "fetch_kline",
        lambda code, days=365: {
            "code": "688017",
            "name": "绿的谐波",
            "bars": [{"time": "2025-06-01", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}],
            "source": "fake",
            "stale": False,
            "updatedAt": "2025-06-06 12:00:00",
            "error": None,
        },
    )
    response = _route_client().get("/market/kline", params={"code": "688017", "days": 90})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "688017"
    assert len(body["bars"]) == 1


def test_holdings_parse_screenshot_route_returns_rows(monkeypatch):
    from src.api import holdings_parse

    monkeypatch.setattr(
        holdings_parse,
        "parse_holdings_image",
        lambda _data: {
            "rows": [{"code": "688017", "name": "绿的谐波", "cost": 248.5, "position": 42, "confidence": 0.95}],
            "meta": {"ocr_chars": 1200, "model": "deepseek", "warnings": []},
        },
    )
    response = _route_client().post(
        "/holdings/parse-screenshot",
        files={"file": ("holdings.png", b"fake image", "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["rows"][0]["code"] == "688017"


def test_parse_tencent_negative_change():
    raw = 'v_sz002050="51~三花智控~002050~45.08~45.17~...";'
    q = parse_tencent_line(raw)
    assert q is not None
    assert q["price"] == 45.08
    assert q["change_pct"] == -0.20


def test_parse_tencent_line_bad_input_returns_none():
    assert parse_tencent_line("garbage") is None
    assert parse_tencent_line('v_x="1~only~two";') is None


def test_parse_tencent_payload_multiline():
    text = (
        'v_sh000001="1~上证指数~000001~4083.97~4075.00~8.97";\n'
        'v_sz399001="51~深证成指~399001~15704.71~15591.00~113.71";\n'
    )
    quotes = parse_tencent_payload(text)
    assert set(quotes.keys()) == {"sh000001", "sz399001"}
    assert quotes["sz399001"]["price"] == 15704.71


def test_parse_sina_news_normalizes_rows():
    payload = {
        "result": {
            "data": [
                {
                    "title": "中际旭创光模块需求旺盛",
                    "intro": "1.6T 放量",
                    "media_name": "财联社",
                    "ctime": "1780000000",
                    "url": "https://example.com/a",
                },
                {"title": "", "intro": "should be skipped"},
            ]
        }
    }
    rows = parse_sina_news(payload)
    assert len(rows) == 1
    assert rows[0]["title"] == "中际旭创光模块需求旺盛"
    assert rows[0]["source"] == "财联社"
    assert "中际旭创" in rows[0]["tickers"]
    assert "光模块" in rows[0]["tickers"]


def test_parse_sina_news_empty_payload():
    assert parse_sina_news({}) == []
    assert parse_sina_news({"result": {"data": []}}) == []


def test_tag_tickers_no_match():
    assert tag_tickers("今日天气晴朗") == []


def test_extract_chain_json_fenced():
    text = (
        "好的，结果如下：\n"
        "```json\n"
        '{"nodes":[{"id":"t1","kind":"trigger","label":"H200解禁","desc":"出口放开"},'
        '{"id":"s1","kind":"sector","label":"光模块","desc":"国产化"},'
        '{"id":"g1","kind":"target","label":"中际旭创","desc":"龙头","code":"300308"}],'
        '"edges":[{"source":"t1","target":"s1"},{"source":"s1","target":"g1"}]}\n'
        "```\n"
    )
    chain = extract_chain_json(text)
    assert len(chain["nodes"]) == 3
    assert len(chain["edges"]) == 2
    target = [n for n in chain["nodes"] if n["kind"] == "target"][0]
    assert target["code"] == "300308"


def test_extract_chain_json_drops_bad_nodes_and_edges():
    text = (
        '{"nodes":[{"id":"a","kind":"trigger","label":"X"},'
        '{"id":"b","kind":"BOGUS","label":"Y"},'
        '{"id":"c","kind":"sector","label":""}],'
        '"edges":[{"source":"a","target":"b"},{"source":"a","target":"a"}]}'
    )
    chain = extract_chain_json(text)
    # only node "a" is valid; edges referencing dropped/ self are removed
    assert [n["id"] for n in chain["nodes"]] == ["a"]
    assert chain["edges"] == []


def test_extract_chain_json_raises_on_empty():
    import pytest

    with pytest.raises(ValueError):
        extract_chain_json("")
    with pytest.raises(ValueError):
        extract_chain_json("no json here")


def test_extract_module_stocks_json_fenced():
    text = (
        "```json\n"
        '{"stocks":[{"name":"中际旭创","code":"300308","industry":"光模块",'
        '"module":"光模块","heatBase":90,"logic":"800G龙头"}]}\n'
        "```"
    )
    rows = extract_module_stocks_json(text, default_module="光模块")
    assert len(rows) == 1
    assert rows[0]["code"] == "300308"
    assert rows[0]["heatBase"] == 90


def test_extract_module_stocks_json_drops_bad_rows():
    text = (
        '[{"name":"好","code":"300308","industry":"光","module":"光模块","heatBase":80,"logic":"ok"},'
        '{"name":"坏","code":"abc","industry":"x","module":"光模块","heatBase":50,"logic":"bad"}]'
    )
    rows = extract_module_stocks_json(text, default_module="光模块")
    assert len(rows) == 1
    assert rows[0]["name"] == "好"


def test_extract_module_stocks_json_raises_on_empty():
    import pytest

    with pytest.raises(ValueError):
        extract_module_stocks_json("", default_module="光模块")


def test_extract_topics_json_fenced():
    text = '```json\n["算力租赁涨价→IDC重估","H200解禁→光模块受益"]\n```'
    topics = extract_topics_json(text)
    assert len(topics) == 2
    assert "光模块" in topics[1]

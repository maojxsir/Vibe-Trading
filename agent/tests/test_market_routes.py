from src.api.market_quotes import parse_tencent_line, parse_tencent_payload
from src.api.market_news import parse_sina_news, tag_tickers


def test_parse_tencent_index_line():
    raw = 'v_sh000001="1~上证指数~000001~4083.97~4075.00~8.97~123~456~789";'
    q = parse_tencent_line(raw)
    assert q is not None
    assert q["code"] == "sh000001"
    assert q["name"] == "上证指数"
    assert q["price"] == 4083.97
    assert q["change_pct"] == 0.22  # (4083.97-4075)/4075*100


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

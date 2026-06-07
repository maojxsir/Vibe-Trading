from src.api.symbol_index import _rows_from_records, search_symbols


FIXTURE = _rows_from_records(
    [
        {"symbol": "688017", "name": "绿的谐波", "cnspell": "LDXB", "ts_code": "688017.SH"},
        {"symbol": "300124", "name": "汇川技术", "cnspell": "HCKJ", "ts_code": "300124.SZ"},
        {"symbol": "002050", "name": "三花智控", "cnspell": "SHZK", "ts_code": "002050.SZ"},
    ]
)


def test_search_by_code_prefix():
    hits = search_symbols("688", FIXTURE, boost=set(), limit=10)
    assert hits[0]["code"] == "688017"


def test_search_by_cnspell():
    hits = search_symbols("ldxb", FIXTURE, boost=set(), limit=10)
    assert hits[0]["code"] == "688017"


def test_search_by_name_substring():
    hits = search_symbols("谐波", FIXTURE, boost=set(), limit=10)
    assert hits[0]["code"] == "688017"


def test_search_boost_recent_within_same_tier():
    hits = search_symbols("3", FIXTURE, boost={"300124"}, limit=10)
    assert hits[0]["code"] == "300124"


def test_empty_query_returns_boosted_rows_only():
    hits = search_symbols("", FIXTURE, boost={"002050"}, limit=10)
    assert [h["code"] for h in hits] == ["002050"]

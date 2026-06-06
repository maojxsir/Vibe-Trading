from src.com.news.merge import merge_news_rows, normalize_title


def test_merge_dedupes_same_title():
    rows_a = [{"title": "光模块需求旺盛", "time": "2026-06-06 10:00", "url": "http://a"}]
    rows_b = [{"title": "光模块 需求旺盛", "time": "2026-06-06 09:00", "url": "http://b"}]
    merged = merge_news_rows([("sina", rows_a), ("wscn", rows_b)], limit=10)
    assert len(merged) == 1
    assert merged[0]["url"] == "http://a"


def test_merge_sorts_newest_first():
    older = [{"title": "A", "time": "2026-06-05 12:00", "url": ""}]
    newer = [{"title": "B", "time": "2026-06-06 12:00", "url": ""}]
    merged = merge_news_rows([("x", older), ("y", newer)], limit=10)
    assert [r["title"] for r in merged] == ["B", "A"]


def test_normalize_title_strips_whitespace():
    assert normalize_title("光模块  需求") == normalize_title("光模块 需求")
